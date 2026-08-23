# -*- coding: utf-8 -*-
"""巨大な配布OBJから、指定オブジェクトの頂点だけを抜き出して npy/json に保存する。"""
import json
import os
import re
import sys

def extract(path, targets, dst):
    want = set(targets)
    cur = None
    buf = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("o "):
                name = line[2:].strip()
                base = re.sub(r"\(.*?\)$", "", name).strip()
                cur = name if (name in want or base in want) else None
                if cur:
                    buf.setdefault(cur, [])
            elif cur and line.startswith("v "):
                p = line.split()
                buf[cur].append((float(p[1]), float(p[2]), float(p[3])))
    json.dump({k: v for k, v in buf.items()},
              open(dst, "w", encoding="utf-8", newline=""), ensure_ascii=False)
    for k, v in buf.items():
        print("  抽出 %s: %d 頂点" % (k, len(v)))
    print("-> ", dst)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    extract(sys.argv[1], sys.argv[3:], sys.argv[2])
