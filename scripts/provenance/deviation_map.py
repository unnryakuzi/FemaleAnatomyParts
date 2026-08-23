# -*- coding: utf-8 -*-
"""製品メッシュの各頂点が BP3D の「面」からどれだけ離れているかを色分け画像にする。

頂点間距離だと BP3D 側が疎な分だけ過大に出るので、点→三角形の厳密距離を使う。
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REFS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "refs", "BodyParts3D_v4.0"))
OBJ_ISA = os.path.join(REFS, "obj_isa", "isa_BP3D_4.0_obj_99")
OUT = os.path.join(REFS, "deviation")

AXIS_PERM = (0, 2, 1)
AXIS_SIGN = (1, 1, -1)


def load_obj(path):
    V, F = [], []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                V.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("f "):
                idx = [int(w.split("/")[0]) - 1 for w in line.split()[1:]]
                for i in range(1, len(idx) - 1):
                    F.append((idx[0], idx[i], idx[i + 1]))
    V = np.array(V)
    V = np.stack([V[:, AXIS_PERM[j]] * AXIS_SIGN[j] for j in range(3)], axis=1)
    return V, np.array(F)


def point_tri_dist(P, A, B, C):
    """P(n,3) と 対応する三角形(n,3)x3 の厳密距離。"""
    AB, AC, AP = B - A, C - A, P - A
    d1 = (AB * AP).sum(1); d2 = (AC * AP).sum(1)
    BP = P - B
    d3 = (AB * BP).sum(1); d4 = (AC * BP).sum(1)
    CP = P - C
    d5 = (AB * CP).sum(1); d6 = (AC * CP).sum(1)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    denom = va + vb + vc
    v = np.zeros(len(P)); w = np.zeros(len(P))
    inside = denom > 1e-20
    v[inside] = vb[inside] / denom[inside]
    w[inside] = vc[inside] / denom[inside]
    # 領域外はクランプ（辺・頂点へ落とす近似だが十分実用的）
    v = np.clip(v, 0, 1); w = np.clip(w, 0, 1)
    over = (v + w) > 1
    scale = np.where(over, v + w, 1.0)
    v = v / scale; w = w / scale
    Q = A + v[:, None] * AB + w[:, None] * AC
    return np.linalg.norm(P - Q, axis=1)


def dist_to_surface(P, V, F, k=24):
    cent = V[F].mean(1)
    tree = cKDTree(cent)
    _, idx = tree.query(P, k=min(k, len(F)))
    best = np.full(len(P), np.inf)
    for j in range(idx.shape[1]):
        tri = F[idx[:, j]]
        d = point_tri_dist(P, V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]])
        best = np.minimum(best, d)
    return best


def norm_to(A, ref_lo, ref_hi):
    c = (ref_lo + ref_hi) / 2.0
    s = (ref_hi - ref_lo).max()
    return (A - c) / s, s


def run(pname, bp_file, prod_verts, title):
    V, F = load_obj(os.path.join(OBJ_ISA, bp_file))
    P = np.array(prod_verts, dtype=float)
    # BP3D の bbox を基準に両者を正規化（位置・全体スケールの差を除去）
    lo, hi = V.min(0), V.max(0)
    Vn, mm = norm_to(V, lo, hi)
    plo, phi = P.min(0), P.max(0)
    Pn, _ = norm_to(P, plo, phi)
    d = dist_to_surface(Pn, Vn, F) * mm      # mm 換算

    fig = plt.figure(figsize=(13, 4.6))
    views = [("front (X-Z)", 0, 2), ("side (Y-Z)", 1, 2), ("top (X-Y)", 0, 1)]
    vmax = float(np.percentile(d, 98))
    for i, (label, a, b) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1)
        o = np.argsort(d)
        sc = ax.scatter(Pn[o, a], Pn[o, b], c=d[o], s=1.2, cmap="turbo",
                        vmin=0, vmax=vmax, linewidths=0)
        ax.set_aspect("equal"); ax.set_title(label, fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
    cb = fig.colorbar(sc, ax=fig.axes, fraction=0.02, pad=0.01)
    cb.set_label("distance to BodyParts3D surface (mm)", fontsize=8)
    fig.suptitle("%s   median=%.2fmm  95%%=%.2fmm  max=%.2fmm   (product %d verts / BP3D %d verts)"
                 % (title, np.median(d), np.percentile(d, 95), d.max(), len(P), len(V)),
                 fontsize=10)
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "%s.png" % title)
    fig.savefig(dst, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("%-26s median=%6.2f  95%%=%6.2f  max=%7.2f mm  -> %s"
          % (title, np.median(d), np.percentile(d, 95), d.max(), os.path.basename(dst)))
    return d


PAIRS = [
    ("下顎骨(かがくこつ)", None, "mandible"),
    ("右上腕骨(みぎじょうわんこつ)", None, "humerus_R"),
    ("右肩甲骨(みぎけんこうこつ)", None, "scapula_R"),
    ("右大胸筋胸肋部(みぎだいきょうきんきょうろくぶ)", None, "pectoralis_major_sternocostal_R"),
    ("右小胸筋(みぎしょうきょうきん)", None, "pectoralis_minor_R"),
    ("右腓腹筋外側頭(みぎひふくきんがいそくとう)", None, "gastrocnemius_lat_R"),
]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    idx = json.load(open(os.path.join(REFS, "bp3d_index.json"), encoding="utf-8"))
    by_en = {r["en"].lower(): r for r in idx if r["tree"] == "isa"}
    fallback = {
        "右上腕骨(みぎじょうわんこつ)": "right humerus",
        "右肩甲骨(みぎけんこうこつ)": "right scapula",
        "下顎骨(かがくこつ)": "mandible",
        "右腓腹筋外側頭(みぎひふくきんがいそくとう)": "lateral head of right gastrocnemius",
        "右大胸筋胸肋部(みぎだいきょうきんきょうろくぶ)": "sternocostal part of right pectoralis major",
        "右小胸筋(みぎしょうきょうきん)": "right pectoralis minor",
    }
    prod = json.load(open(os.path.join(REFS, "sample_verts.json"), encoding="utf-8"))
    for pname, bpf, title in PAIRS:
        if bpf is None:
            bpf = by_en[fallback[pname]]["file"]
        run(pname, bpf, prod[pname], title)
    print("\n出力先:", OUT)
