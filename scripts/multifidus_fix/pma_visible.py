# 大胸筋の腹部のうち、体の外から見える頂点を数える（商品画像と同じ表示＝骨格・女性外皮・筋肉・歯・靱帯腱）。.blend は保存しない
#  正面・左右 20°/35°・下から 15°・上から 15° の 7 方向から光線を飛ばし、最初に当たるのが大胸筋の腹部のその頂点（1mm 以内）なら「見える」
#  見える頂点が乳房（Breast_Base）の下の縁からどれだけ下にあるかも出す（正面から見て同じ左右位置 ±3mm の乳房の最も低い所との高さの差）
# blender -b <blend> -P pma_visible.py -- <出力 json>
import bpy, sys, json, math, numpy as np
from mathutils import Vector, Matrix
OUT = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene; vl = bpy.context.view_layer
base = lambda n: n.split("(")[0].split(".")[0]
SHOW = {"骨格", "女性外皮", "筋肉", "歯", "靱帯・腱"}
def cols_of(o):
    acc = set()
    def up(c):
        for p in bpy.data.collections:
            if c.name in p.children and p.name not in acc: acc.add(p.name); up(p)
    for c in o.users_collection: acc.add(c.name); up(c)
    return acc
for lc in vl.layer_collection.children: lc.exclude = False; lc.hide_viewport = False
for o in sc.objects:
    cs = cols_of(o)
    show = o.type == 'MESH' and bool(cs & SHOW) and not (cs & {"_RenderSetup", "_ガイドライン"}) and not o.name.startswith(("CURRENT_", "DIAG_", "Swimwear_"))
    o.hide_viewport = False
    if o.name in vl.objects: o.hide_set(not show)
    for md in o.modifiers:
        if md.type == 'DECIMATE': md.show_viewport = False
vl.update(); dg = bpy.context.evaluated_depsgraph_get()
pma = [o for o in sc.objects if o.type == 'MESH' and base(o.name) in ("右大胸筋腹部", "左大胸筋腹部")]
br = next(o for o in sc.objects if o.type == 'MESH' and o.name.startswith("Breast_Base"))
def wv(o):
    e = o.evaluated_get(dg); me = e.to_mesh(); co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); e.to_mesh_clear()
    M = np.array(o.matrix_world); return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
B = wv(br)
DIRS = {"正面": (0, 0), "右20": (20, 0), "左20": (-20, 0), "右35": (35, 0), "左35": (-35, 0), "下から15": (0, 15), "上から15": (0, -15)}
res = {}
for P in pma:
    W = wv(P); vis = np.zeros(len(W), bool); per = {}; per_idx = {}
    for nm, (yaw, pitch) in DIRS.items():
        R = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Matrix.Rotation(math.radians(pitch), 3, 'X')
        D = (R @ Vector((0, 1, 0))).normalized()                         # カメラから体へ向かう向き（体は −Y を向いている）
        cnt = 0; idx_dir = []
        for i, v in enumerate(W):
            o = Vector(v) - D * 1.5
            hit, loc, nrm, idx, ob, mat = sc.ray_cast(dg, o, D, distance=3.0)
            if hit and ob is not None and ob.original is P and (loc - Vector(v)).length < 0.001:
                vis[i] = True; cnt += 1; idx_dir.append(i)
        per[nm] = cnt; per_idx[nm] = idx_dir
    # 乳房の下の縁からの高さの差（正面から見て同じ x ±3mm の乳房の最も低い点）
    gaps = []
    for v in W[vis]:
        m = np.abs(B[:, 0] - v[0]) < 0.003
        if m.any(): gaps.append(float(B[m, 2].min() - v[2]))
    res[base(P.name)] = dict(n=len(W), visible=int(vis.sum()), per_dir=per, per_idx=per_idx, idx=np.where(vis)[0].tolist(),
                             gap_mm=[round(float(np.percentile(gaps, q)) * 1000, 1) for q in (5, 50, 95)] if gaps else None,
                             vis_center=W[vis].mean(0).round(4).tolist() if vis.any() else None, vis_zrange=[round(float(W[vis, 2].min()), 4), round(float(W[vis, 2].max()), 4)] if vis.any() else None)
    print(base(P.name), "見える頂点", int(vis.sum()), "/", len(W), per, "乳房の下の縁より下 mm (5/50/95%)", res[base(P.name)]["gap_mm"])
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
