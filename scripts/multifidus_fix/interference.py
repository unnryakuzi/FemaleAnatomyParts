# 干渉（めり込み）を数える。.blend は保存しない
#  対象パーツの頂点（間引き）が、周りのパーツ（筋・骨・腱）の中へ 1mm 以上入っている数と最大の深さ。
#  中かどうかは、相手の面でいちばん近い点の外向き法線との符号で決める（男性版も同じ方法で数え、元データの重なりと比べる）
# blender -b <blend> -P interference.py -- <対象 base 名の json> <出力 json> [候補 npz（キー=base名, 値=ワールド座標）] [間引き=4]
import bpy, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]
NAMES = json.load(open(a[0], encoding="utf-8")); OUT = a[1]
CAND = np.load(a[2]) if len(a) > 2 and a[2] not in ("", "-") else None
STEP = int(a[3]) if len(a) > 3 else 4
TH = 0.001
base = lambda n: n.split("(")[0].split(".")[0]
for o in bpy.context.scene.objects:                                   # 非表示だと depsgraph から外れて BVH が作れない
    if o.hide_viewport: o.hide_viewport = False
    for md in o.modifiers: md.show_viewport = False                   # 女性の一部の腕の筋に DECIMATE がある。元の形で測る（2026-10-14）
    if o.name in bpy.context.view_layer.objects and o.hide_get(): o.hide_set(False)
for lc in bpy.context.view_layer.layer_collection.children:
    lc.exclude = False; lc.hide_viewport = False
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("表層筋", "深層筋", "靱帯・腱", "骨格")]
parts = sorted({o for c in USE for o in c.all_objects if o.type == 'MESH'}, key=lambda o: o.name)
tg = [o for o in parts if base(o.name) in NAMES]
if CAND is not None:
    for o in tg:
        k = base(o.name)
        if k in CAND.files:
            w = CAND[k].astype(np.float64); Mi = np.array(o.matrix_world.inverted())
            o.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
def wverts(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
bb = {}
for o in parts:
    w = wverts(o); bb[o] = (w.min(0), w.max(0))
cache = {}
def tree(o):
    if o not in cache:
        cache[o] = (BVHTree.FromObject(o, dg), np.array(o.matrix_world.inverted()), np.array(o.matrix_world.to_3x3()))
    return cache[o]
res = {}
for P in tg:
    W = wverts(P)[::STEP]; lo, hi = W.min(0) - TH, W.max(0) + TH; pr = {}
    for Q in parts:
        if Q is P: continue
        qlo, qhi = bb[Q]
        if np.any(qlo > hi) or np.any(qhi < lo): continue
        sel = np.where(np.all((W > qlo) & (W < qhi), 1))[0]
        if not len(sel): continue
        T, Mi, M3 = tree(Q); Minv_T = np.linalg.inv(M3).T
        L = W[sel] @ Mi[:3, :3].T + Mi[:3, 3]; deep = []
        for v in L:
            loc, n, _, _ = T.find_nearest(Vector(v))
            if loc is None: continue
            dw = M3 @ (np.array(loc) - v); nw = Minv_T @ np.array(n); nw /= np.linalg.norm(nw)
            d = float(dw @ nw)                                        # 正 = 相手の面の内側
            if d > TH: deep.append(d)
        if deep:
            pr[base(Q.name) + ("" if Q.name.split("(")[0] == base(Q.name) else Q.name[len(base(Q.name)):].split("(")[0])] = [len(deep), round(len(deep) / len(W) * 100, 2), round(max(deep) * 1000, 1)]
    res[base(P.name)] = dict(n=len(W), pairs=pr)
    tot = sum(v[0] for v in pr.values()); print("%s 対象%d点 干渉 %d点 相手%d個" % (base(P.name), len(W), tot, len(pr)), flush=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("DONE", OUT)
