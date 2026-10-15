# 肋骨のかごを広げ、内腹斜筋・腹横筋の下の部分を骨盤に付け直す（システムの Python）。結果は npz（ワールド座標）
#  1) 肋骨のかご（肋骨・肋軟骨・胸骨・肋間筋・胸横筋・肋骨挙筋）: 各頂点を中心軸 (0, cy(z)) から水平に Δr(z,θ) だけ外へ（cage_field.npz）
#     背骨（胸椎）から 15mm 以内は動かさず、50mm までコサインで効かせる（肋骨の付け根を背骨から離さない）
#  2) 肋骨に付く筋（小胸筋・鎖骨下筋・上後鋸筋・下後鋸筋・胸腸肋筋・内腹斜筋・腹横筋）: 上と同じ動きに、元の肋骨からの距離で重み（8mm まで1、35mm で0）
#  3) 内腹斜筋・腹横筋の下の部分: 男性の形を骨盤（寛骨）と同じ変換 G1 で置き直した位置へ、男性空間で寛骨から 15mm まで1、50mm で0 の重みで寄せる
# python cage_apply.py <work/cage（女性の今の全頂点）> <work/wc（男性）> <cage_field.npz> <affine_report.json> <出力 npz>
import sys, json, numpy as np
from scipy.spatial import cKDTree
WF, WM, FIELD, AREP, OUT = sys.argv[1:6]
fj = json.load(open(WF + "/female.json", encoding="utf-8")); F = np.load(WF + "/female.npz")
mj = json.load(open(WM + "/male.json", encoding="utf-8")); M = np.load(WM + "/male.npz")
FD = np.load(FIELD); zg, thg, dr, cy = FD["z"], FD["th"], FD["dr"], FD["cy"]
G1 = np.vstack([np.array(json.load(open(AREP, encoding="utf-8"))["groups"][1]), [0, 0, 0, 1]])
def cs(d, d0, d1):   # d<=d0 で 1、d>=d1 で 0（コサイン）
    t = np.clip((d - d0) / (d1 - d0), 0, 1); return (1 + np.cos(np.pi * t)) / 2
def field(P):
    z = P[:, 2]; zc = np.clip(z, zg.min(), zg.max())
    fz = cs(np.abs(z - zc), 0.0, 0.030)                       # かごの高さの外は 30mm でゼロへ
    i = np.clip(np.searchsorted(zg, zc) - 1, 0, len(zg) - 2); tz = (zc - zg[i]) / (zg[i + 1] - zg[i])
    c = cy[i] * (1 - tz) + cy[i + 1] * tz
    d = P[:, :2] - np.c_[np.zeros(len(P)), c]; r = np.hypot(d[:, 0], d[:, 1]); u = d / np.maximum(r, 1e-9)[:, None]
    th = np.degrees(np.arctan2(d[:, 1], -d[:, 0])); tt = (th + 180) / 10.0; j = np.floor(tt).astype(int) % 36; tj = tt - np.floor(tt); j1 = (j + 1) % 36
    v = (dr[i, j] * (1 - tz) + dr[i + 1, j] * tz) * (1 - tj) + (dr[i, j1] * (1 - tz) + dr[i + 1, j1] * tz) * tj
    out = np.zeros_like(P); out[:, :2] = u * (v * fz)[:, None]; return out
def full(k): return F["w_%d" % fj["full"][k]].astype(float)
names = list(fj["full"])
is_bone = lambda k: (("肋骨" in k or "肋軟骨" in k) and "挙筋" not in k) or k in ("胸骨柄", "胸骨体", "剣状突起")
CAGE = [k for k in names if is_bone(k) or any(s in k for s in ("肋間筋", "胸横筋", "肋骨挙筋"))]
PART = [k for k in names if any(s in k for s in ("小胸筋", "鎖骨下筋", "上後鋸筋", "下後鋸筋", "胸腸肋筋", "内腹斜筋", "腹横筋"))]
spine = np.concatenate([F["p_%d" % m["slot"]] for k, m in fj["meta"].items() if "胸椎" in k and "円板" not in k]).astype(float)
tsp = cKDTree(spine)
ribs_old = np.concatenate([full(k)[::3] for k in names if is_bone(k)]); trib = cKDTree(ribs_old)
hip_m = np.concatenate([M["p_%d" % m["slot"]] for k, m in mj["meta"].items() if "寛骨" in k]).astype(float); thip = cKDTree(hip_m)
out, rep = {}, {}
for k in CAGE + PART:
    P = full(k); ds, _ = tsp.query(P); s = cs(-ds, -0.050, -0.015)   # 背骨から 15mm 以内 0、50mm 以上 1
    w = s
    if k in PART:
        dr_, _ = trib.query(P); w = s * cs(dr_, 0.008, 0.035)
    disp = field(P) * w[:, None]; Pn = P + disp
    if k[1:] in ("内腹斜筋", "腹横筋") and k in mj["full"]:
        X = M["w_%d" % mj["full"][k]].astype(float); T = X @ G1[:3, :3].T + G1[:3, 3]
        dh, _ = thip.query(X); wp = cs(dh, 0.015, 0.050)
        Pn = Pn + wp[:, None] * (T - Pn)
        rep[k + "_骨盤に寄せた頂点"] = int((wp > 0.01).sum())
    out[k] = Pn.astype(np.float32); mv = np.linalg.norm(Pn - P, axis=1) * 1000
    rep[k] = (int((mv > 0.1).sum()), len(P), round(float(np.median(mv[mv > 0.1])) if (mv > 0.1).any() else 0, 1), round(float(mv.max()), 1))
np.savez_compressed(OUT, **out)
for k, v in rep.items(): print(k, v)
