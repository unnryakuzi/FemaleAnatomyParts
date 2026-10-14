# 男性 Man_All のパーツを、周りの男性→女性の変位で女性マスターへ移す（transfer.py の一般版。システムの Python）
#  対応点から外すもの: 移す対象そのもの・v1.68.0 で足した43個（変形を移して作ったもので、元の対応ではない）・多裂筋・周りと 35mm 以上食い違うパーツ
# python transfer_parts.py <work dir> <out.npz> <除外する名前の json> <対象の base 名 ...>
import sys, json, numpy as np
from scipy.spatial import cKDTree
W, OUT, EXJ = sys.argv[1:4]; TARGET = sys.argv[4:]; K, E, SM = 24, 0.002, 20
mj = json.load(open(W + "/male.json", encoding="utf-8")); fj = json.load(open(W + "/female.json", encoding="utf-8"))
m, f = mj["meta"], fj["meta"]; M = np.load(W + "/male.npz"); F = np.load(W + "/female.npz")
ex = {n.split("(")[0] for n in json.load(open(EXJ, encoding="utf-8"))} | {"右多裂筋", "左多裂筋"} | set(TARGET)
same = [k for k in f if k in m and m[k]["n"] == f[k]["n"] and m[k]["sig"] == f[k]["sig"] and k not in ex]
P = np.concatenate([M["p_%d" % m[k]["slot"]] for k in same]).astype(np.float64)
D = np.concatenate([F["p_%d" % f[k]["slot"]] - M["p_%d" % m[k]["slot"]] for k in same]).astype(np.float64)
Lb = np.concatenate([np.full(len(M["p_%d" % m[k]["slot"]]), t) for t, k in enumerate(same)]); tree = cKDTree(P); bad = []
for t, k in enumerate(same):
    ii = np.where(Lb == t)[0]; ii = ii[:: max(1, len(ii) // 200)]; dev = []
    for q, nb in zip(ii, tree.query_ball_point(P[ii], 0.03)):
        nb = [x for x in nb if Lb[x] != t]
        if len(nb) >= 5: dev.append(np.linalg.norm(D[q] - np.median(D[nb], 0)))
    if dev and np.median(dev) > 0.035: bad.append((k, round(float(np.median(dev)) * 1000, 1)))
print("対応パーツ", len(same), "外した（周りとの食い違い mm）", bad)
keep = ~np.isin(Lb, [same.index(k) for k, _ in bad]); P, D = P[keep], D[keep]; tree = cKDTree(P)
out = {}
for k in TARGET:
    src, mirror = k, False
    if not (m[k]["n"] == f[k]["n"] and m[k]["sig"] == f[k]["sig"]):
        # 女性の左多裂筋は右の鏡像（男性の左とは頂点数が違う）。反対側の男性パーツを鏡に映して使う
        opp = ("左" if k[0] == "右" else "右") + k[1:]
        assert m[opp]["n"] == f[k]["n"] and m[opp]["sig"] == f[k]["sig"], k
        src, mirror = opp, True
    s = mj["full"][src]; w = M["w_%d" % s].astype(np.float64); e = M["e_%d" % s]
    if mirror: w = w * np.array([-1.0, 1.0, 1.0])
    d, j = tree.query(w, K); wt = 1.0 / (d ** 2 + E ** 2); dv = (D[j] * wt[..., None]).sum(1) / wt.sum(1)[:, None]
    n = len(w); deg = np.bincount(e.ravel(), minlength=n).astype(np.float64)
    for _ in range(SM):
        acc = np.zeros_like(dv); np.add.at(acc, e[:, 0], dv[e[:, 1]]); np.add.at(acc, e[:, 1], dv[e[:, 0]])
        nb = np.where(deg[:, None] > 0, acc / np.maximum(deg, 1)[:, None], dv); dv = 0.5 * dv + 0.5 * nb
    new = w + dv; out[k] = new.astype(np.float32)
    old = F["w_%d" % fj["full"][k]] if k in fj["full"] else None
    print(k, "n", n, "nn_mm", round(float(np.median(d[:, 0])) * 1000, 1),
          "今の形との差 median/max mm", None if old is None else (round(float(np.median(np.linalg.norm(new - old, axis=1))) * 1000, 1), round(float(np.linalg.norm(new - old, axis=1).max()) * 1000, 1)))
np.savez_compressed(OUT, **out)
