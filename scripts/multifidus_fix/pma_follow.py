# 大胸筋の腹部を、下の肋骨・肋軟骨と同じだけ動かす（システムの Python）
#  2026-10-15: 他の大胸筋と同じ G4 の位置へ寄せると、腱の色の端が乳房の下から白い三角にのぞいた（外から見える形が変わる）。
#  肋骨の動き（候補 − 今）を 4mm の格子に σ12mm でならし、大胸筋の腹部の各頂点に同じだけ足す。上腕骨から 30mm 以内は今のまま、90mm で全量
# python pma_follow.py <work/g4> <候補 npz（肋骨を含む）> <出力 npz（候補に大胸筋の腹部を差し替えたもの）>
import sys, json, numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter, map_coordinates
W, CAND, OUT = sys.argv[1:4]
fj = json.load(open(W + "/female.json", encoding="utf-8")); F = np.load(W + "/female.npz"); C = np.load(CAND)
cur = lambda k: F["w_%d" % fj["full"][k]].astype(float)
is_bone = lambda k: (("肋骨" in k or "肋軟骨" in k) and "挙筋" not in k) or k in ("胸骨柄", "胸骨体", "剣状突起")
bones = [k for k in C.files if is_bone(k)]
bp = np.concatenate([cur(k) for k in bones]); bv = np.concatenate([C[k].astype(float) - cur(k) for k in bones])
VX = 0.004; lo = bp.min(0) - 0.08; shp = np.ceil((bp.max(0) + 0.08 - lo) / VX).astype(int) + 1
gi = np.round((bp - lo) / VX).astype(int); Wg = np.zeros(shp); np.add.at(Wg, tuple(gi.T), 1.0); Dg = [np.zeros(shp) for _ in range(3)]
for c in range(3): np.add.at(Dg[c], tuple(gi.T), bv[:, c])
SG = 0.012 / VX; Ws = gaussian_filter(Wg, SG); Ds = [gaussian_filter(D, SG) for D in Dg]
def field(P):
    q = ((P - lo) / VX).T; w = map_coordinates(Ws, q, order=1, mode="nearest")
    return np.stack([map_coordinates(D, q, order=1, mode="nearest") for D in Ds], 1) / np.maximum(w, 1e-12)[:, None], w
def cs(d, d0, d1):
    t = np.clip((d - d0) / (d1 - d0), 0, 1); return (1 + np.cos(np.pi * t)) / 2
hum = cKDTree(np.concatenate([F["p_%d" % m["slot"]] for k, m in fj["meta"].items() if "上腕骨" in k]).astype(float))
out = {k: C[k] for k in C.files}
for k in ("右大胸筋腹部", "左大胸筋腹部"):
    P = cur(k); d, w = field(P); dh, _ = hum.query(P); s = 1 - cs(dh, 0.030, 0.090)
    out[k] = (P + d * s[:, None]).astype(np.float32); mv = np.linalg.norm(d * s[:, None], axis=1) * 1000
    print("  %s 動いた量 中央値 %.1f / 95%%点 %.1f / 最大 %.1f mm" % (k, np.median(mv), np.percentile(mv, 95), mv.max()))
np.savez_compressed(OUT, **out)
