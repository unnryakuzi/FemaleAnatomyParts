# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 指定したパーツだけ水色にして、体の外から見える範囲を撮る（.blend は保存しない）
#  ほかのパーツは商品と同じ頂点カラー。カメラは固定の座標（腕以外は各ファイルで同じ位置なので同じ視点になる）
# blender -b <blend> -P tpose_port_render_hl.py -- <出力フォルダ> <タグ> <パーツ名の一部（カンマ区切り）> <視点セット: abd>
import bpy, sys, os, math, numpy as np
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index("--") + 1:]; OUT, TAG, KEYS, VIEWS = os.path.abspath(a[0]), a[1], a[2].split(","), a[3]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; vl = bpy.context.view_layer
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
    if any(k in o.name for k in KEYS):
        at = o.data.color_attributes.get("強調") or o.data.color_attributes.new("強調", 'FLOAT_COLOR', 'POINT')
        at.data.foreach_set("color", np.tile(lin((0.2, 0.85, 1.0)), (len(o.data.vertices), 1)).astype(np.float32).ravel())
        o.data.color_attributes.active_color = at
    elif o.data.color_attributes.get("Col"): o.data.color_attributes.active_color = o.data.color_attributes["Col"]
sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "VERTEX"; sh.show_cavity = False
sc.world = sc.world or bpy.data.worlds.new("W"); sc.world.color = (0.72, 0.72, 0.72); sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
cam = bpy.data.objects.new("_hl_cam", bpy.data.cameras.new("_hl_cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.clip_start = 0.01; cam.data.clip_end = 20
def shoot(name, ctr, yaw, pitch, scale, res=(900, 800)):
    q = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(90 - pitch), 4, 'X')
    cam.matrix_world = Matrix.Translation(Vector(ctr)) @ q @ Matrix.Translation((0, 0, 3)); cam.data.ortho_scale = scale
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (name, TAG)); bpy.ops.render.render(write_still=True); print("SHOT", name, TAG, flush=True)
if VIEWS == "abd":
    shoot("31_腹_正面", (0, -0.05, 1.02), 0, 0, 0.50)
    shoot("32_腹_前の下から", (0, -0.05, 1.00), 0, -35, 0.50)
    shoot("33_腹_右前斜め", (-0.05, -0.04, 1.00), -45, 0, 0.50)
print("DONE", TAG)
