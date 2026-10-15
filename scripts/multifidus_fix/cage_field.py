# 肋骨のかごを広げる量 Δr(z, θ) を作る（システムの Python）
#  目標 = 女性のすき間（肋骨の外面〜外のパーツの内面）− 男性の同じ所のすき間（肋骨の番号の高さで対応づけ、0.3mm 以上）。0 未満は 0（縮めない）
#  上限 = 女性のすき間 − 0.3mm（外のパーツに当てない）。外のパーツ = cage_profile.py の「かごと一緒に動かさない全パーツ」
#  なめらかさ（高さ・向きの 1 階と 2 階の差）を入れた有界の最小二乗で解く（scipy の lsq_linear）
#  （2026-10-15: ガウスでならすだけだと、空きの少ない所（第七肋軟骨と大胸筋、剣状突起と白線、肩甲下筋）へ隣の大きな値がにじみ出て干渉が増えた。
#    ならした後に上限で切ると、こんどは升ごとに 0 と 10mm が交互に出てギザギザになった）
# python cage_field.py <cage_female.json> <cage_male.json> <出力 npz> [λ1=1] [λ2=4]
import sys, json, numpy as np
from scipy.optimize import lsq_linear
from scipy.sparse import lil_matrix, vstack, identity, csr_matrix
Fj = json.load(open(sys.argv[1], encoding="utf-8")); Mj = json.load(open(sys.argv[2], encoding="utf-8")); OUT = sys.argv[3]
L1 = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0; L2 = float(sys.argv[5]) if len(sys.argv) > 5 else 4.0
lf = np.array([Fj["levels"][str(n)] for n in range(1, 12)]); lm = np.array([Mj["levels"][str(n)] for n in range(1, 12)])
o = np.argsort(lf); f2m = lambda z: float(np.interp(z, lf[o], lm[o]))   # 女性の高さ → 男性の同じ肋骨の高さ
TH = np.arange(-180, 180, 10)
def grid(J):
    zs = np.array([r["z"] for r in J["rows"]]); G = np.full((len(zs), len(TH)), np.nan)
    for i, r in enumerate(J["rows"]):
        for j, th in enumerate(TH):
            p = r["prof"].get(str(th))
            if p and p[1] is not None: G[i, j] = (p[1] - p[0]) * 1000      # mm
    return zs, G, np.array([r["cy"] for r in J["rows"]])
zf, Gf, cyf = grid(Fj); zm, Gm, _ = grid(Mj)
T = np.full_like(Gf, np.nan)
for i, z in enumerate(zf):
    k = np.argmin(np.abs(zm - f2m(z)))
    T[i] = np.where(np.isfinite(Gf[i]) & np.isfinite(Gm[k]), np.maximum(Gf[i] - np.maximum(Gm[k], 0.3), 0.0), np.nan)
U = np.where(np.isfinite(Gf), np.maximum(Gf - 0.3, 1e-6), np.inf)               # 上限（0 だと下限と同じになり解けないので 1e-6mm）
nz, nt = Gf.shape; N = nz * nt; idx = lambda i, j: i * nt + (j % nt)
rows = []
def diff(order, axis, w):
    D = lil_matrix((N, N)); r = 0
    for i in range(nz):
        for j in range(nt):
            if axis == 0:
                if order == 1 and i + 1 < nz: D[r, idx(i, j)] = -w; D[r, idx(i + 1, j)] = w; r += 1
                if order == 2 and 0 < i < nz - 1: D[r, idx(i - 1, j)] = w; D[r, idx(i, j)] = -2 * w; D[r, idx(i + 1, j)] = w; r += 1
            else:
                if order == 1: D[r, idx(i, j)] = -w; D[r, idx(i, j + 1)] = w; r += 1
                if order == 2: D[r, idx(i, j - 1)] = w; D[r, idx(i, j)] = -2 * w; D[r, idx(i, j + 1)] = w; r += 1
    return csr_matrix(D[:r])
has = np.isfinite(T).ravel(); Dd = identity(N, format="csr")[np.where(has)[0]]
Amat = vstack([Dd, diff(1, 0, L1), diff(1, 1, L1), diff(2, 0, L2), diff(2, 1, L2)]).tocsr()
b = np.concatenate([np.nan_to_num(T).ravel()[has], np.zeros(Amat.shape[0] - int(has.sum()))])
res = lsq_linear(Amat, b, bounds=(np.zeros(N), U.ravel()), lsmr_tol="auto", max_iter=5000)
Ds = res.x.reshape(nz, nt) / 1000                                              # m
dev = (Ds * 1000 - T)[np.isfinite(T)]
print("解: %s  目標との差 mm 中央値 %.2f  90%%点 %.1f  上限に当たった升 %d" % (res.status, np.median(np.abs(dev)), np.percentile(np.abs(dev), 90), int((np.abs(Ds * 1000 - U) < 0.05).sum())))
np.savez(OUT, z=zf, th=TH, dr=Ds, raw=T / 1000, cy=cyf, allow=np.where(np.isfinite(U), U, np.nan) / 1000)
print("z %.3f〜%.3f  %d 段 × %d 方向" % (zf.min(), zf.max(), len(zf), len(TH)))
print("広げる量 mm  行=高さ  列=向き（0=右横 -90=前 +90=背中 ±180=左横）  [目標]")
cols = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150]
print("   z    " + " ".join("%11d" % c for c in cols))
for i in range(0, len(zf), 2):
    print("%.3f  " % zf[i] + " ".join("%5.1f[%4s]" % (Ds[i, list(TH).index(c)] * 1000, ("%4.0f" % T[i, list(TH).index(c)]) if np.isfinite(T[i, list(TH).index(c)]) else "   -") for c in cols))
