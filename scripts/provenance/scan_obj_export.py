# -*- coding: utf-8 -*-
"""配布OBJ(書き出し済み)をストリーミング走査し、オブジェクトごとの
頂点数・bbox・重心を JSON に出す。Blender を起動せずに幾何を測るため。
"""
import json
import os
import sys


def scan(path, dst):
    cur = None
    recs = []

    def flush():
        if cur and cur["verts"]:
            n = cur["verts"]
            cur["centroid"] = [cur["sum"][i] / n for i in range(3)]
            del cur["sum"]
            recs.append(cur)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                if cur is None:
                    continue
                p = line.split()
                x, y, z = float(p[1]), float(p[2]), float(p[3])
                cur["verts"] += 1
                bmin, bmax, s = cur["bmin"], cur["bmax"], cur["sum"]
                for i, val in enumerate((x, y, z)):
                    if val < bmin[i]:
                        bmin[i] = val
                    if val > bmax[i]:
                        bmax[i] = val
                    s[i] += val
            elif line.startswith("o "):
                flush()
                cur = {"name": line[2:].strip(), "verts": 0,
                       "bmin": [1e30] * 3, "bmax": [-1e30] * 3,
                       "sum": [0.0] * 3, "faces": 0}
            elif line.startswith("f "):
                if cur is not None:
                    cur["faces"] += 1
    flush()

    with open(dst, "w", encoding="utf-8", newline="") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)
    print("objects:", len(recs), "-> ", dst)


if __name__ == "__main__":
    scan(sys.argv[1], sys.argv[2])
