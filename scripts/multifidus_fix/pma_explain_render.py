# 大胸筋の腹部の置き方の説明画像を撮る（.blend は保存しない）
#  1) 見た目: 商品画像と同じ表示（頂点カラー）で胸の下を正面から
#  2) 大胸筋の腹部だけ（＋骨）: 水色＝ほかのパーツの外、赤＝ほかのパーツ（筋・骨・腱）の中に 1mm 以上埋まっている頂点
#     内外は interference.py と同じ（いちばん近い面の法線の向き＋光線の交差回数）
# blender -b <blend> -P pma_explain_render.py -- <出力フォルダ> <タグ>
import bpy, sys, os, math, numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; OUT, TAG = a[0], a[1]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; vl = bpy.context.view_layer
base = lambda n: n.split("(")[0].split(".")[0]
SHOW = {"骨格", "女性外皮", "筋肉", "歯", "靱帯・腱"}
def in_show(o):
    cs = set()
    def up(c, acc):
        for p in bpy.data.collections:
            if c.name in p.children: acc.add(p.name); up(p, acc)
    for c in o.users_collection: cs.add(c.name); up(c, cs)
    return bool(cs & SHOW) and not (cs & {"_RenderSetup", "_ガイドライン"})
for o in sc.objects:
    for md in o.modifiers: md.show_viewport = md.show_render = (md.type != 'DECIMATE')
pma = [o for o in sc.objects if o.type == 'MESH' and base(o.name) in ("右大胸筋腹部", "左大胸筋腹部")]
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格")]
parts = sorted({o for c in USE for o in c.all_objects if o.type == 'MESH'}, key=lambda o: o.name)
for o in parts:
    if o.hide_viewport: o.hide_viewport = False
for lc in vl.layer_collection.children: lc.exclude = False; lc.hide_viewport = False
vl.update(); dg = bpy.context.evaluated_depsgraph_get()
def wv(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world); return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
AX = [Vector(x) for x in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
def parity(T, v):
    odd = 0
    for ax in AX:
        c, p = 0, Vector(v)
        for _ in range(64):
            h = T.ray_cast(p, ax, 1e6)
            if h[0] is None: break
            c += 1; p = h[0] + ax * 1e-4
        odd += c % 2
    return odd >= 4
lin = lambda c: [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c] + [1.0]
CY, RD = lin((0.25, 0.8, 1.0)), lin((0.95, 0.1, 0.1))
stat = {}
for P in pma:
    W = wv(P); lo, hi = W.min(0) - 0.002, W.max(0) + 0.002; inside = np.zeros(len(W), bool); who = {}
    for Q in parts:
        if Q is P: continue
        q = wv(Q); 
        if np.any(q.min(0) > hi) or np.any(q.max(0) < lo): continue
        sel = np.where(np.all((W > q.min(0)) & (W < q.max(0)), 1))[0]
        if not len(sel): continue
        T = BVHTree.FromObject(Q, dg); Mi = np.array(Q.matrix_world.inverted()); M3 = np.array(Q.matrix_world.to_3x3()); MiT = np.linalg.inv(M3).T
        L = W[sel] @ Mi[:3, :3].T + Mi[:3, 3]
        for i, v in zip(sel, L):
            if inside[i]: continue
            loc, n, _, _ = T.find_nearest(Vector(v))
            if loc is None: continue
            dw = M3 @ (np.array(loc) - v); nw = MiT @ np.array(n); nn = np.linalg.norm(nw)
            if nn and float(dw @ nw) / nn > 0.001 and parity(T, v): inside[i] = True; who[base(Q.name)] = who.get(base(Q.name), 0) + 1
    col = np.where(inside[:, None], np.array(RD), np.array(CY))
    at = P.data.color_attributes.get("説明") or P.data.color_attributes.new("説明", 'FLOAT_COLOR', 'POINT')
    at.data.foreach_set("color", col.astype(np.float32).ravel())
    stat[base(P.name)] = (round(inside.mean() * 100, 1), sorted(who.items(), key=lambda x: -x[1])[:4])
print("埋まっている頂点の割合", stat)
sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "VERTEX"; sh.show_cavity = False
sc.world = sc.world or bpy.data.worlds.new("W"); sc.world.color = (0.72, 0.72, 0.72); sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 900, 640
cam = bpy.data.objects.new("_c", bpy.data.cameras.new("_c")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = "ORTHO"; cam.data.clip_end = 20
ctr = Vector((0.0, -0.0166, 1.3095))                                        # 3案で同じ視点にするため固定（今の大胸筋の腹部の中心）
def shoot(name, rot_deg, scale):
    q = Matrix.Rotation(math.radians(rot_deg), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X')
    cam.matrix_world = Matrix.Translation(ctr) @ q @ Matrix.Translation((0, 0, 3)); cam.data.ortho_scale = scale
    sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (TAG, name)); bpy.ops.render.render(write_still=True); print("SHOT", name)
# 1) 見た目（商品と同じ: 頂点カラー Col）
for o in sc.objects: o.hide_render = not (o.type == 'MESH' and in_show(o) and not o.name.startswith(("CURRENT_", "DIAG_", "Swimwear_")))
for P in pma:
    c = P.data.color_attributes.get("Col")
    if c: P.data.color_attributes.active_color = c
shoot("look_front", 0, 0.36); shoot("look_34", -35, 0.38)
# 2) 大胸筋の腹部だけ（＋骨は灰色）
bones = {o for c in bpy.data.collections if c.name == "骨格" for o in c.all_objects}
for o in sc.objects: o.hide_render = not (o in pma or o in bones)
for P in pma: P.data.color_attributes.active_color = P.data.color_attributes["説明"]
for o in bones:
    if o.type == 'MESH':
        at = o.data.color_attributes.get("説明") or o.data.color_attributes.new("説明", 'FLOAT_COLOR', 'POINT')
        at.data.foreach_set("color", np.tile(lin((0.8, 0.8, 0.78)), (len(o.data.vertices), 1)).astype(np.float32).ravel()); o.data.color_attributes.active_color = at
shoot("pma_front", 0, 0.36); shoot("pma_34", -35, 0.38)
