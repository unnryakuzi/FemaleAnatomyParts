# 腹横筋の上の部分を肋骨のかごの内側へ戻す（システムの Python）
#  女性版は下の肋骨を細くしてあり（横 0.81〜0.85倍）、外腹斜筋に合わせて移した腹横筋が下の肋骨の外側に出ていた（男性は内側）。
#  男性の腹横筋の各頂点を、近くの肋骨・肋軟骨・胸骨それぞれの男性→女性の変換（女性版では骨ごとのアフィン、残差 ~1mm）で動かし、
#  近い骨ほど重く混ぜる（σ=20mm）。肋骨から 15mm 以内は全部この位置、45mm でコサインで今の形へ戻す。お腹の中ほど・下は今の形のまま
# python ta_rib_skin.py <work/wc（男性）> <work/after2（女性の今）> <出力 npz> [σ mm=20] [d0 mm=15] [d1 mm=45]
import sys, json, numpy as np
from scipy.spatial import cKDTree
WM, WF, OUT = sys.argv[1:4]
SIG = float(sys.argv[4]) / 1000 if len(sys.argv) > 4 else 0.020
D0 = float(sys.argv[5]) / 1000 if len(sys.argv) > 5 else 0.015
D1 = float(sys.argv[6]) / 1000 if len(sys.argv) > 6 else 0.045
mj = json.load(open(WM + "/male.json", encoding="utf-8")); M = np.load(WM + "/male.npz")
fj = json.load(open(WF + "/female.json", encoding="utf-8")); F = np.load(WF + "/female.npz")
def is_cage(k):
    return (("肋骨" in k or "肋軟骨" in k) and "挙筋" not in k) or any(s in k for s in ("胸骨", "剣状突起"))
bones = [k for k in mj["meta"] if is_cage(k) and k in fj["meta"] and mj["meta"][k]["n"] == fj["meta"][k]["n"] and mj["meta"][k]["sig"] == fj["meta"][k]["sig"]]
T, P, L = {}, [], []
for k in sorted(bones):
    X = M["p_%d" % mj["meta"][k]["slot"]].astype(float); Y = F["p_%d" % fj["meta"][k]["slot"]].astype(float)
    Xh = np.c_[X, np.ones(len(X))]; A, *_ = np.linalg.lstsq(Xh, Y, rcond=None); T[k] = A
    r = np.linalg.norm(Xh @ A - Y, axis=1) * 1000
    P.append(X); L += [k] * len(X)
    if np.median(r) > 2: print("残差が大きい骨", k, round(float(np.median(r)), 1))
P = np.concatenate(P); L = np.array(L); tree = cKDTree(P); names = sorted(T); idx = {k: i for i, k in enumerate(names)}
print("肋骨・肋軟骨・胸骨", len(names))
out = {}
for side in ("右", "左"):
    k = side + "腹横筋"
    X = M["w_%d" % mj["full"][k]].astype(float); cur = F["w_%d" % fj["full"][k]].astype(float)
    d, j = tree.query(X, 64, distance_upper_bound=0.08)
    Wt = np.zeros((len(X), len(names))); r = np.arange(len(X))
    for c in range(d.shape[1]):
        ok = np.isfinite(d[:, c])
        li = np.array([idx[L[jj]] if o else 0 for jj, o in zip(j[:, c], ok)])
        w = np.where(ok, np.exp(-(np.where(ok, d[:, c], 1) / SIG) ** 2), 0.0)
        Wt[r, li] = np.maximum(Wt[r, li], w)
    s = Wt.sum(1); has = s > 1e-12
    Xh = np.c_[X, np.ones(len(X))]
    skin = cur.copy()
    Wn = Wt[has] / s[has, None]
    skin[has] = sum(Wn[:, i:i + 1] * (Xh[has] @ T[kk]) for kk, i in idx.items())
    dmin = np.where(np.isfinite(d[:, 0]), d[:, 0], 1.0)
    t = np.clip((dmin - D0) / (D1 - D0), 0, 1); b = (1 + np.cos(np.pi * t)) / 2; b[~has] = 0
    new = cur + b[:, None] * (skin - cur)
    out[k] = new.astype(np.float32)
    mv = np.linalg.norm(new - cur, axis=1) * 1000
    print(k, "動いた頂点 %d / %d（肋骨に合わせた %d）  移動 中央値 %.1f mm / 最大 %.1f mm" % ((mv > 0.1).sum(), len(mv), (b > 0.999).sum(), np.median(mv[mv > 0.1]) if (mv > 0.1).any() else 0, mv.max()))
np.savez_compressed(OUT, **out)
