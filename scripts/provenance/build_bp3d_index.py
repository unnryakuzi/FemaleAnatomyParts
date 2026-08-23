# -*- coding: utf-8 -*-
"""BodyParts3D v4.0 の OBJ ヘッダを走査してインデックス JSON を作る。

各 OBJ の先頭コメントに File ID / Representation ID / Concept ID / English name /
Bounds(mm) / Volume(cm3) が入っているので、メッシュ本体を読まずに照合キーが揃う。
"""
import json
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                    "refs", "BodyParts3D_v4.0")
BASE = os.path.normpath(BASE)

DIRS = {
    "isa": os.path.join(BASE, "obj_isa", "isa_BP3D_4.0_obj_99"),
    "partof": os.path.join(BASE, "obj_partof", "partof_BP3D_4.0_obj_99"),
}

HDR = re.compile(r"^#\s*([A-Za-z ()3]+?)\s*:\s*(.+?)\s*$")
BOUNDS = re.compile(r"\(([-\d.,]+)\)-\(([-\d.,]+)\)")


def read_header(path):
    """OBJ 先頭のコメント行だけ読む。頂点行が始まったら打ち切る。"""
    info = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("#"):
                break
            m = HDR.match(line.rstrip("\n"))
            if m:
                info[m.group(1).strip()] = m.group(2).strip()
    return info


def count_verts(path):
    n = 0
    with open(path, "rb") as f:
        for line in f:
            if line.startswith(b"v "):
                n += 1
    return n


def main(with_verts=False):
    parts_list = {}
    for fn, tree in (("isa_parts_list.txt", "isa"),
                     ("partof_parts_list.txt", "partof")):
        p = os.path.join(BASE, fn)
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            next(f)
            for line in f:
                c = line.rstrip("\n").split("\t")
                if len(c) >= 5:
                    parts_list.setdefault(c[1], {
                        "fma": c[0], "en": c[2], "kanji": c[3], "kana": c[4],
                        "tree": tree})

    out = []
    for tree, d in DIRS.items():
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".obj"):
                continue
            path = os.path.join(d, name)
            h = read_header(path)
            bp = h.get("Representation ID", "")
            rec = {
                "tree": tree,
                "file": name,
                "file_id": h.get("File ID", os.path.splitext(name)[0]),
                "bp": bp,
                "fma": h.get("Concept ID", ""),
                "en": h.get("English name", ""),
                "volume_cm3": float(h["Volume(cm3)"]) if "Volume(cm3)" in h else None,
                "size_bytes": os.path.getsize(path),
            }
            b = h.get("Bounds(mm)", "")
            m = BOUNDS.search(b)
            if m:
                rec["bmin"] = [float(x) for x in m.group(1).split(",")]
                rec["bmax"] = [float(x) for x in m.group(2).split(",")]
            meta = parts_list.get(bp)
            if meta:
                rec["kanji"] = meta["kanji"]
                rec["kana"] = meta["kana"]
                rec["en_list"] = meta["en"]
            if with_verts:
                rec["verts"] = count_verts(path)
            out.append(rec)

    dst = os.path.join(BASE, "bp3d_index.json")
    with open(dst, "w", encoding="utf-8", newline="") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("parts_list entries:", len(parts_list))
    print("OBJ indexed:", len(out))
    print("-> ", dst)


if __name__ == "__main__":
    main(with_verts="--verts" in sys.argv)
