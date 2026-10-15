# 肋骨のかごを G4（外側の筋と同じ変換）で置き直す量に、場所ごとの係数 α(z, θ)（0〜1）を掛けて、外のパーツに当たらない範囲で動かす（システムの Python）
#  目標の動き d = G4(男性の形) − 今の形（横と前後だけ。高さは今のまま）。背骨から 15mm 以内 0、50mm で 1（肋骨の付け根を離さない）
#  α: なるべく 1、ただし各升で「動いた後のすき間 = 今のすき間 − α×外向きの動き」が 0.3mm 以上。なめらかさを入れた有界の最小二乗で解く
#  （2026-10-15: α なしの G4 だと前と横は男性並みになったが、背中側（脊柱起立筋・腰方形筋・広背筋）と下の肋骨の横（外腹斜筋）で食い込んだ。
#    背中側の筋は G4 ではなく、今の肋骨の背中側と合っている）
#  肋間筋・剣状突起・胸横筋・肋骨挙筋・肋骨に付く筋（小胸筋・鎖骨下筋・上後鋸筋・下後鋸筋・胸腸肋筋）は、骨の動きを格子にならして補間（骨から離れると 0 へ）、
#  大胸筋の腹部は G4(男性の形) へ α を掛けて寄せる（上腕骨から 30mm 以内は今のまま、90mm で全量）
# python cage_alpha.py <work/g4> <affine_report.json> <今の女性の cage_profile json> <出力 npz> [λ1=2] [λ2=6]
import sys, json, numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import lsq_linear
from scipy.sparse import lil_matrix, vstack, identity, csr_matrix
W, AREP, PROF, OUT = sys.argv[1:5]
L1 = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0; L2 = float(sys.argv[6]) if len(sys.argv) > 6 else 6.0
fj = json.load(open(W + "/female.json", encoding="utf-8")); F = np.load(W + "/female.npz")
mj = json.load(open(W + "/male.json", encoding="utf-8")); M = np.load(W + "/male.npz")
G4 = np.vstack([np.array(json.load(open(AREP, encoding="utf-8"))["groups"][4]), [0, 0, 0, 1]])
J = json.load(open(PROF, encoding="utf-8"))
ap = lambda A, P: P @ A[:3, :3].T + A[:3, 3]
def cs(d, d0, d1):
    t = np.clip((d - d0) / (d1 - d0), 0, 1); return (1 + np.cos(np.pi * t)) / 2
cur = lambda k: F["w_%d" % fj["full"][k]].astype(float)
def same(k):
    a, b = fj["meta"][k], mj["meta"].get(k)
    return b is not None and k in mj["full"] and a["n"] == b["n"] and a["sig"] == b["sig"]
is_bone = lambda k: (("肋骨" in k or "肋軟骨" in k) and "挙筋" not in k) or k in ("胸骨柄", "胸骨体", "剣状突起")
names = [k for k in fj["full"] if not any(s in k for s in ("中手", "中足", "指", "趾", "骨間筋", "腓骨筋"))]
BONE = [k for k in names if is_bone(k)]
CAGE = [k for k in names if any(s in k for s in ("肋間筋", "胸横筋", "肋骨挙筋"))]
PART = [k for k in names if any(s in k for s in ("小胸筋", "鎖骨下筋", "上後鋸筋", "下後鋸筋", "胸腸肋筋"))]
PMA = [k for k in ("右大胸筋腹部", "左大胸筋腹部") if k in names and same(k)]
spine = np.concatenate([F["p_%d" % m["slot"]] for k, m in fj["meta"].items() if "胸椎" in k and "円板" not in k]).astype(float); tsp = cKDTree(spine)
# 1) 目標の動き
D0 = {}
for k in BONE + PMA:
    if not same(k): continue
    P = cur(k); T = ap(G4, M["w_%d" % mj["full"][k]].astype(float)); T[:, 2] = P[:, 2]
    ds, _ = tsp.query(P); D0[k] = (T - P) * (cs(-ds, -0.050, -0.015)[:, None] if k in BONE else 1.0)
# 2) 升（高さ × 向き）
zg = np.array([r["z"] for r in J["rows"]]); cyg = np.array([r["cy"] for r in J["rows"]]); TH = np.arange(-180, 180, 10); nz, nt = len(zg), len(TH)
def polar(P):
    cy = np.interp(P[:, 2], zg, cyg); dx, dy = P[:, 0], P[:, 1] - cy
    return np.degrees(np.arctan2(dy, -dx)), np.hypot(dx, dy), np.c_[dx, dy] / np.maximum(np.hypot(dx, dy), 1e-9)[:, None]
gap = np.full((nz, nt), np.nan); rrib = np.full((nz, nt), np.nan)
for i, r in enumerate(J["rows"]):
    for j, th in enumerate(TH):
        p = r["prof"].get(str(int(th)))
        if p: rrib[i, j] = p[0]; gap[i, j] = (p[1] - p[0]) if p[1] is not None else np.nan
dr = np.full((nz, nt), np.nan); cnt = np.zeros((nz, nt), int)
allP = np.concatenate([cur(k) for k in D0 if k in BONE]); allD = np.concatenate([D0[k] for k in D0 if k in BONE])
th_, r_, u_ = polar(allP); rad = (allD[:, :2] * u_).sum(1)
ii = np.clip(np.round((allP[:, 2] - zg[0]) / np.diff(zg).mean()).astype(int), 0, nz - 1); jj = np.round((th_ + 180) / 10).astype(int) % nt
for i in range(nz):
    for j in range(nt):
        m = (ii == i) & (jj == j)
        if m.sum() < 10 or not np.isfinite(rrib[i, j]): continue
        o = m & (r_ > rrib[i, j] - 0.003); cnt[i, j] = int(o.sum())
        if o.sum() >= 3: dr[i, j] = float(np.percentile(rad[o], 90))
U = np.full((nz, nt), np.inf)
lim = np.isfinite(gap) & np.isfinite(dr) & (dr > 0.0003)
U[lim] = np.maximum((gap[lim] - 0.0003) / dr[lim], 1e-6)
# 3) α を解く
N = nz * nt; idx = lambda i, j: i * nt + (j % nt)
def diff(order, axis, w):
    D = lil_matrix((N * 2, N)); r = 0
    for i in range(nz):
        for j in range(nt):
            if axis == 0:
                if order == 1 and i + 1 < nz: D[r, idx(i, j)] = -w; D[r, idx(i + 1, j)] = w; r += 1
                if order == 2 and 0 < i < nz - 1: D[r, idx(i - 1, j)] = w; D[r, idx(i, j)] = -2 * w; D[r, idx(i + 1, j)] = w; r += 1
            else:
                if order == 1: D[r, idx(i, j)] = -w; D[r, idx(i, j + 1)] = w; r += 1
                if order == 2: D[r, idx(i, j - 1)] = w; D[r, idx(i, j)] = -2 * w; D[r, idx(i, j + 1)] = w; r += 1
    return csr_matrix(D[:r])
has = (cnt > 0).ravel(); Dd = identity(N, format="csr")[np.where(has)[0]]
A = vstack([Dd, diff(1, 0, L1), diff(1, 1, L1), diff(2, 0, L2), diff(2, 1, L2)]).tocsr()
b = np.concatenate([np.ones(int(has.sum())), np.zeros(A.shape[0] - int(has.sum()))])
ub = np.minimum(U.ravel(), 1.0 + 1e-9); res = lsq_linear(A, b, bounds=(np.zeros(N), np.maximum(ub, 1e-6)), lsmr_tol="auto", max_iter=5000)
al = res.x.reshape(nz, nt)
def alpha_at(P):
    th, _, _ = polar(P); zc = np.clip(P[:, 2], zg[0], zg[-1]); i0 = np.clip(np.searchsorted(zg, zc) - 1, 0, nz - 2); tz = (zc - zg[i0]) / (zg[i0 + 1] - zg[i0])
    tt = (th + 180) / 10.0; j0 = np.floor(tt).astype(int) % nt; tj = tt - np.floor(tt); j1 = (j0 + 1) % nt
    return (al[i0, j0] * (1 - tz) + al[i0 + 1, j0] * tz) * (1 - tj) + (al[i0, j1] * (1 - tz) + al[i0 + 1, j1] * tz) * tj
# 4) 動かす
out, Dfin = {}, {}
hum = cKDTree(np.concatenate([F["p_%d" % m["slot"]] for k, m in fj["meta"].items() if "上腕骨" in k]).astype(float))
for k, d in D0.items():
    P = cur(k); a_ = alpha_at(P)
    if k in PMA:                                                       # 大胸筋の腹部: 上腕骨に付く側は今の位置のまま（腕は G3 で置かれていて G4 と合わない）
        dh, _ = hum.query(P); a_ = a_ * (1 - cs(dh, 0.030, 0.090))
    Dfin[k] = d * a_[:, None]; out[k] = P + Dfin[k]
# 骨以外は、骨の動きを 3 次元の格子（4mm）にならして（σ 12mm の正規化畳み込み）から補間する。骨から離れるほど 0 へ（重みの格子で薄める）
#  （2026-10-15: 近い骨の頂点 24 個からの補間だと、肋間筋の表と裏が上下の別の肋骨を拾い、折れが 5→1576 本に増えた）
from scipy.ndimage import gaussian_filter, map_coordinates
bp = np.concatenate([cur(k) for k in Dfin if k in BONE]); bv = np.concatenate([Dfin[k] for k in Dfin if k in BONE])
VX = 0.004; lo = bp.min(0) - 0.08; shp = np.ceil((bp.max(0) + 0.08 - lo) / VX).astype(int) + 1
gi = np.round((bp - lo) / VX).astype(int); Wg = np.zeros(shp); np.add.at(Wg, tuple(gi.T), 1.0)
Dg = [np.zeros(shp) for _ in range(3)]
for c in range(3): np.add.at(Dg[c], tuple(gi.T), bv[:, c])
SG = 0.012 / VX; Ws = gaussian_filter(Wg, SG); Ds = [gaussian_filter(D, SG) for D in Dg]
Wref = np.percentile(Ws[tuple(gi.T)], 50)                                   # 骨の上での重みの中央値
def field(P):
    q = ((P - lo) / VX).T; w = map_coordinates(Ws, q, order=1, mode="nearest")
    d = np.stack([map_coordinates(D, q, order=1, mode="nearest") for D in Ds], 1) / np.maximum(w, 1e-12)[:, None]
    fade = np.clip(w / (0.25 * Wref), 0, 1); fade = (1 - np.cos(np.pi * fade)) / 2   # 骨から離れると 0 へなめらかに
    return d * fade[:, None]
for k in BONE + CAGE + PART:
    if k in out: continue
    P = cur(k); out[k] = P + field(P)
np.savez_compressed(OUT, **{k: v.astype(np.float32) for k, v in out.items()})
np.savez(OUT.replace(".npz", "_alpha.npz"), z=zg, th=TH, alpha=al, U=U, gap=gap, dr=dr)
print("解: %s   α の平均（肋骨のある升）%.2f   上限に当たった升 %d" % (res.status, al.ravel()[has].mean(), int((np.abs(al - np.minimum(U, 1)) < 1e-3).sum())))
cols = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150]
print("α  行=高さ 列=向き（0=右横 -90=前 +90=背中 ±180=左横）  [外向きの動き mm]")
print("   z   " + " ".join("%10d" % c for c in cols))
for i in range(0, nz, 2):
    print("%.3f " % zg[i] + " ".join("%4.2f[%4s]" % (al[i, list(TH).index(c)], ("%4.0f" % (dr[i, list(TH).index(c)] * 1000)) if np.isfinite(dr[i, list(TH).index(c)]) else "   -") for c in cols))
for k in sorted(out, key=lambda k: -np.percentile(np.linalg.norm(out[k] - cur(k), axis=1), 95))[:12]:
    mv = np.linalg.norm(out[k] - cur(k), axis=1) * 1000; print("   %s 動いた量 中央値 %.1f / 95%%点 %.1f / 最大 %.1f mm" % (k, np.median(mv), np.percentile(mv, 95), mv.max()))
