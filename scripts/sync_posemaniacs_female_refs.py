import argparse
import json
import mimetypes
import re
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_SOURCE_URL = "https://www.posemaniacs.com/poses/female"
DEFAULT_OUTDIR = Path(r"C:\Users\abesh\Documents\Blender\MaleAnatomy\Sample\posemaniacs_ref\female_poses_live")
DEFAULT_MANIFEST = DEFAULT_OUTDIR / "manifest.json"
USER_AGENT = "CodexPoseManiacsSync/1.0 (+https://www.posemaniacs.com/poses/female)"


def first_url_from_srcset(value: str) -> str:
    return value.split(",")[0].strip().split(" ")[0].strip()


def normalize_url(base_url: str, raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        return url
    if url.startswith("//"):
        return "https:" + url
    return urljoin(base_url, url)


def infer_extension(url: str, content_type: Optional[str]) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix:
        return suffix
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    return ".bin"


@dataclass
class PoseEntry:
    pose_number: str
    image_url: str
    source_hint: str


class PoseManiacsFemaleParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.anchor_stack: list[str] = []
        self.entries: dict[str, PoseEntry] = {}

    def handle_starttag(self, tag: str, attrs):
        attr_map = {key: value for key, value in attrs}
        if tag == "a":
            href = normalize_url(self.base_url, attr_map.get("href", ""))
            self.anchor_stack.append(href)
            return

        if tag != "img":
            return

        alt = attr_map.get("alt", "") or ""
        match = re.search(r"Pose number (\d+)", alt)
        if not match:
            return

        pose_number = match.group(1)
        candidate_urls = []
        for key in ("data-src", "data-lazy-src", "src", "srcset", "data-srcset"):
            value = attr_map.get(key)
            if not value:
                continue
            candidate = first_url_from_srcset(value) if "srcset" in key else value
            candidate_urls.append(normalize_url(self.base_url, candidate))

        if self.anchor_stack:
            candidate_urls.insert(0, self.anchor_stack[-1])

        image_url = ""
        source_hint = ""
        for candidate in candidate_urls:
            if not candidate:
                continue
            if "cdn-cgi/image" in candidate or "cdn.posemaniacs.com" in candidate:
                image_url = candidate
                source_hint = candidate
                break
            if candidate.endswith((".png", ".jpg", ".jpeg", ".webp")):
                image_url = candidate
                source_hint = candidate
                break

        if not image_url:
            return

        self.entries[pose_number] = PoseEntry(
            pose_number=pose_number,
            image_url=image_url,
            source_hint=source_hint or image_url,
        )

    def handle_endtag(self, tag: str):
        if tag == "a" and self.anchor_stack:
            self.anchor_stack.pop()


def fetch_text(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        encoding = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(encoding, errors="replace")


def download_file(url: str, destination: Path, timeout: float, overwrite: bool) -> dict:
    if destination.exists() and not overwrite:
        return {
            "path": str(destination),
            "status": "skipped_existing",
            "bytes": destination.stat().st_size,
        }

    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type")
        payload = response.read()

    final_destination = destination
    inferred_ext = infer_extension(url, content_type)
    if final_destination.suffix.lower() != inferred_ext.lower():
        final_destination = final_destination.with_suffix(inferred_ext)

    final_destination.parent.mkdir(parents=True, exist_ok=True)
    final_destination.write_bytes(payload)
    return {
        "path": str(final_destination),
        "status": "downloaded",
        "bytes": len(payload),
        "content_type": content_type,
    }


def build_manifest(source_url: str, entries: list[PoseEntry], output_dir: Path, downloaded: list[dict]) -> dict:
    by_pose = {item["pose_number"]: item for item in downloaded}
    return {
        "source_url": source_url,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "entry_count": len(entries),
        "output_dir": str(output_dir),
        "poses": [
            {
                "pose_number": entry.pose_number,
                "image_url": entry.image_url,
                "local_path": by_pose.get(entry.pose_number, {}).get("local_path"),
                "download_status": by_pose.get(entry.pose_number, {}).get("download_status"),
                "bytes": by_pose.get(entry.pose_number, {}).get("bytes"),
            }
            for entry in entries
        ],
    }


def sync_posemaniacs_female_refs(
    source_url: str,
    output_dir: Path,
    manifest_path: Path,
    timeout: float,
    limit: Optional[int],
    skip_download: bool,
    overwrite: bool,
) -> dict:
    html = fetch_text(source_url, timeout=timeout)
    parser = PoseManiacsFemaleParser(source_url)
    parser.feed(html)

    entries = sorted(parser.entries.values(), key=lambda item: item.pose_number)
    if limit is not None:
        entries = entries[:limit]

    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for entry in entries:
        local_stub = output_dir / f"{entry.pose_number}_female"
        result = {
            "pose_number": entry.pose_number,
            "image_url": entry.image_url,
            "local_path": None,
            "download_status": "not_requested",
            "bytes": None,
        }
        if not skip_download:
            download_result = download_file(entry.image_url, local_stub, timeout=timeout, overwrite=overwrite)
            result["local_path"] = download_result["path"]
            result["download_status"] = download_result["status"]
            result["bytes"] = download_result["bytes"]
        downloaded.append(result)

    manifest = build_manifest(source_url, entries, output_dir, downloaded)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync PoseManiacs female pose reference images from the public listing page.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = sync_posemaniacs_female_refs(
            source_url=args.source_url,
            output_dir=args.outdir,
            manifest_path=args.manifest,
            timeout=args.timeout,
            limit=args.limit,
            skip_download=args.skip_download,
            overwrite=args.overwrite,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"ok": True, "manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
