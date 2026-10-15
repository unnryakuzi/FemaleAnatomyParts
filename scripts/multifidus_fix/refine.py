# 置き直したパーツを、形を変えずに平行移動（剛体）して、干渉と露出を減らす。.blend は保存しない（結果は npz）
#  点数 = 男性版を超える干渉（%・相手ごとの和） + EXPW（既定2）× 男性版を超える露出（%） + 0.3 × 移動量（mm）
#  座標ごとに ±3mm を試して良くなる向きへ進め、最後に ±1.5mm で詰める。他のパーツの置き方は入力 npz のまま（順に確定していく）
# blender -b 3DAnatomyFemale.blend -P refine.py -- <入力 npz> <int_male.json> <exp_male.json> <対象 json> <出力 npz> <ログ json>
import bpy, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]
INP, MI, ME, TJ, OUT, LOG = a
X = dict(np.load(INP)); male_int = json.load(open(MI, encoding="utf-8")); male_exp = json.load(open(ME, encoding="utf-8"))
TARGETS = json.load(open(TJ, encoding="utf-8"))
TH = 0.001; ISTEP, ESTEP = 6, 10
import os
ISTEP = int(os.environ.get("ISTEP", ISTEP)); ESTEP = int(os.environ.get("ESTEP", ESTEP))
import os
EXPW = float(os.environ.get("EXPW", "2"))   # 露出の重み（既定 2。表から見えては困るパーツは大きくする）
base = lambda n: n.split("(")[0].split(".")[0]
def key(n):
    b = base(n); return b + ("" if n.split("(")[0] == b else n[len(b):].split("(")[0])
VIS = {c.name for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格", "歯", "女性外皮")}
vis_objs = {o for c in bpy.data.collections if c.name in VIS for o in c.all_objects if o.type == 'MESH'}
for o in bpy.context.scene.objects:
    for md in o.modifiers: md.show_viewport = False
    o.hide_viewport = o not in vis_objs
for lc in bpy.context.view_layer.layer_collection.children:
    lc.exclude = False; lc.hide_viewport = False
INT = [o for o in vis_objs if any(c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格") for c in o.users_collection)]
byb = {}
for o in vis_objs: byb.setdefault(base(o.name), o)
def setco(o, w):
    Mi = np.array(o.matrix_world.inverted()); o.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
for k, w in X.items(): setco(byb[k], w.astype(np.float64))
bpy.context.view_layer.update()
def wverts(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
bb = {o: (lambda w: (w.min(0), w.max(0)))(wverts(o)) for o in INT}
cache = {}
def tree(o):
    if o not in cache:
        dg = bpy.context.evaluated_depsgraph_get(); M3 = np.array(o.matrix_world.to_3x3())
        cache[o] = (BVHTree.FromObject(o, dg), np.array(o.matrix_world.inverted()), M3, np.linalg.inv(M3).T)
    return cache[o]
def interference(P, Z):
    lo, hi = Z.min(0) - TH, Z.max(0) + TH; mb = male_int.get(base(P.name), {}).get("pairs", {}); ex = 0.0
    for Q in INT:
        if Q is P: continue
        qlo, qhi = bb[Q]
        if np.any(qlo > hi) or np.any(qhi < lo): continue
        sel = np.where(np.all((Z > qlo) & (Z < qhi), 1))[0]
        if not len(sel): continue
        T, Mi, M3, MiT = tree(Q); L = Z[sel] @ Mi[:3, :3].T + Mi[:3, 3]; c = 0
        for v in L:
            loc, n, _, _ = T.find_nearest(Vector(v))
            if loc is None: continue
            nw = MiT @ np.array(n); nn = np.linalg.norm(nw)
            if nn > 0 and float((M3 @ (np.array(loc) - v)) @ nw) / nn > TH: c += 1
        if c: ex += max(0.0, c / len(Z) * 100 - mb.get(key(Q.name), [0, 0.0, 0])[1])
    return ex
s2 = 2 ** -0.5
DIRS = [(0, -1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0), (s2, -s2, 0), (-s2, -s2, 0)]
if os.environ.get("DIRS14") == "1":   # 上下斜め45°の8方向を足す（exposure.py の 14dirs と同じ）
    for x, y in ((0, -1), (0, 1), (1, 0), (-1, 0)):
        DIRS += [(x * s2, y * s2, -s2), (x * s2, y * s2, s2)]
def exposure(P, Z):
    dg = bpy.context.evaluated_depsgraph_get(); sc = bpy.context.scene; seen = np.zeros(len(Z), bool)
    for d in DIRS:
        dv = Vector(d)
        for i, p in enumerate(Z):
            if seen[i]: continue
            pv = Vector(p); hit, loc, n, fi, ob, mx = sc.ray_cast(dg, pv - dv, dv, distance=1.05)
            if hit and ob is not None and ob.original == P and (loc - pv).length < 0.0015: seen[i] = True
    return float(seen.mean()) * 100
log = {}
for k in TARGETS:
    P = byb[k]; W0 = X[k].astype(np.float64); me_m = male_exp.get(k, {}).get("exposed", 0.0)
    def evaluate(t):
        W = W0 + t; setco(P, W); bpy.context.view_layer.update(); cache.pop(P, None)
        ii = interference(P, W[::ISTEP]); ee = max(0.0, exposure(P, W[::ESTEP]) - me_m)
        return ii + EXPW * ee + 0.3 * np.linalg.norm(t) * 1000, ii, ee
    t = np.zeros(3); best = evaluate(t); hist = [(t.tolist(), best)]
    for step in (0.003, 0.0015):
        improved = True; it = 0
        while improved and it < 8:
            improved = False; it += 1
            for ax in range(3):
                for sg in (1, -1):
                    t2 = t.copy(); t2[ax] += sg * step
                    r = evaluate(t2)
                    if r[0] < best[0] - 0.05: t, best, improved = t2, r, True; hist.append((t.tolist(), r))
    X[k] = (W0 + t).astype(np.float32); setco(P, X[k].astype(np.float64)); bpy.context.view_layer.update(); cache.pop(P, None)
    for o in INT:
        if o is P: bb[o] = (X[k].min(0), X[k].max(0))
    log[k] = dict(t_mm=(t * 1000).round(1).tolist(), score=round(best[0], 1), interference=round(best[1], 1), exposure=round(best[2], 1), start=hist[0][1])
    print(k, log[k], flush=True)
np.savez_compressed(OUT, **X); json.dump(log, open(LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("DONE")
