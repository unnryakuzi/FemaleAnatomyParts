# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 大胸筋の腹部だけ水色にして、体の外から見える範囲を撮る（.blend は保存しない）
#  ほかのパーツは商品と同じ頂点カラー。正面・前の下から・右横から。カメラは固定の座標（3ファイルで同じ視点）
# blender -b <blend> -P tpose_port_render_pma.py -- <出力フォルダ> <タグ>
import bpy, sys, os, math, numpy as np
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index("--") + 1:]; OUT, TAG = os.path.abspath(a[0]), a[1]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; vl = bpy.context.view_layer
base = lambda n: n.split("(")[0].split(".")[0]
SHOW = {"骨格", "女性外皮", "筋肉", "歯", "靱帯・腱"}
def colls_of(o):
    cs = set()
    def up(c):
        for p in bpy.data.collections:
            if c.name in p.children and p.name not in cs: cs.add(p.name); up(p)
    for c in o.users_collection: cs.add(c.name); up(c)
    return cs
for lc in vl.layer_collection.children: lc.exclude = False
lin = lambda c: [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c] + [1.0]
for o in sc.objects:
    cs = colls_of(o)
    o.hide_render = not (o.type == 'MESH' and cs & SHOW and not cs & {"_RenderSetup", "_ガイドライン", "_下着(検討用)"})
    for md in o.modifiers: md.show_render = md.type != 'DECIMATE'
    if o.type != 'MESH': continue
    if base(o.name) in ("右大胸筋腹部", "左大胸筋腹部"):
        at = o.data.color_attributes.get("強調") or o.data.color_attributes.new("強調", 'FLOAT_COLOR', 'POINT')
        at.data.foreach_set("color", np.tile(lin((0.2, 0.85, 1.0)), (len(o.data.vertices), 1)).astype(np.float32).ravel())
        o.data.color_attributes.active_color = at
    elif o.data.color_attributes.get("Col"): o.data.color_attributes.active_color = o.data.color_attributes["Col"]
sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "VERTEX"; sh.show_cavity = False
sc.world = sc.world or bpy.data.worlds.new("W"); sc.world.color = (0.72, 0.72, 0.72); sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
cam = bpy.data.objects.new("_pma_cam", bpy.data.cameras.new("_pma_cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.clip_start = 0.01; cam.data.clip_end = 20
def shoot(name, ctr, yaw, pitch, scale, res=(900, 800)):
    q = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(90 - pitch), 4, 'X')
    cam.matrix_world = Matrix.Translation(Vector(ctr)) @ q @ Matrix.Translation((0, 0, 3)); cam.data.ortho_scale = scale
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (name, TAG)); bpy.ops.render.render(write_still=True); print("SHOT", name, TAG, flush=True)
shoot("21_大胸筋の腹部_正面", (0, -0.02, 1.30), 0, 0, 0.55)
shoot("22_大胸筋の腹部_前の下から", (0, -0.02, 1.30), 0, -45, 0.55)
shoot("23_大胸筋の腹部_右横から", (-0.12, 0.02, 1.32), -90, 0, 0.50)
print("DONE", TAG)
