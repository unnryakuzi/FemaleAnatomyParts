# 販売中の元の多裂筋（形はきれい・上は椎骨より 5〜9cm 高い）を、高さ z の関数だけでずらして椎骨に合わせる（システムの Python）
#  目標 = multifidus_skin.py の椎骨追従の位置。元との差（dy, dz）を 10mm ごとの中央値にし、
#  ガウス核（σ=30mm）でならした滑らかな関数 Δ(z) にして、全頂点に1回だけ足す（CLAUDE.md: Z依存変形はクリーン状態×単一パス・厚み保持）
#  dx は足さない（左右の幅は元のまま）。z の写像は単調（傾き 1+dΔz/dz > 0）であることを確かめる
# python multifidus_zshift.py <元 npz（キー=右多裂筋/左多裂筋）> <椎骨追従 npz> <出力 npz>
import sys, numpy as np
ORIG, SKIN, OUT = sys.argv[1:4]
# 首だけ直す場合: z0 より下は元のまま（Δ=0）、z0〜z1 でコサインで Δ を効かせ、z1 より上は全部効かせる（元の座標の z, m）
Z01 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else None
O = np.load(ORIG); S = np.load(SKIN)
o = O["右多裂筋"].astype(float); t = S["右多裂筋"].astype(float); d = t - o
zc = np.arange(o[:, 2].min(), o[:, 2].max() + 0.01, 0.01); med = []
for z in zc:
    m = np.abs(o[:, 2] - z) < 0.005
    med.append(np.median(d[m], 0) if m.sum() > 20 else [np.nan] * 3)
med = np.array(med); ok = ~np.isnan(med[:, 0]); zc, med = zc[ok], med[ok]
def delta(z, sig=0.030):
    w = np.exp(-((z[:, None] - zc[None, :]) / sig) ** 2); w /= w.sum(1, keepdims=True)
    d = w @ med
    if Z01:
        t = np.clip((z - Z01[0]) / (Z01[1] - Z01[0]), 0, 1); d = d * ((1 - np.cos(np.pi * t)) / 2)[:, None]
    return d
zz = np.linspace(o[:, 2].min(), o[:, 2].max(), 2000); dd = delta(zz)
slope = 1 + np.gradient(dd[:, 2], zz)
print("z 写像の傾き min %.3f max %.3f（>0 なら折れない）" % (slope.min(), slope.max()))
for z in np.arange(0.95, 1.70, 0.05):
    print("  z %.2f  Δy %+6.1f  Δz %+6.1f mm" % (z, *(delta(np.array([z]))[0, 1:] * 1000)))
out = {}
for k in ("右多裂筋", "左多裂筋"):
    v = O[k].astype(float); dl = delta(v[:, 2]); v2 = v.copy(); v2[:, 1] += dl[:, 1]; v2[:, 2] += dl[:, 2]; out[k] = v2.astype(np.float32)
    print(k, "z %.3f..%.3f" % (v2[:, 2].min(), v2[:, 2].max()))
np.savez_compressed(OUT, **out)
