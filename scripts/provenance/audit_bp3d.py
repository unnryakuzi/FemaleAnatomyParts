# -*- coding: utf-8 -*-
"""製品メッシュ全939個を BodyParts3D v4.0 へ幾何のみで突合し、監査CSVを出す。

名前（英訳・和名）は人が付けたものなので、証拠としては幾何を主にする。
match_geometry.py が推定した相似変換で BP3D を製品座標へ載せ、
bbox中心・bboxサイズの近さで最良候補を選ぶ。
"""
import csv
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
REFS = os.path.join(ROOT, "refs", "BodyParts3D_v4.0")


def main():
    rep = json.load(open(os.path.join(REFS, "match_report.json"), encoding="utf-8"))
    T = rep["transform"]
    perm, signs, s, t = T["perm"], T["signs"], T["scale"], T["translate"]

    bp = [r for r in json.load(open(os.path.join(REFS, "bp3d_index.json"),
                                    encoding="utf-8")) if "bmin" in r]
    man = json.load(open(os.path.join(REFS, "man_geom.json"), encoding="utf-8"))

    def xf(p):
        return np.array([s * p[perm[j]] * signs[j] + t[j] for j in range(3)])

    bc = np.array([xf([(r["bmin"][i] + r["bmax"][i]) / 2 for i in range(3)]) for r in bp])
    bs = np.array([sorted(abs(r["bmax"][i] - r["bmin"][i]) * s for i in range(3))
                   for r in bp])

    # 名前一致の結果を答え合わせ用に持っておく
    named = {r["name"]: r for r in rep["matched"]}

    rows = []
    for m in man:
        c = np.array([(m["bmin"][i] + m["bmax"][i]) / 2 for i in range(3)])
        sz = np.array(sorted(m["bmax"][i] - m["bmin"][i] for i in range(3)))
        d = np.linalg.norm(bc - c, axis=1)
        # サイズ比の対数差（大きさの合わない候補を弾く）
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.abs(np.log((sz + 1e-9) / (bs + 1e-9))).mean(axis=1)
        score = d + 0.05 * lr          # 位置が主、サイズは補助
        k = int(np.argmin(score))
        r = bp[k]
        ratio = float(np.mean(sz / (bs[k] + 1e-12)))
        nm = named.get(m["name"])
        rows.append({
            "object": m["name"],
            "verts": m["verts"],
            "faces": m["faces"],
            "bp3d_file": r["file"],
            "bp3d_tree": r["tree"],
            "bp3d_id": r["bp"],
            "fma_id": r["fma"],
            "bp3d_en": r["en"],
            "center_dist_mm": round(float(d[k]) * 1000, 2),
            "size_ratio": round(ratio, 3),
            "name_match": "yes" if nm else "no",
            "name_agrees": ("yes" if nm and nm["bp_file"] == r["file"]
                            else ("no" if nm else "")),
        })

    def verdict(r):
        if r["object"].startswith("下着_"):
            return "自作(製品固有)"
        if r["center_dist_mm"] <= 25 and 0.85 <= r["size_ratio"] <= 1.18:
            return "BP3D由来(強)"
        if r["center_dist_mm"] <= 60 and 0.7 <= r["size_ratio"] <= 1.45:
            return "BP3D由来(可)"
        return "要確認"

    for r in rows:
        r["verdict"] = verdict(r)

    dst = os.path.join(ROOT, "refs", "provenance_audit.csv")
    with open(dst, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    import collections
    cnt = collections.Counter(r["verdict"] for r in rows)
    print("=== 判定内訳 (全%d オブジェクト) ===" % len(rows))
    for k, v in cnt.most_common():
        print("  %-16s %4d  (%.1f%%)" % (k, v, 100 * v / len(rows)))
    agree = [r for r in rows if r["name_agrees"] == "yes"]
    named_n = [r for r in rows if r["name_match"] == "yes"]
    print("\n名前照合と幾何照合が同じBP3Dパーツを指した: %d / %d (%.1f%%)"
          % (len(agree), len(named_n), 100 * len(agree) / max(1, len(named_n))))
    print("\n=== 要確認の一覧 ===")
    for r in rows:
        if r["verdict"] == "要確認":
            print("  %-38s dist=%7.1fmm ratio=%.2f  最近傍=%s"
                  % (r["object"][:36], r["center_dist_mm"], r["size_ratio"],
                     r["bp3d_en"][:34]))
    print("\n-> ", dst)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
