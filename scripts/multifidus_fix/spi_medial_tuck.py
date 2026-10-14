# 下後鋸筋の内側の端（棘突起のわき）だけを前へ入れる（システムの Python）
#  Δy(x) = -A × w(|x|)、w は |x|<=x0 で 1、x0〜x1 でコサインで 0 へ。x だけの関数なので同じ x の列は同じだけ動き、厚みは変わらない（ずれ変形・面は反転しない）
# python spi_medial_tuck.py <入力 npz> <出力 npz> <A mm> <x0 mm> <x1 mm>
import sys, numpy as np
INP, OUT = sys.argv[1:3]; A, x0, x1 = (float(v) / 1000 for v in sys.argv[3:6])
F = dict(np.load(INP))
for k in ("右下後鋸筋", "左下後鋸筋"):
    v = F[k].astype(float); ax = np.abs(v[:, 0]); t = np.clip((ax - x0) / (x1 - x0), 0, 1); w = (1 + np.cos(np.pi * t)) / 2
    v[:, 1] -= A * w; F[k] = v.astype(np.float32)
    print(k, "動いた頂点 %d / %d" % ((w > 0.01).sum(), len(w)), "x 範囲 %.0f〜%.0f mm" % (ax.min() * 1000, ax.max() * 1000))
np.savez_compressed(OUT, **F)
