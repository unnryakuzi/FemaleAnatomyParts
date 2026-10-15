# 腹横筋を、胸の内壁（肋骨・肋軟骨・胸骨・内肋間筋・最内肋間筋）の内側へ寄せる（システムの Python）
#  高さ z（5mm）× 向き θ（5°）の升ごとに、内壁の内面（半径の 3% 点）と腹横筋の外面（97% 点）を比べ、
#  腹横筋が「内壁 − 1mm」より外に出ている分だけ、中心へ向けて水平に戻す。必要量は近傍の最大で包んでからならす（どこでも必要量以上・なめらか）。
#  量は升の位置だけで決まるので、腹横筋の表と裏に同じ量がかかり、厚みは変わらない
#  （2026-10-15: 男性の形から作り直した腹横筋が、背中側と横で下の肋骨の外を通っていた。背中側の肋骨は今の位置に残したため）
# python ta_inside.py <候補 npz（肋骨・肋間筋・腹横筋を含む）> <出力 npz（腹横筋だけ）> [余白 mm=1]
import sys, numpy as np
from scipy.ndimage import maximum_filter, gaussian_filter
C = np.load(sys.argv[1]); OUT = sys.argv[2]; MG = (float(sys.argv[3]) if len(sys.argv) > 3 else 1.0) / 1000
is_wall = lambda k: ((("肋骨" in k or "肋軟骨" in k) and "挙筋" not in k) or k in ("胸骨柄", "胸骨体", "剣状突起") or k.startswith("内肋間筋") or k.startswith("最内肋間筋"))
Wl = np.concatenate([C[k].astype(float) for k in C.files if is_wall(k)])
TA = {k: C[k].astype(float) for k in C.files if "腹横筋" in k}
DZ, DT = 0.005, 5.0
z0 = min(Wl[:, 2].min(), min(v[:, 2].min() for v in TA.values())) - 0.01; z1 = Wl[:, 2].max() + 0.01
zb = np.arange(z0, z1, DZ); nz = len(zb); TH = np.arange(-180, 180, DT); nt = len(TH)
cy = np.array([((Wl[m, 1].min() + Wl[m, 1].max()) / 2) if (m := np.abs(Wl[:, 2] - z) < 0.01).sum() > 100 else np.nan for z in zb])
ok = np.isfinite(cy); cy = np.interp(zb, zb[ok], cy[ok]); cy = gaussian_filter(cy, 3, mode="nearest")
def polar(P):
    c = np.interp(P[:, 2], zb, cy); dx, dy = P[:, 0], P[:, 1] - c; r = np.hypot(dx, dy)
    return np.degrees(np.arctan2(dy, -dx)), r, np.c_[dx, dy] / np.maximum(r, 1e-9)[:, None]
def binq(P, q):
    th, r, _ = polar(P); i = np.clip(((P[:, 2] - z0) / DZ).astype(int), 0, nz - 1); j = np.round((th + 180) / DT).astype(int) % nt
    G = np.full((nz, nt), np.nan); key = i * nt + j; o = np.argsort(key); ks, st = np.unique(key[o], return_index=True); en = np.r_[st[1:], len(o)]
    for kk, s, e in zip(ks, st, en):
        if e - s >= 3: G[kk // nt, kk % nt] = np.percentile(r[o[s:e]], q)
    return G
rw = binq(Wl, 3); rt = binq(np.concatenate(list(TA.values())), 97)
need = np.where(np.isfinite(rw) & np.isfinite(rt), np.maximum(rt - (rw - MG), 0.0), 0.0)     # 内へ戻す量（正）
print("内壁より外に出ている升 %d / %d   最大 %.1f mm   中央値（出ている升）%.1f mm" % ((need > 0).sum(), need.size, need.max() * 1000, np.median(need[need > 0]) * 1000 if (need > 0).any() else 0))
env = maximum_filter(need, size=(5, 5), mode=("nearest", "wrap"))                      # 近傍の最大で包む（±10mm・±10°）
sm = gaussian_filter(env, sigma=(2.0, 2.0), mode=("nearest", "wrap"))
sm = np.maximum(sm, need)                                                                # どこでも必要量以上
out = {}
for k, P in TA.items():
    th, r, u = polar(P); zz = np.clip(P[:, 2], zb[0], zb[-1]); i0 = np.clip(((zz - zb[0]) / DZ).astype(int), 0, nz - 2); tz = (zz - zb[i0]) / DZ
    tt = (th + 180) / DT; j0 = np.floor(tt).astype(int) % nt; tj = tt - np.floor(tt); j1 = (j0 + 1) % nt
    v = (sm[i0, j0] * (1 - tz) + sm[i0 + 1, j0] * tz) * (1 - tj) + (sm[i0, j1] * (1 - tz) + sm[i0 + 1, j1] * tz) * tj
    Q = P.copy(); Q[:, :2] -= u * v[:, None]; out[k] = Q.astype(np.float32)
    print("  %s 内へ戻した量 mm: 動いた頂点 %d / %d  中央値 %.1f  最大 %.1f" % (k, (v > 1e-4).sum(), len(v), np.median(v[v > 1e-4]) * 1000 if (v > 1e-4).any() else 0, v.max() * 1000))
np.savez_compressed(OUT, **out)
