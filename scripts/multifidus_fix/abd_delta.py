# abd_rebuild.py の結果に、向きごとの補正を足す（システムの Python）
#  高さごとのアフィンだけでは、肋骨（背中側は今のまま・前と横だけ広げた）と外腹斜筋の両方には合わせきれない。
#  高さ z（10mm）× 向き θ（10°）の升ごとに、男性の形をアフィンで置いた位置と、女性の実際の位置の「中心からの距離」の差を、
#  同じ番号の頂点どうし（男女で頂点の並びが同じ）で測って中央値をとる（2026-10-15: 内面の 5% 点どうしで比べたら、升に入る肋骨が男女で違って ±50mm の外れ値が出た）
#   δ_EO = 外腹斜筋、δ_rib = 肋骨・肋軟骨（肋骨のある升だけ）。絶対値は 25mm まで
#  をならして（σ 15mm・15°）、腹横筋は肋骨のある高さで δ_rib、無い所で δ_EO、内腹斜筋・腹直筋・錐体筋は δ_EO を、水平・中心から外向きに足す。
#  補正は升の位置（高さ・向き）だけで決まるので、同じ所の表と裏に同じ量がかかり、厚みは変わらない
# python abd_delta.py <work/g4> <かごの npz> <abd_rebuild の npz（_affines.npy を一緒に読む）> <出力 npz>
import sys, json, numpy as np
W, CAGE, ABD, OUT = sys.argv[1:5]
fj = json.load(open(W + "/female.json", encoding="utf-8")); F = np.load(W + "/female.npz")
mj = json.load(open(W + "/male.json", encoding="utf-8")); M = np.load(W + "/male.npz"); C = np.load(CAGE); A0 = np.load(ABD)
As = np.load(ABD.replace(".npz", "_affines.npy"))
X_all = {k: M["w_%d" % mj["full"][k]].astype(float) for k in A0.files}
zall = np.concatenate([X[:, 2] for X in X_all.values()]); zc = np.arange(zall.min() - 0.01, zall.max() + 0.015, 0.005)
def aff(X):
    i0 = np.clip(np.searchsorted(zc, X[:, 2]) - 1, 0, len(zc) - 2); t = ((X[:, 2] - zc[i0]) / (zc[i0 + 1] - zc[i0]))[:, None, None]
    A = As[i0] * (1 - t) + As[i0 + 1] * t; return np.einsum("ni,nij->nj", np.c_[X, np.ones(len(X))], A)
cur = lambda k: (C[k].astype(float) if k in C.files else F["w_%d" % fj["full"][k]].astype(float))
male = lambda k: M["w_%d" % mj["full"][k]].astype(float)
KAN = {5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}
RIBS = [s + "第%s肋骨" % KAN[n] for s in "右左" for n in range(5, 13)] + [s + "第%s肋軟骨" % KAN[n] for s in "右左" for n in (5, 6, 7)] + ["右肋軟骨", "左肋軟骨"]
EO = ["右外腹斜筋", "左外腹斜筋"]
Fe = np.concatenate([cur(k) for k in EO]); Me = np.concatenate([aff(male(k)) for k in EO])
Fr = np.concatenate([cur(k) for k in RIBS]); Mr = np.concatenate([aff(male(k)) for k in RIBS])
z0, z1 = min(Fe[:, 2].min(), Fr[:, 2].min()) - 0.02, max(Fe[:, 2].max(), Fr[:, 2].max()) + 0.02
zb = np.arange(z0, z1, 0.010); TH = np.arange(-180, 180, 10); nz, nt = len(zb), len(TH)
# 中心: 女性の外腹斜筋の前後の真ん中（高さごと、ならす）
cyz = np.array([np.median(Fe[np.abs(Fe[:, 2] - z) < 0.01, 1]) if (np.abs(Fe[:, 2] - z) < 0.01).sum() > 50 else np.nan for z in zb])
ok = np.isfinite(cyz); cyz = np.interp(zb, zb[ok], cyz[ok]); cyz = np.convolve(np.pad(cyz, 3, mode="edge"), np.ones(7) / 7, mode="valid")
def polar(P):
    cy = np.interp(P[:, 2], zb, cyz); dx, dy = P[:, 0], P[:, 1] - cy
    return np.degrees(np.arctan2(dy, -dx)), np.hypot(dx, dy), np.c_[dx, dy] / np.maximum(np.hypot(dx, dy), 1e-9)[:, None]
def corr(Q, P):
    th, rq, _ = polar(Q); _, rp, _ = polar(P); dd = rq - rp
    i = np.clip(((Q[:, 2] - z0) / 0.010).astype(int), 0, nz - 1); j = np.round((th + 180) / 10).astype(int) % nt
    G = np.full((nz, nt), np.nan); key = i * nt + j; o = np.argsort(key); ks, st = np.unique(key[o], return_index=True); en = np.r_[st[1:], len(o)]
    for kk, s, e in zip(ks, st, en):
        if e - s >= 5: G[kk // nt, kk % nt] = np.clip(np.median(dd[o[s:e]]), -0.025, 0.025)
    return G
dEO = corr(Fe, Me); dRIB = corr(Fr, Mr)
def smooth(G, sz=1.5, st=1.5):
    Wt = np.isfinite(G).astype(float); V = np.nan_to_num(G)
    def g1(s): x = np.arange(-3 * int(np.ceil(s)), 3 * int(np.ceil(s)) + 1); k = np.exp(-(x / s) ** 2 / 2); return k / k.sum()
    kz, kt = g1(sz), g1(st)
    def conv(A):
        A = np.apply_along_axis(lambda v: np.convolve(v, kz, mode="same"), 0, A); p = len(kt) // 2
        A = np.concatenate([A[:, -p:], A, A[:, :p]], 1); A = np.apply_along_axis(lambda v: np.convolve(v, kt, mode="same"), 1, A); return A[:, p:-p]
    num, den = conv(V * Wt), conv(Wt); return np.where(den > 0.05, num / np.maximum(den, 1e-9), np.nan), den
sEO, denE = smooth(dEO); sRIB, denR = smooth(dRIB)
sEO = np.where(np.isfinite(sEO), sEO, 0.0)
wR = np.clip(denR / 0.5, 0, 1)                                          # 肋骨がある升ほど 1
sRIB = np.where(np.isfinite(sRIB), sRIB, 0.0)
def field(G, P):
    th, _, u = polar(P); zz = np.clip(P[:, 2], zb[0], zb[-1]); i0 = np.clip(((zz - zb[0]) / 0.010).astype(int), 0, nz - 2); tz = (zz - zb[i0]) / 0.010
    tt = (th + 180) / 10.0; j0 = np.floor(tt).astype(int) % nt; tj = tt - np.floor(tt); j1 = (j0 + 1) % nt
    v = (G[i0, j0] * (1 - tz) + G[i0 + 1, j0] * tz) * (1 - tj) + (G[i0, j1] * (1 - tz) + G[i0 + 1, j1] * tz) * tj
    return v, u
def cs_mid(ax):                                                        # |x| < 25mm で 0、60mm で 1
    t = np.clip((ax - 0.025) / 0.035, 0, 1); return (1 - np.cos(np.pi * t)) / 2
out = {}
for k in A0.files:
    P = A0[k].astype(float)
    vE, u = field(sEO, P)
    if "腹横筋" in k:
        vR, _ = field(sRIB, P); w, _ = field(wR, P); v = w * vR + (1 - w) * vE
    else: v = vE
    v = v * cs_mid(np.abs(P[:, 0]))                                     # 正中（白線のそば）は高さごとのアフィンのまま（白線に 2.2mm で合っている）
    out[k] = P.copy(); out[k][:, :2] += u * v[:, None]
    print("  %s 補正 mm: 中央値 %+.1f  5%%点 %+.1f  95%%点 %+.1f" % (k, np.median(v) * 1000, np.percentile(v, 5) * 1000, np.percentile(v, 95) * 1000))
np.savez_compressed(OUT, **{k: v.astype(np.float32) for k, v in out.items()})
cols = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150]
print("δ_EO / δ_rib mm（ならした後）  行=高さ 列=向き")
for i in range(0, nz, 3):
    print("%.3f " % zb[i] + " ".join("%+5.1f/%s" % (sEO[i, list(TH).index(c)] * 1000, ("%+5.1f" % (sRIB[i, list(TH).index(c)] * 1000)) if wR[i, list(TH).index(c)] > 0.3 else "  -  ") for c in cols))
