# -*- coding: utf-8 -*-
""".obj / .mtl の先頭に 2026-10 ライセンスの識別コメントを入れる（OBJ はカスタムプロパティを持てないため）。

  python scripts/listing/stamp_obj.py <in.obj> <out.obj> [--mtl-rename OLD.mtl NEW.mtl]

本体は1行も変えない（mtllib 行のファイル名だけ、指定があれば差し替える）。数GBあるのでストリームで写す。
"""
import shutil
import sys

from apply_license_mark import MARK_ID

HEADER = [
    "# Kabe-Tech license %s" % MARK_ID,
    "# Adapted from BodyParts3D (c) The Database Center for Life Science, CC BY 4.0.",
    "# Redistribution, resale or sharing of this model data is prohibited. See LICENSE.txt.",
]


def stamp(src, dst, rename=None):
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        fo.write(("\n".join(HEADER) + "\n").encode("utf-8"))
        n = 0
        for line in fi:
            if rename and n < 50 and line.startswith(b"mtllib "):
                line = line.replace(rename[0].encode("utf-8"), rename[1].encode("utf-8"))
            fo.write(line)
            n += 1
            if n == 50:
                shutil.copyfileobj(fi, fo, 64 * 1024 * 1024)
                break
    print("[stamp_obj] %s" % dst)


if __name__ == "__main__":
    a = sys.argv[1:]
    rename = (a[3], a[4]) if len(a) >= 5 and a[2] == "--mtl-rename" else None
    stamp(a[0], a[1], rename)
