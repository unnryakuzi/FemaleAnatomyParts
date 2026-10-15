# 腹壁の深い層（内腹斜筋・腹横筋・腹直筋・錐体筋）を男性の形から作り直す（システムの Python）。結果は npz（ワールド座標）
#  v1.68.0 で Tポーズ版から移した形は、外腹斜筋・白線に合わせて押し込んだため折れが多く（腹横筋 1288 本、男性 0 本）、
#  腹横筋の横は内腹斜筋から 30〜40mm 内側へつぶれていた（2026-10-15 断面で確認）。
#  男性の高さ z ごとに、周りの「動かさない／置き直した」パーツ（外腹斜筋・白線・肋骨と肋軟骨（置き直した後）・寛骨）の
#  男性→女性の対応から 3 次元のアフィン変換を重み付き最小二乗で求め（高さ方向はガウス σ）、同じ高さの頂点に同じ変換を掛ける。
#  変換は高さだけの関数なので、筋の厚みと形は保たれる（CLAUDE.md の「shift は z の一次元関数のみ」）
# python abd_rebuild.py <work/g4> <置き直したかごの npz> <出力 npz> [σ mm=30]
import sys, json, numpy as np
W, CAGE, OUT = sys.argv[1:4]; SIG = (float(sys.argv[4]) if len(sys.argv) > 4 else 30.0) / 1000
fj = json.load(open(W + "/female.json", encoding="utf-8")); F = np.load(W + "/female.npz")
mj = json.load(open(W + "/male.json", encoding="utf-8")); M = np.load(W + "/male.npz"); C = np.load(CAGE)
def same(k):
    a, b = fj["meta"].get(k), mj["meta"].get(k)
    return a is not None and b is not None and a["n"] == b["n"] and a["sig"] == b["sig"]
def pair(k, full=True):
    a, b = fj["meta"][k], mj["meta"][k]
    if full and k in fj["full"] and k in mj["full"]:
        P = M["w_%d" % b["slot"]].astype(float); Q = C[k].astype(float) if k in C.files else F["w_%d" % a["slot"]].astype(float)
        return P[::4], Q[::4]
    idx = F["i_%d" % a["slot"]]; P = M["p_%d" % b["slot"]].astype(float)
    Q = (C[k].astype(float)[idx] if k in C.files else F["p_%d" % a["slot"]].astype(float))
    return P, Q
KAN = {5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}
CLS = {"外腹斜筋": ["右外腹斜筋", "左外腹斜筋"], "白線": ["白線"], "寛骨": ["右寛骨", "左寛骨"],
       "肋骨": [s + "第%s肋骨" % KAN[n] for s in "右左" for n in range(7, 13)] + [s + "第%s肋軟骨" % KAN[n] for s in "右左" for n in (5, 6, 7)] + ["右肋軟骨", "左肋軟骨", "胸骨体"]}
anc = {}
for c, ks in CLS.items():
    Ps, Qs = [], []
    for k in ks:
        if not same(k): print("  対応なし:", k); continue
        P, Q = pair(k); Ps.append(P); Qs.append(Q)
    anc[c] = (np.concatenate(Ps), np.concatenate(Qs)); print("  アンカー %s %d 点" % (c, len(anc[c][0])))
TARGET = [k for k in ("右内腹斜筋", "左内腹斜筋", "右腹横筋", "左腹横筋", "右腹直筋", "左腹直筋", "右錐体筋", "左錐体筋") if same(k)]
Xs = {k: M["w_%d" % mj["full"][k]].astype(float) for k in TARGET}
zall = np.concatenate([X[:, 2] for X in Xs.values()]); zc = np.arange(zall.min() - 0.01, zall.max() + 0.015, 0.005)
As = []; res = {c: [] for c in anc}
wmax = {c: max(np.exp(-((P[:, 2] - z) / SIG) ** 2 / 2).sum() for z in zc) for c, (P, Q) in anc.items()}
for z in zc:
    rows, rhs, ws = [], [], []
    for c, (P, Q) in anc.items():
        w = np.exp(-((P[:, 2] - z) / SIG) ** 2 / 2)
        if w.sum() < 1e-6 * wmax[c]: continue
        w = w / wmax[c]                                   # 種類ごとに「いちばん多い高さで合計 1」（点の多い外腹斜筋に引っ張られず、少ない高さでは効きが薄れる）
        rows.append(np.c_[P, np.ones(len(P))]); rhs.append(Q); ws.append(w)
    X = np.concatenate(rows); Y = np.concatenate(rhs); w = np.sqrt(np.concatenate(ws))[:, None]
    A, _, _, _ = np.linalg.lstsq(X * w, Y * w, rcond=None); As.append(A)
    for c, (P, Q) in anc.items():
        m = np.abs(P[:, 2] - z) < 0.0025
        if m.sum() > 20: res[c].append(np.linalg.norm(np.c_[P[m], np.ones(m.sum())] @ A - Q[m], axis=1))
As = np.array(As)
from scipy.ndimage import gaussian_filter1d
As = gaussian_filter1d(As, 15 / 5, axis=0, mode="nearest")             # 変換を高さ方向にさらにならす（σ 15mm）
print("当てはめの残差 mm（その高さのアンカー点）: 中央値 / 95%点")
for c, r in res.items():
    if r: r = np.concatenate(r) * 1000; print("  %-6s %.1f / %.1f" % (c, np.median(r), np.percentile(r, 95)))
out = {}
for k, X in Xs.items():
    i0 = np.clip(np.searchsorted(zc, X[:, 2]) - 1, 0, len(zc) - 2); t = ((X[:, 2] - zc[i0]) / (zc[i0 + 1] - zc[i0]))[:, None, None]
    A = As[i0] * (1 - t) + As[i0 + 1] * t
    out[k] = (np.einsum("ni,nij->nj", np.c_[X, np.ones(len(X))], A)).astype(np.float32)
    Fk = F["w_%d" % fj["full"][k]].astype(float); mv = np.linalg.norm(out[k] - Fk, axis=1) * 1000
    print("  %s 今の形からの差 中央値 %.1f / 95%%点 %.1f / 最大 %.1f mm" % (k, np.median(mv), np.percentile(mv, 95), mv.max()))
np.savez_compressed(OUT, **out); np.save(OUT.replace(".npz", "_affines.npy"), As)
