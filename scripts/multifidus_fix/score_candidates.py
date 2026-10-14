# build_candidates.py の候補ごとに、既存パーツとの干渉（男性版を超える分）を数える。.blend は保存しない
#  相手は既存パーツだけ（足したパーツと多裂筋どうしの干渉は、選んだあとで interference.py で全体を測る）
# blender -b 3DAnatomyFemale.blend -P score_candidates.py -- <work/wc> <cands.json> <int_male.json> <出力 json>
import bpy, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; W, CJ, MJ, OUT = a
C = json.load(open(CJ, encoding="utf-8")); male_int = json.load(open(MJ, encoding="utf-8"))
mj = json.load(open(W + "/male.json", encoding="utf-8")); fj = json.load(open(W + "/female.json", encoding="utf-8")); MZ = np.load(W + "/male.npz")
TH = 0.001
base = lambda n: n.split("(")[0].split(".")[0]
def key(n):
    b = base(n); return b + ("" if n.split("(")[0] == b else n[len(b):].split("(")[0])
for o in bpy.context.scene.objects:
    if o.hide_viewport: o.hide_viewport = False
    for md in o.modifiers: md.show_viewport = False
    if o.name in bpy.context.view_layer.objects and o.hide_get(): o.hide_set(False)
for lc in bpy.context.view_layer.layer_collection.children:
    lc.exclude = False; lc.hide_viewport = False
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格")]
skip = set(fj["full"])
parts = sorted({o for c in USE for o in c.all_objects if o.type == 'MESH' and base(o.name) not in skip}, key=lambda o: o.name)
bb = {}
for o in parts:
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
    w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]; bb[o] = (w.min(0), w.max(0))
cache = {}
def tree(o):
    if o not in cache:
        M3 = np.array(o.matrix_world.to_3x3()); cache[o] = (BVHTree.FromObject(o, dg), np.array(o.matrix_world.inverted()), M3, np.linalg.inv(M3).T)
    return cache[o]
def score(k, Z):
    lo, hi = Z.min(0) - TH, Z.max(0) + TH; pr = {}
    for Q in parts:
        qlo, qhi = bb[Q]
        if np.any(qlo > hi) or np.any(qhi < lo): continue
        sel = np.where(np.all((Z > qlo) & (Z < qhi), 1))[0]
        if not len(sel): continue
        T, Mi, M3, MiT = tree(Q); L = Z[sel] @ Mi[:3, :3].T + Mi[:3, 3]; c = 0; mx = 0.0
        for v in L:
            loc, n, _, _ = T.find_nearest(Vector(v))
            if loc is None: continue
            nw = MiT @ np.array(n); d = float((M3 @ (np.array(loc) - v)) @ nw / np.linalg.norm(nw))
            if d > TH: c += 1; mx = max(mx, d)
        if c: pr[key(Q.name)] = (c / len(Z) * 100, mx * 1000)
    mb = male_int.get(k, {}).get("pairs", {})
    ex = {q: (fr - mb.get(q, [0, 0.0, 0])[1], mx) for q, (fr, mx) in pr.items()}
    ex = {q: v for q, v in ex.items() if v[0] > 0}
    return round(sum(v[0] for v in ex.values()), 2), sorted(((q, round(v[0], 1), round(v[1], 1)) for q, v in ex.items()), key=lambda x: -x[1])[:3]
res = {}
for k, info in C.items():
    src = info["src"]; X = MZ["w_%d" % mj["full"][src]].astype(np.float64)
    if info["mirror"]: X = X * np.array([-1.0, 1.0, 1.0])
    Xs = X[:: max(4, len(X) // 2500)]; rows = []
    for c in info["cands"]:
        T = np.array(c["T"]); Z = Xs @ T[:3, :3].T + T[:3, 3]
        ex, worst = score(k, Z); rows.append(dict(id=c["id"], excess=ex, worst=worst, dev_med=c["dev_med"], sv=c["sv"]))
    res[k] = rows
    best = sorted(rows, key=lambda r: r["excess"] + r["dev_med"])[:3]
    print(k, [(r["id"][:12], r["excess"], r["dev_med"]) for r in best], flush=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("DONE")
