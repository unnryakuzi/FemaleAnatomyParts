# 露出（表から見えているか）を数える。.blend は保存しない
#  対象パーツの頂点（間引き）ごとに、体の外（1m 先）から前・後ろ・左右・斜め後ろの6方向で光線を当て、
#  最初に当たるのがそのパーツ自身（当たった点が頂点から 1.5mm 以内）なら「見えている」。どれか1方向で見えれば露出
#  見えるもの = 筋・骨・腱・歯・女性外皮（Breast_Base）。男性は 外皮・下着 を隠して同じ条件にする
# blender -b <blend> -P exposure.py -- <対象 base 名の json> <出力 json> [候補 npz] [間引き=8]
import bpy, sys, json, numpy as np
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
NAMES = json.load(open(a[0], encoding="utf-8")); OUT = a[1]
CAND = np.load(a[2]) if len(a) > 2 and a[2] not in ("", "-") else None
STEP = int(a[3]) if len(a) > 3 else 8
base = lambda n: n.split("(")[0].split(".")[0]
VIS = {c.name for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("表層筋", "深層筋", "靱帯・腱", "骨格", "歯", "女性外皮")}
vis_objs = {o for c in bpy.data.collections if c.name in VIS for o in c.all_objects if o.type == 'MESH'}
for o in bpy.context.scene.objects:
    for md in o.modifiers: md.show_viewport = False
    show = o in vis_objs
    o.hide_viewport = not show
for lc in bpy.context.view_layer.layer_collection.children:
    lc.exclude = False; lc.hide_viewport = False
tg = [o for o in vis_objs if base(o.name) in NAMES]
if CAND is not None:
    for o in tg:
        k = base(o.name)
        if k in CAND.files:
            w = CAND[k].astype(np.float64); Mi = np.array(o.matrix_world.inverted())
            o.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); sc = bpy.context.scene
s2 = 2 ** -0.5
DIRS = {"後ろ": (0, -1, 0), "前": (0, 1, 0), "右から": (1, 0, 0), "左から": (-1, 0, 0), "右後ろ": (s2, -s2, 0), "左後ろ": (-s2, -s2, 0)}   # 光線の向き（後ろ側 = +Y から -Y へ）
res = {}
for P in sorted(tg, key=lambda o: o.name):
    co = np.empty(len(P.data.vertices) * 3); P.data.vertices.foreach_get("co", co); M = np.array(P.matrix_world)
    W = (co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])[::STEP]
    seen = np.zeros(len(W), bool); per = {}
    for dn, d in DIRS.items():
        dv = Vector(d); c = 0
        for i, p in enumerate(W):
            pv = Vector(p)
            hit, loc, n, fi, ob, mx = sc.ray_cast(dg, pv - dv * 1.0, dv, distance=1.05)
            if hit and ob is not None and ob.original == P and (loc - pv).length < 0.0015:
                seen[i] = True; c += 1
        per[dn] = round(c / len(W) * 100, 2)
    res[base(P.name)] = dict(n=len(W), exposed=round(float(seen.mean()) * 100, 2), per=per)
    print(base(P.name), res[base(P.name)], flush=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("DONE")
