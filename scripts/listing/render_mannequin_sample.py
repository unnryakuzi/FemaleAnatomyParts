# -*- coding: utf-8 -*-
"""マネキン調サンプル（男性・生殖器除外）。認識合わせ用に2枚だけ撮る。"""
import bpy, os, math
from mathutils import Vector, Quaternion

OUT = os.environ.get("MQ_OUT")
os.makedirs(OUT, exist_ok=True)

print("COLLECTIONS:", [c.name for c in bpy.data.collections])

SHOW = {"骨格", "表層筋", "深層筋", "歯", "靱帯・腱"}
HIDE_ALWAYS = {"生殖器"}          # 全年齢版で除外する対象

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'

sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'SINGLE'                 # 頂点カラー(肌色)を使わない ← 肝
sh.single_color = (0.16, 0.16, 0.17)     # 黒〜濃灰のマット
sh.show_shadows = True
sh.shadow_intensity = 0.4
sh.show_cavity = True                    # 凹凸を出さないと筋の構造が消える
sh.cavity_type = 'BOTH'
sh.curvature_ridge_factor = 1.2
sh.curvature_valley_factor = 1.2
sh.show_object_outline = False
sh.background_type = 'VIEWPORT'
sh.background_color = (0.72, 0.72, 0.72)

RES_X, RES_Y = 1000, 1400
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 100

hidden_genital = []
show_objs = set()
for c in bpy.data.collections:
    if c.name in HIDE_ALWAYS:
        for o in c.all_objects:
            if o.type == 'MESH':
                hidden_genital.append(o.name)
        continue
    if c.name in SHOW:
        for o in c.all_objects:
            if o.type == 'MESH':
                show_objs.add(o.name)

show_objs -= set(hidden_genital)
for o in scene.objects:
    o.hide_render = o.name not in show_objs

print("HIDDEN_GENITAL:", len(hidden_genital), hidden_genital[:15])
print("VISIBLE:", len(show_objs))

mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for n in show_objs:
    o = scene.objects[n]
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
print("BBOX", [round(v, 3) for v in mn], [round(v, 3) for v in mx])

cam_data = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
QF = Quaternion((0.70710678, 0.70710678, 0.0, 0.0))


def shot(fname, center, w, h, quat):
    ortho = max(h, w * RES_Y / RES_X) * 1.15
    cam.data.type = 'ORTHO'
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.ortho_scale = ortho
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = quat
    fwd = quat @ Vector((0, 0, -1))
    dist = ortho * 4 + 5
    cam.location = center - fwd * dist
    cam.data.clip_start = 0.01
    cam.data.clip_end = dist * 2 + 50
    scene.render.filepath = os.path.join(OUT, fname)
    bpy.ops.render.render(write_still=True)
    print("SHOT", fname, "ortho=%.3f" % ortho)


c = (mn + mx) / 2
H = mx.z - mn.z
W = mx.x - mn.x
shot("mq_01_male_front.png", c, W, H, QF.copy())

groin_z = mn.z + H * 0.52
shot("mq_02_male_groin.png", Vector((c.x, c.y, groin_z)), 0.44, 0.36, QF.copy())
print("DONE")
