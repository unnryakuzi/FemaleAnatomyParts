# 腹壁の深い層の下端（恥骨まわり）だけを移し直した形にし、上は今の形のまま残す（システムの Python）
#  今の形 = v1.68.0 で Tポーズ版から取った形（外腹斜筋・白線の変形だけで移し、覆う面の内側に押し込み済み。上腹部はこちらが女性の外腹斜筋に合う）
#  移し直した形 = transfer_parts.py の結果（周り全体の変形。恥骨まわりで潰れない）
#  重み w(z): z <= z0 で 1、z0〜z1 でコサインで 0 へ（CLAUDE.md の段差を出さない定型）。錐体筋は全体を移し直した形にする
# python blend_lower.py <work/wb> <移し直した npz> <出力 npz> <z0> <z1>
import sys, json, numpy as np
W, NEW, OUT = sys.argv[1:4]; z0, z1 = float(sys.argv[4]), float(sys.argv[5])
fj = json.load(open(W + "/female.json", encoding="utf-8")); F = np.load(W + "/female.npz"); N = np.load(NEW)
out = {}
for k in N.files:
    new = N[k].astype(np.float64); cur = F["w_%d" % fj["full"][k]].astype(np.float64)
    if "錐体筋" in k:
        w = np.ones(len(cur))
    else:
        t = np.clip((cur[:, 2] - z0) / (z1 - z0), 0, 1); w = (1 + np.cos(np.pi * t)) / 2
    res = cur + w[:, None] * (new - cur); out[k] = res.astype(np.float32)
    mv = np.linalg.norm(res - cur, axis=1) * 1000
    print(k, "動いた頂点 %d / %d  最大 %.1fmm" % ((mv > 0.1).sum(), len(mv), mv.max()))
np.savez_compressed(OUT, **out)
