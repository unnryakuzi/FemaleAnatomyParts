# 多裂筋を椎骨に追従させて置く（システムの Python）
#  各椎骨（仙骨・腰椎・胸椎・頚椎）の男性→女性の変換（女性版では椎骨ごとの相似・アフィン、残差 ~0）を、
#  多裂筋の頂点ごとに「近い椎骨ほど重い」ガウス重み（距離 σ）で混ぜる（線形ブレンド）。形は男性の多裂筋のまま、椎骨の並びに沿って曲がる
#  女性の左多裂筋は右の鏡像なので、男性の右を鏡に映して同じ変換を掛ける
# python multifidus_skin.py <work/wc> <出力 npz> [σ mm=15]
import sys, json, numpy as np
from scipy.spatial import cKDTree
W, OUT = sys.argv[1:3]; SIG = float(sys.argv[3]) / 1000 if len(sys.argv) > 3 else 0.015
mj = json.load(open(W + "/male.json", encoding="utf-8")); fj = json.load(open(W + "/female.json", encoding="utf-8"))
M = np.load(W + "/male.npz"); F = np.load(W + "/female.npz")
vert = [k for k in mj["meta"] if any(s in k for s in ("頚椎", "胸椎", "腰椎", "仙骨", "環椎", "軸椎", "隆椎")) and "円板" not in k
        and k in fj["meta"] and mj["meta"][k]["n"] == fj["meta"][k]["n"] and mj["meta"][k]["sig"] == fj["meta"][k]["sig"]]
T, P, L = {}, [], []
for k in sorted(vert):
    X = M["p_%d" % mj["meta"][k]["slot"]].astype(float); Y = F["p_%d" % fj["meta"][k]["slot"]].astype(float)
    Xh = np.c_[X, np.ones(len(X))]; A, *_ = np.linalg.lstsq(Xh, Y, rcond=None); T[k] = A
    P.append(X); L += [k] * len(X)
P = np.concatenate(P); L = np.array(L); tr = cKDTree(P); names = sorted(T); idx = {k: i for i, k in enumerate(names)}
print("椎骨", len(names))
def skin(X):
    d, j = tr.query(X, 48); Wt = np.zeros((len(X), len(names))); r = np.arange(len(X))
    for c in range(d.shape[1]):
        li = np.array([idx[x] for x in L[j[:, c]]]); Wt[r, li] = np.maximum(Wt[r, li], np.exp(-(d[:, c] / SIG) ** 2))
    Wt /= np.maximum(Wt.sum(1, keepdims=True), 1e-300)
    Xh = np.c_[X, np.ones(len(X))]
    return sum(Wt[:, i:i + 1] * (Xh @ T[k]) for k, i in idx.items())
Xr = M["w_%d" % mj["full"]["右多裂筋"]].astype(float)
out = {"右多裂筋": skin(Xr).astype(np.float32), "左多裂筋": skin(Xr * np.array([-1.0, 1, 1])).astype(np.float32)}
for k, v in out.items(): print(k, "z %.3f..%.3f" % (v[:, 2].min(), v[:, 2].max()))
np.savez_compressed(OUT, **out)
