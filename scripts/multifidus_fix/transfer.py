# 男性 Man_All の多裂筋を、周りのパーツの男性→女性の変位で女性マスターへ移す（システムの Python。scipy を使う）
#  handoff_muscle_idmap_20261013\scripts\12_transfer.py と同じ方法（近くの対応点 K 個の重み付き平均 → 辺に沿って平滑化）
#  対応点から外すもの: 多裂筋そのもの（女性側が上へ伸びている＝直す対象）と、周りと 35mm 以上食い違うパーツ
# python transfer.py <work dir> [all|bone]
import sys, json, numpy as np
from scipy.spatial import cKDTree
W = sys.argv[1]; MODE = sys.argv[2] if len(sys.argv) > 2 else "all"; K, E, SM = 24, 0.002, 20
mj = json.load(open(W + "/male.json", encoding="utf-8")); fj = json.load(open(W + "/female.json", encoding="utf-8"))
m, f = mj["meta"], fj["meta"]; M = np.load(W + "/male.npz"); F = np.load(W + "/female.npz")
TARGET = ("右多裂筋", "左多裂筋")
same = [k for k in f if k in m and m[k]["n"] == f[k]["n"] and m[k]["sig"] == f[k]["sig"] and k not in TARGET]
if MODE == "bone":
    same = [k for k in same if "骨格" in f[k]["cols"] and any(x in k for x in ("椎", "仙骨", "尾骨", "後頭骨", "肋骨"))]
P = np.concatenate([M["p_%d" % m[k]["slot"]] for k in same]).astype(np.float64)
D = np.concatenate([F["p_%d" % f[k]["slot"]] - M["p_%d" % m[k]["slot"]] for k in same]).astype(np.float64)
Lb = np.concatenate([np.full(len(M["p_%d" % m[k]["slot"]]), t) for t, k in enumerate(same)]); tree = cKDTree(P); bad = []
for t, k in enumerate(same):
    ii = np.where(Lb == t)[0]; ii = ii[:: max(1, len(ii) // 200)]; dev = []
    for q, nb in zip(ii, tree.query_ball_point(P[ii], 0.03)):
        nb = [x for x in nb if Lb[x] != t]
        if len(nb) >= 5: dev.append(np.linalg.norm(D[q] - np.median(D[nb], 0)))
    if dev and np.median(dev) > 0.035: bad.append((k, round(float(np.median(dev)) * 1000, 1)))
print("mode", MODE, "対応パーツ", len(same), "外した（周りとの食い違い mm）", bad)
keep = ~np.isin(Lb, [same.index(k) for k, _ in bad]); P, D = P[keep], D[keep]; tree = cKDTree(P)
out, rep = {}, []
# 女性の左多裂筋は右の鏡像（頂点番号ごとに一致）。男性の左は頂点数が違うので、男性の右を鏡に映したものを左として移す
for k in TARGET:
    s = mj["full"]["右多裂筋"]; w = M["w_%d" % s].astype(np.float64); e = M["e_%d" % s]
    if k == "左多裂筋": w = w * np.array([-1.0, 1.0, 1.0])
    assert m["右多裂筋"]["n"] == f[k]["n"] and m["右多裂筋"]["sig"] == f[k]["sig"], k   # 女性の多裂筋と同じ頂点の並び（頂点カラー等をそのまま使える）
    d, j = tree.query(w, K); wt = 1.0 / (d ** 2 + E ** 2); dv = (D[j] * wt[..., None]).sum(1) / wt.sum(1)[:, None]
    raw = dv.copy(); n = len(w); deg = np.bincount(e.ravel(), minlength=n).astype(np.float64)
    for _ in range(SM):
        acc = np.zeros_like(dv); np.add.at(acc, e[:, 0], dv[e[:, 1]]); np.add.at(acc, e[:, 1], dv[e[:, 0]])
        nb = np.where(deg[:, None] > 0, acc / np.maximum(deg, 1)[:, None], dv); dv = 0.5 * dv + 0.5 * nb
    new = w + dv; out[k] = new.astype(np.float32)
    fs = fj["full"][k]; old = F["w_%d" % fs]
    rep.append(dict(part=k, n=n, nn_mm=round(float(np.median(d[:, 0])) * 1000, 1), z_new=[round(new[:, 2].min() * 1000), round(new[:, 2].max() * 1000)],
                    z_old=[round(float(old[:, 2].min()) * 1000), round(float(old[:, 2].max()) * 1000)],
                    move_median_mm=round(float(np.median(np.linalg.norm(new - old, axis=1))) * 1000, 1), move_max_mm=round(float(np.linalg.norm(new - old, axis=1).max()) * 1000, 1)))
np.savez_compressed(W + "/multifidus_new_%s.npz" % MODE, **out)
for r in rep: print(r)
print("左 と 右の鏡像 の差 mm: median %.1f max %.1f" % tuple(np.percentile(np.linalg.norm(out["左多裂筋"] - out["右多裂筋"] * np.array([-1, 1, 1], np.float32), axis=1), [50, 100]) * 1000))
