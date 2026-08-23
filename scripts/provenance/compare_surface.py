# -*- coding: utf-8 -*-
"""製品メッシュとBP3D _99メッシュの「面としての一致度」を測る。

各パーツ単位で bbox 中心・スケールを合わせたうえで、
  A) BP3D頂点 -> 製品頂点 の最近傍距離   (BP3Dの面が製品の面上にあるか)
  B) 製品頂点 -> BP3D頂点 の最近傍距離   (製品に BP3D に無い張り出しがあるか)
を出す。A が小さければ同一表面、B が大きければ製品側に独自の細部がある。
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

REFS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "refs", "BodyParts3D_v4.0"))
OBJ_ISA = os.path.join(REFS, "obj_isa", "isa_BP3D_4.0_obj_99")

PAIRS = {
    "下顎骨(かがくこつ)": "Mandible",
    "右肩甲骨(みぎけんこうこつ)": "Right scapula",
    "右上腕骨(みぎじょうわんこつ)": "Right humerus",
    "右大胸筋胸肋部(みぎだいきょうきんきょうろくぶ)": "Sternocostal part of right pectoralis major",
    "右小胸筋(みぎしょうきょうきん)": "Right pectoralis minor",
    "右腓腹筋外側頭(みぎひふくきんがいそくとう)": "Lateral head of right gastrocnemius",
}


def load_bp3d_verts(path):
    v = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                v.append((float(p[1]), float(p[2]), float(p[3])))
    return np.array(v)


AXIS_PERM = (0, 2, 1)      # match_geometry.py が推定した BP3D->製品 の軸対応
AXIS_SIGN = (1, 1, -1)


def to_product_axes(a):
    """BP3D(mm, z-up) を製品OBJの軸並びへ入れ替える。"""
    return np.stack([a[:, AXIS_PERM[j]] * AXIS_SIGN[j] for j in range(3)], axis=1)


def norm(a):
    """bbox中心を原点へ、最大辺を1へ。位置と全体スケールの違いを除去する。"""
    lo, hi = a.min(0), a.max(0)
    c = (lo + hi) / 2.0
    s = (hi - lo).max()
    return (a - c) / s, s


def main():
    idx = json.load(open(os.path.join(REFS, "bp3d_index.json"), encoding="utf-8"))
    by_en = {}
    for r in idx:
        if r["tree"] == "isa":
            by_en.setdefault(r["en"].lower(), r)
    prod = json.load(open(os.path.join(REFS, "sample_verts.json"), encoding="utf-8"))

    print("%-32s %8s %8s | %-9s %-9s | %-9s %-9s" %
          ("パーツ", "製品v", "BP3Dv", "A中央値", "A 95%", "B中央値", "B 95%"))
    print("-" * 100)
    for pname, en in PAIRS.items():
        r = by_en.get(en.lower())
        if r is None or pname not in prod:
            print("スキップ:", pname, en)
            continue
        P = np.array(prod[pname], dtype=float)
        B = to_product_axes(load_bp3d_verts(os.path.join(OBJ_ISA, r["file"])))
        Pn, Ps = norm(P)
        Bn, Bs = norm(B)
        # 実寸(mm)に戻すため BP3D の最大辺長を使う
        mm = Bs
        ta = cKDTree(Pn)
        tb = cKDTree(Bn)
        da, _ = ta.query(Bn)          # A: BP3D -> 製品
        db, _ = tb.query(Pn)          # B: 製品 -> BP3D
        da *= mm
        db *= mm
        print("%-32s %8d %8d | %8.3f %8.3f | %8.3f %8.3f" %
              (pname[:30], len(P), len(B),
               np.median(da), np.percentile(da, 95),
               np.median(db), np.percentile(db, 95)))
    print("\n単位: mm（BP3Dのbbox最大辺で実寸換算）")
    print("A = BP3D頂点から製品面までの距離 / B = 製品頂点からBP3D面までの距離")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
