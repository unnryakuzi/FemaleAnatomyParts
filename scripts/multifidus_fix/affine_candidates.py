# 欠けていたパーツを「男性の形の相似形（アフィン）」で女性へ置く候補を作る（システムの Python）
#  A: 周りの“頂点が男性版のまま”の女性パーツが使っている変換グループ G（女性の matrix_world × 男性の逆行列）を、
#     近さで多数決して1つ選び、そのまま掛ける（女性版を作ったときと同じ規則）
#  B: transfer_parts.py の結果（周りの変形を頂点ごとに写した形）に、最小二乗でいちばん合う1つのアフィン変換を掛ける
# python affine_candidates.py <work/wc> <pure.npz> <d_master.json> <d_man.json> <出力 dir>
import sys, json, collections, numpy as np
from scipy.spatial import cKDTree
W, PURE, DMA, DMN, OUT = sys.argv[1:6]
mj = json.load(open(W + "/male.json", encoding="utf-8")); fj = json.load(open(W + "/female.json", encoding="utf-8"))
M = np.load(W + "/male.npz"); PU = np.load(PURE)
ma = json.load(open(DMA, encoding="utf-8"))["objs"]; mn = json.load(open(DMN, encoding="utf-8"))["objs"]
# 頂点が男性と同じ女性パーツの G
G, gid, gl = {}, {}, []
for n, o in ma.items():
    if o["type"] != "MESH" or n not in mn or o["cohash"] != mn[n]["cohash"]: continue
    g = np.array(o["M"]) @ np.linalg.inv(np.array(mn[n]["M"])); key = tuple(np.round(g[:3, :4].ravel(), 4))
    if key not in gid: gid[key] = len(gl); gl.append(g)
    G[n.split("(")[0]] = gid[key]
print("グループ", len(gl), "対象パーツ（頂点が男性と同じ）", len(G))
# 男性空間の近傍（間引き点）に、その点のパーツのグループ番号を付ける
P_, L_ = [], []
for k, mt in mj["meta"].items():
    b = k.split("#")[0]
    if b in G and b not in fj["full"]:
        p = M["p_%d" % mt["slot"]]; P_.append(p); L_.append(np.full(len(p), G[b]))
P_ = np.concatenate(P_).astype(np.float64); L_ = np.concatenate(L_); tree = cKDTree(P_)
outA, outB, rep = {}, {}, {}
for k in PU.files:
    src, mir = k, 1.0
    if not (mj["meta"][k]["n"] == fj["meta"][k]["n"] and mj["meta"][k]["sig"] == fj["meta"][k]["sig"]):
        src, mir = ("左" if k[0] == "右" else "右") + k[1:], -1.0
    X = M["w_%d" % mj["full"][src]].astype(np.float64) * np.array([mir, 1, 1])
    # A: 近さで多数決（各頂点の 8mm 以内の点のグループ）
    Xs = X[:: max(1, len(X) // 4000)]
    hits = tree.query_ball_point(Xs, 0.008)
    votes = collections.Counter(int(L_[j]) for h in hits for j in h)
    if not votes:
        d, j = tree.query(Xs, 8); votes = collections.Counter(int(x) for x in L_[j].ravel())
    tot = sum(votes.values()); top = votes.most_common(3)
    g = gl[top[0][0]]
    # 男性ワールド → 女性ワールド: G は (女性 M) @ inv(男性 M)。鏡像の左多裂筋は、右の鏡像点に G をそのまま掛ける
    A = X @ g[:3, :3].T + g[:3, 3]; outA[k] = A.astype(np.float32)
    # B: 最小二乗アフィン
    Y = PU[k].astype(np.float64); Xh = np.c_[X, np.ones(len(X))]; T, *_ = np.linalg.lstsq(Xh, Y, rcond=None)
    Bv = Xh @ T; outB[k] = Bv.astype(np.float32)
    det = np.linalg.det(T[:3, :3])
    rep[k] = dict(A_votes=[(i, round(c / tot * 100)) for i, c in top], A_scale=np.linalg.norm(g[:3, :3], axis=0).round(3).tolist(),
                  B_det=round(float(det), 3), B_scale=np.linalg.norm(T[:3, :3], axis=0).round(3).tolist(),
                  B_resid_mm=[round(float(x) * 1000, 1) for x in np.percentile(np.linalg.norm(Bv - Y, axis=1), [50, 95, 100])],
                  A_vs_pure_mm=[round(float(x) * 1000, 1) for x in np.percentile(np.linalg.norm(A - Y, axis=1), [50, 95, 100])])
    print(k, rep[k])
np.savez_compressed(OUT + "/candA.npz", **outA); np.savez_compressed(OUT + "/candB.npz", **outB)
json.dump(dict(groups=[g[:3, :4].round(5).tolist() for g in gl], parts=rep), open(OUT + "/affine_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
