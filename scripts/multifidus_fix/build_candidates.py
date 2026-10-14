# パーツごとに「男性の形をそのまま置く変換（アフィン）」の候補を集める（システムの Python）
#  候補 = 女性版の変換グループ12個 ＋ 周り（男性空間で 10mm 以内）の既存パーツそれぞれの男性→女性アフィン ＋ 周りの変形への当てはめ（B）
#  伸び縮みが 0.75〜1.3 倍を外れる候補は捨てる。周りの変形で移した形（pure）との中央値のずれも付ける
# python build_candidates.py <work/wc> <pure.npz> <affine_report.json> <対象 base 名 json> <出力 json>
import sys, json, numpy as np
from scipy.spatial import cKDTree
W, PURE, AREP, TJ, OUT = sys.argv[1:6]
mj = json.load(open(W + "/male.json", encoding="utf-8")); fj = json.load(open(W + "/female.json", encoding="utf-8"))
M = np.load(W + "/male.npz"); F = np.load(W + "/female.npz"); PU = np.load(PURE)
groups = [np.vstack([np.array(g), [0, 0, 0, 1]]) for g in json.load(open(AREP, encoding="utf-8"))["groups"]]
targets = json.load(open(TJ, encoding="utf-8")); skip = set(fj["full"])           # 足したパーツと多裂筋は周りに数えない
def fit(X, Y):
    Xh = np.c_[X, np.ones(len(X))]; T, *_ = np.linalg.lstsq(Xh, Y, rcond=None)
    A = np.eye(4); A[:3, :3] = T[:3].T; A[:3, 3] = T[3]
    return A, np.linalg.norm(Xh @ T - Y, axis=1)
# 既存パーツ（頂点数・並びが男女同じ）ごとの男性→女性アフィン
nb_T, nb_P, nb_L = {}, [], []
for k, a in mj["meta"].items():
    if k in skip or k not in fj["meta"]: continue
    b = fj["meta"][k]
    if a["n"] != b["n"] or a["sig"] != b["sig"]: continue
    X = M["p_%d" % a["slot"]].astype(float); Y = F["p_%d" % b["slot"]].astype(float)
    A, r = fit(X, Y)
    if np.median(r) > 0.003: continue                                             # アフィンで説明できない（大きく手で編集された）ものは使わない
    nb_T[k] = A; nb_P.append(X); nb_L += [k] * len(X)
nb_P = np.concatenate(nb_P); nb_L = np.array(nb_L); tree = cKDTree(nb_P)
print("周りに使える既存パーツ", len(nb_T))
def ok(A):
    s = np.linalg.svd(A[:3, :3], compute_uv=False); return s.min() > 0.75 and s.max() < 1.3 and np.linalg.det(A[:3, :3]) > 0
out = {}
for k in targets:
    src, mir = k, 1.0
    if not (mj["meta"][k]["n"] == fj["meta"][k]["n"] and mj["meta"][k]["sig"] == fj["meta"][k]["sig"]):
        src, mir = ("左" if k[0] == "右" else "右") + k[1:], -1.0
    X = M["w_%d" % mj["full"][src]].astype(float) * np.array([mir, 1, 1]); Y = PU[k].astype(float)
    Xs = X[:: max(1, len(X) // 3000)]
    near = sorted({nb_L[j] for h in tree.query_ball_point(Xs, 0.010) for j in h})
    cands = [("G%d" % i, g) for i, g in enumerate(groups)] + [("nb:" + n, nb_T[n]) for n in near]
    A_b, _ = fit(X, Y); cands.append(("B", A_b))
    lst = []
    for name, A in cands:
        if not ok(A): continue
        Z = X @ A[:3, :3].T + A[:3, 3]; dev = np.linalg.norm(Z - Y, axis=1) * 1000
        lst.append(dict(id=name, T=A.round(7).tolist(), dev_med=round(float(np.median(dev)), 1), dev_p90=round(float(np.percentile(dev, 90)), 1),
                        sv=[round(float(x), 3) for x in np.linalg.svd(A[:3, :3], compute_uv=False)]))
    # 同じ変換の重複を除く
    seen, uniq = [], []
    for c in sorted(lst, key=lambda c: c["dev_med"]):
        T = np.array(c["T"])
        if any(np.abs(T - s).max() < 2e-4 for s in seen): continue
        seen.append(T); uniq.append(c)
    out[k] = dict(src=src, mirror=mir < 0, cands=uniq)
    print(k, "候補", len(uniq), "近い順", [(c["id"][:14], c["dev_med"]) for c in uniq[:5]])
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
