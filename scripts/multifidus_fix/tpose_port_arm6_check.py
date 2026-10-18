# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 腕の6個の形を比べる（システムの Python）
#  折れ辺（隣の面の向きが120°以上違う辺）と、マスター（＝男性の形）に対する辺の長さの比。Tポーズへの回転では辺の長さは変わらないので、比が1から離れるのは形の歪み
# python tpose_port_arm6_check.py <面のあるダンプ dir（dump_parts.py の female.json/npz）> <plan.json> <ラベル=tpose_port_dump の接頭辞> ...
import sys, json, numpy as np
D, PLAN = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8")); SETS = [s.split("=", 1) for s in sys.argv[3:]]
fj = json.load(open(D + "/female.json", encoding="utf-8")); F = np.load(D + "/female.npz")
def tris(s):
    lv, ls, lt = F["fl_%d" % s], F["fs_%d" % s], F["ft_%d" % s]; out = []
    for k in range(3, int(lt.max()) + 1):
        sel = np.where(lt == k)[0]
        for j in range(1, k - 1): out.append(np.stack([lv[ls[sel]], lv[ls[sel] + j], lv[ls[sel] + j + 1]], 1))
    return np.concatenate(out)
def adj(T):
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); f = np.tile(np.arange(len(T)), 3)
    e.sort(1); key = e[:, 0].astype(np.int64) * 10**7 + e[:, 1]; o = np.argsort(key, kind="stable"); key = key[o]; f = f[o]
    same = key[1:] == key[:-1]; return f[:-1][same], f[1:][same]
def folds(W, T, A):
    n = np.cross(W[T[:, 1]] - W[T[:, 0]], W[T[:, 2]] - W[T[:, 0]]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-30)[:, None]
    return int(((n[A[0]] * n[A[1]]).sum(1) < -0.5).sum())
L = {lab: (json.load(open(p + ".json", encoding="utf-8"))["objects"], np.load(p + ".npz")) for lab, p in SETS}
print("パーツ  " + " | ".join("%s: 折れ辺 辺比(0.1%%/中央/99.9%%)" % lab for lab, _ in SETS))
for r in PLAN["keep_arm"]:
    k = r["n"].split("(")[0]; s = fj["full"][k]; T = tris(s); A = adj(T); E = F["e_%d" % s]; ref = F["w_%d" % s].astype(float)
    lr = np.linalg.norm(ref[E[:, 0]] - ref[E[:, 1]], axis=1); ok = lr > 1e-9; cells = []
    for lab, (J, Z) in L.items():
        W = Z[J[r["n"]]["key"]].astype(float); lw = np.linalg.norm(W[E[:, 0]] - W[E[:, 1]], axis=1); q = lw[ok] / lr[ok]
        cells.append("%5d  %.2f/%.3f/%.2f" % (folds(W, T, A), np.percentile(q, 0.1), np.median(q), np.percentile(q, 99.9)))
    print("%-10s " % k + " | ".join(cells))
