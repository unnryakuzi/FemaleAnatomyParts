# -*- coding: utf-8 -*-
"""配布パッケージから形式別 zip を組み立てる（blend/fbx/glb/obj の4本）。

  python scripts/listing/make_zips.py <female|male> <version>

例:
  python scripts/listing/make_zips.py male v1.2.0
    配布パッケージ_Man_v1.2.0/  ->  配布zip_Man_v1.2.0/MaleAnatomy_v1.2.0_{blend,fbx,glb,obj}.zip

★構成は配布済み v1.1.0 の zip を実測して合わせてある:
  各 zip = README.txt / LICENSE.txt / CREDITS.txt / index/* / models/<その形式のファイル>
  previews は zip に入れない（パッケージディレクトリにのみ置く）。
  obj は .obj と .mtl の2ファイル。BOOTH の1ファイル上限は 1.2GB。
"""
import os
import sys
import time
import zipfile

ROOT = r"C:\Users\abesh\Documents\Blender\MaleAnatomy"
COMMON = ["README.txt", "LICENSE.txt", "CREDITS.txt"]
EXTS = {"blend": [".blend"], "fbx": [".fbx"], "glb": [".glb"], "obj": [".obj", ".mtl"]}
BOOTH_LIMIT = 1.2 * 1000 ** 3


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: python make_zips.py <female|male> <version>")
    model, version = sys.argv[1], sys.argv[2]
    dirtag = ("Man_" + version) if model == "male" else version
    stem = ("MaleAnatomy_" if model == "male" else "FemaleAnatomy_") + version
    pkg = os.path.join(ROOT, "配布パッケージ_" + dirtag)
    out = os.path.join(ROOT, "配布zip_" + dirtag)
    os.makedirs(out, exist_ok=True)

    index_dir = os.path.join(pkg, "index")
    index_files = sorted(os.listdir(index_dir)) if os.path.isdir(index_dir) else []

    over = []
    for fmt, exts in EXTS.items():
        members = [(os.path.join(pkg, f), f) for f in COMMON]
        members += [(os.path.join(index_dir, f), "index/" + f) for f in index_files]
        for e in exts:
            src = os.path.join(pkg, "models", stem + e)
            if not os.path.exists(src):
                raise SystemExit("見つからない: " + src)
            members.append((src, "models/" + stem + e))

        zpath = os.path.join(out, stem + "_" + fmt + ".zip")
        t = time.time()
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9,
                             allowZip64=True) as z:
            for src, arc in members:
                z.write(src, arc)
        size = os.path.getsize(zpath)
        flag = "  ★BOOTH 1.2GB 超過" if size > BOOTH_LIMIT else ""
        if size > BOOTH_LIMIT:
            over.append(os.path.basename(zpath))
        print("[zip] %-40s %8.1f MB  %.0fs%s"
              % (os.path.basename(zpath), size / 1e6, time.time() - t, flag))

    total = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    print("[zip] 合計 %.2f GB -> %s" % (total / 1e9, out))
    if over:
        print("[zip] ★BOOTH にアップできないファイルがある: " + ", ".join(over))


main()
