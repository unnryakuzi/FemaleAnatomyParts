# 肋骨のかごを、外側の筋（胴の表層）と同じ変換 G4 で男性の形から置き直す（システムの Python）。結果は npz（ワールド座標）
#  女性化のとき、肋骨・肋軟骨・胸骨は横幅を 0.81〜0.94 倍に縮められ、外側の筋（G4: 0.98 倍）と合っていなかった（すき間 7〜28mm）。
#  1) 男性と頂点の並びが同じ骨（肋骨・肋軟骨・胸骨）: 目標 = G4(男性の形)。モード xy は高さ z を今のまま残し、横と前後だけ G4 に合わせる
#     背骨（胸椎）から 15mm 以内は今のまま、50mm までコサインで目標へ（肋骨の付け根を背骨から離さない）
#  2) 並びが違う・男性に無いかごのパーツ（肋間筋・剣状突起・胸横筋・肋骨挙筋）: 1) の骨の動きを近くの骨の頂点からなめらかに補間して同じだけ動かす
#  3) 肋骨に付く筋（小胸筋・鎖骨下筋・上後鋸筋・下後鋸筋・胸腸肋筋）: 2) と同じ動きに、元の骨からの距離で重み（8mm まで1、35mm で0）
#  4) 大胸筋の腹部: 肋骨と同じ縮め方をされていた（x0.842）ので、他の大胸筋と同じ G4(男性の形) にする
# python cage_g4.py <work/g4> <affine_report.json> <出力 npz> <xy|xyz>
import sys, json, numpy as np
from scipy.spatial import cKDTree
W, AREP, OUT, MODE = sys.argv[1:5]
fj = json.load(open(W + "/female.json", encoding="utf-8")); F = np.load(W + "/female.npz")
mj = json.load(open(W + "/male.json", encoding="utf-8")); M = np.load(W + "/male.npz")
G4 = np.vstack([np.array(json.load(open(AREP, encoding="utf-8"))["groups"][4]), [0, 0, 0, 1]])
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
spine = np.concatenate([F["p_%d" % m["slot"]] for k, m in fj["meta"].items() if "胸椎" in k and "円板" not in k]).astype(float); tsp = cKDTree(spine)
out, disp_pts, disp_vec, rep = {}, [], [], {}
for k in BONE:
    P = cur(k)
    if same(k):
        T = ap(G4, M["w_%d" % mj["full"][k]].astype(float))
        if MODE == "xy": T[:, 2] = P[:, 2]
        ds, _ = tsp.query(P); d = (T - P) * cs(-ds, -0.050, -0.015)[:, None]
        out[k] = P + d; disp_pts.append(P[::2]); disp_vec.append(d[::2])
bt = cKDTree(np.concatenate(disp_pts)); BV = np.concatenate(disp_vec)
def interp(P, k=24, s=0.008):
    dd, ii = bt.query(P, k=k); w = np.exp(-((dd - dd[:, :1]) / s) ** 2); w /= w.sum(1, keepdims=True)
    return (BV[ii] * w[:, :, None]).sum(1)
ribs_old = cKDTree(np.concatenate([cur(k)[::3] for k in BONE]))
for k in BONE + CAGE + PART:
    if k in out: continue
    P = cur(k); d = interp(P)
    if k in PART:
        dr, _ = ribs_old.query(P); d = d * cs(dr, 0.008, 0.035)[:, None]
    out[k] = P + d
for k in ("右大胸筋腹部", "左大胸筋腹部"):
    if same(k): out[k] = ap(G4, M["w_%d" % mj["full"][k]].astype(float))
for k, Pn in out.items():
    mv = np.linalg.norm(Pn - cur(k), axis=1) * 1000
    rep[k] = (len(mv), round(float(np.median(mv)), 1), round(float(np.percentile(mv, 95)), 1), round(float(mv.max()), 1))
np.savez_compressed(OUT, **{k: v.astype(np.float32) for k, v in out.items()})
print("パーツ  頂点数  動いた量 mm（中央値・95%点・最大）")
for k, v in sorted(rep.items(), key=lambda kv: -kv[1][2]): print("  ", k, v)
