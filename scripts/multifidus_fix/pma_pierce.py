# 大胸筋の腹部のうち正面から見える先端の頂点について、すぐ奥（+Y）にある面までの距離と、その面のパーツを調べる。.blend は保存しない
#  出ている高さ = 頂点から奥へ光線を飛ばし、大胸筋の腹部自身を抜けた先で最初に当たる「ほかのパーツの表面」までの距離
#  あわせて、頂点が腹直筋・外腹斜筋・前鋸筋の中にあるか（突き抜けて中から出ているか）を交差回数で調べる
# blender -b <blend> -P pma_pierce.py -- <vis json> <vis_now json> <出力 json>
import bpy, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; V1, V0, OUT = a
v1 = json.load(open(V1, encoding="utf-8")); v0 = json.load(open(V0, encoding="utf-8"))
sc = bpy.context.scene; vl = bpy.context.view_layer
base = lambda n: n.split("(")[0].split(".")[0]
for lc in vl.layer_collection.children: lc.exclude = False; lc.hide_viewport = False
vl.update(); dg = bpy.context.evaluated_depsgraph_get()
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格", "女性外皮")]
parts = sorted({o for c in USE for o in c.all_objects if o.type == 'MESH'}, key=lambda o: o.name)
res = {}
for P in [o for o in sc.objects if o.type == 'MESH' and base(o.name) in ("右大胸筋腹部", "左大胸筋腹部")]:
    k = base(P.name); new = sorted(set(v1[k]["per_idx"]["正面"]) - set(v0[k]["per_idx"]["正面"]))
    M = P.matrix_world; W = [M @ P.data.vertices[i].co for i in new]
    lo = Vector((min(w.x for w in W), min(w.y for w in W), min(w.z for w in W))) - Vector((0.03, 0.03, 0.03)); hi = Vector((max(w.x for w in W), max(w.y for w in W), max(w.z for w in W))) + Vector((0.03, 0.03, 0.03))
    trees = []
    for Q in parts:
        if Q is P: continue
        bb = [Q.matrix_world @ Vector(c) for c in Q.bound_box]
        if any(max(b[i] for b in bb) < lo[i] or min(b[i] for b in bb) > hi[i] for i in range(3)): continue
        trees.append((Q, BVHTree.FromObject(Q, dg), Q.matrix_world.inverted(), Q.matrix_world))
    hts, behind, inside = [], {}, {}
    for w in W:
        best = None
        for Q, T, Mi, Mw in trees:
            o = Mi @ w; d = (Mi.to_3x3() @ Vector((0, 1, 0))).normalized()
            hit = T.ray_cast(o, d, 0.05)
            if hit[0] is not None:
                dist = ((Mw @ hit[0]) - w).length
                if best is None or dist < best[0]: best = (dist, base(Q.name))
            # 中にあるか（6方向の交差回数）
            if base(Q.name)[1:] in ("腹直筋", "外腹斜筋", "前鋸筋"):
                odd = 0
                for ax in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    c, p = 0, o.copy(); axv = (Mi.to_3x3() @ Vector(ax)).normalized()
                    for _ in range(32):
                        h = T.ray_cast(p, axv, 1.0)
                        if h[0] is None: break
                        c += 1; p = h[0] + axv * 1e-5
                    odd += c % 2
                if odd >= 4: inside[base(Q.name)] = inside.get(base(Q.name), 0) + 1
        if best: hts.append(best[0]); behind[best[1]] = behind.get(best[1], 0) + 1
    h = np.array(hts) * 1000
    res[k] = dict(n=len(W), height_mm=[round(float(np.percentile(h, q)), 1) for q in (10, 50, 90, 100)], behind=behind, inside=inside)
    print(k, "見える先端", len(W), "奥の面までの距離 mm（10/50/90/最大）", res[k]["height_mm"], "奥の面のパーツ", behind, "中にある頂点", inside)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
