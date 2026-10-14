# 形の崩れを数える（システムの Python）: 男性の同じ面と比べて、面の向きが 90° 以上ひっくり返った面（折れ・潰れ）の割合など
#  女性の左多裂筋のように男性と頂点数が違うものは、反対側の男性パーツの鏡像と比べる
# python shape_metrics.py <work/wc> [候補 npz ...]   ※候補 npz のキー = base 名、値 = ワールド座標
import sys, json, numpy as np
W = sys.argv[1]; CANDS = sys.argv[2:]
mj = json.load(open(W + "/male.json", encoding="utf-8")); fj = json.load(open(W + "/female.json", encoding="utf-8"))
M = np.load(W + "/male.npz"); F = np.load(W + "/female.npz"); C = [np.load(c) for c in CANDS]

def tris(Z, s):
    lv, ls, lt = Z["fl_%d" % s], Z["fs_%d" % s], Z["ft_%d" % s]
    out = []
    for k in range(3, int(lt.max()) + 1):                      # 多角形を扇形に三角形へ
        sel = np.where(lt == k)[0]
        for j in range(1, k - 1):
            out.append(np.stack([lv[ls[sel]], lv[ls[sel] + j], lv[ls[sel] + j + 1]], 1))
    return np.concatenate(out)

def normals(w, T):
    n = np.cross(w[T[:, 1]] - w[T[:, 0]], w[T[:, 2]] - w[T[:, 0]]); a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a, 1e-15)[:, None], a

def metrics(wm, wf, T, E):
    nm, am = normals(wm, T); nf, af = normals(wf, T); ok = (am > 1e-12) & (af > 1e-12)
    dot = (nm * nf).sum(1)[ok]
    lm = np.linalg.norm(wm[E[:, 0]] - wm[E[:, 1]], axis=1); lf = np.linalg.norm(wf[E[:, 0]] - wf[E[:, 1]], axis=1)
    r = lf[lm > 1e-9] / lm[lm > 1e-9]
    return dict(flip=round(float((dot < 0).mean()) * 100, 2), gt60=round(float((dot < 0.5).mean()) * 100, 2),
                er_p1=round(float(np.percentile(r, 1)), 2), er_p99=round(float(np.percentile(r, 99)), 2))

rows = {}
for k, s in sorted(fj["full"].items()):
    src, mir = k, 1.0
    if not (k in mj["meta"] and mj["meta"][k]["n"] == fj["meta"][k]["n"] and mj["meta"][k]["sig"] == fj["meta"][k]["sig"]):
        src, mir = ("左" if k[0] == "右" else "右") + k[1:], -1.0
    sm = mj["full"][src]; wm = M["w_%d" % sm] * np.array([mir, 1, 1]); T = tris(M, sm); E = M["e_%d" % sm]
    if mir < 0: T = T[:, ::-1]                                  # 鏡に映すと面の向きが逆になるので頂点順を戻す
    r = {"今": metrics(wm, F["w_%d" % s], T, E)}
    for name, c in zip(CANDS, C):
        if k in c.files: r[name.split("/")[-1].replace(".npz", "")] = metrics(wm, c[k].astype(np.float64), T, E)
    rows[k] = r
keys = ["今"] + [n.split("/")[-1].replace(".npz", "") for n in CANDS]
print("%-12s " % "パーツ" + " | ".join("%-28s" % k for k in keys))
for k, r in sorted(rows.items(), key=lambda kv: -kv[1]["今"]["flip"]):
    print("%-12s " % k + " | ".join(("反転%5.2f%% >60°%5.2f%% 辺比%.2f-%.2f" % (r[x]["flip"], r[x]["gt60"], r[x]["er_p1"], r[x]["er_p99"])) if x in r else " " * 28 for x in keys))
json.dump(rows, open(W + "/shape_metrics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
