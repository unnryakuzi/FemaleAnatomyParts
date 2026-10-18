# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: マスター・移植前・移植後を同じカメラで撮る（.blend は保存しない）
#  胴体の正面・背面（見た目＝頂点カラー）、首の後ろ（表の筋を隠した深い層）、腹の拡大（見た目と、外腹斜筋を隠した層）、
#  肋骨のかご（骨だけ）、右の腕の付け根（Tポーズの形で前斜め・下から・後ろ斜め）
#  カメラは固定の座標（腕以外は3ファイルで同じ位置にあるので、同じ視点になる）。Decimate は外して元の形で撮る
#  手のひら（表の筋を隠す）と前腕（骨と前腕骨間膜だけ）は、ポーズ（A=マスター / T=Tポーズ版）ごとの座標で撮る
# blender -b <blend> -P tpose_port_render.py -- <出力フォルダ> <タグ> <A|T>
import bpy, sys, os, math
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index("--") + 1:]; OUT, TAG, POSE = os.path.abspath(a[0]), a[1], a[2]; os.makedirs(OUT, exist_ok=True)   # 相対パスのままだと Blender は C:\ 直下に書く
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
CS = {o: colls_of(o) for o in sc.objects}
LOOK = {o for o in sc.objects if o.type == 'MESH' and CS[o] & SHOW and not CS[o] & {"_RenderSetup", "_ガイドライン", "_下着(検討用)"}}
BONES = {o for o in LOOK if "骨格" in CS[o]} | {o for o in LOOK if "歯" in CS[o]}
for o in sc.objects:
    for md in o.modifiers: md.show_render = md.type != 'DECIMATE'
    if o.type == 'MESH' and o.data.color_attributes.get("Col"): o.data.color_attributes.active_color = o.data.color_attributes["Col"]
for lc in vl.layer_collection.children: lc.exclude = False
sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "VERTEX"; sh.show_cavity = False
sc.world = sc.world or bpy.data.worlds.new("W"); sc.world.color = (0.72, 0.72, 0.72); sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
cam = bpy.data.objects.new("_tp_cam", bpy.data.cameras.new("_tp_cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.clip_start = 0.01; cam.data.clip_end = 20
def show(objs):
    for o in sc.objects: o.hide_render = o not in objs
def hide_names(objs, words): return {o for o in objs if not any(w in base(o.name) for w in words)}
def shoot(name, ctr, yaw, pitch, scale, res=(800, 900)):
    # yaw 0 = 正面（-Y から +Y を見る）、180 = 背面、負 = モデルの右（-X）側。pitch 正 = 上から、負 = 下から
    q = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(90 - pitch), 4, 'X')
    cam.matrix_world = Matrix.Translation(Vector(ctr)) @ q @ Matrix.Translation((0, 0, 3)); cam.data.ortho_scale = scale
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (name, TAG)); bpy.ops.render.render(write_still=True); print("SHOT", name, TAG, flush=True)
SURF_BACK = ("僧帽筋", "頭板状筋", "頚板状筋", "胸鎖乳突筋", "広背筋", "三角筋", "広頚筋")
show(LOOK)
shoot("01_正面", (0, 0, 1.22), 0, 0, 0.95)
shoot("02_背面", (0, 0, 1.22), 180, 0, 0.95)
shoot("05_腹_見た目", (0, -0.05, 1.12), 0, 0, 0.55)
shoot("07_腋_前斜め", (-0.15, 0.0, 1.38), -35, 0, 0.42, (900, 800))
shoot("08_腋_下から", (-0.15, 0.02, 1.38), -20, -45, 0.42, (900, 800))
shoot("09_腋_後ろ斜め", (-0.15, 0.03, 1.38), -145, 0, 0.42, (900, 800))
show(hide_names(LOOK - {o for o in LOOK if "女性外皮" in CS[o]}, SURF_BACK))
shoot("03_首の後ろ_深い層", (0, 0.10, 1.52), 180, 0, 0.36)
shoot("04_背中_深い層", (0, 0.06, 1.25), 180, 0, 0.80)
show(hide_names(LOOK - {o for o in LOOK if "女性外皮" in CS[o]}, ("外腹斜筋", "白線")))
shoot("06_腹_外腹斜筋を隠す", (0, -0.05, 1.12), 0, 0, 0.55)
show(BONES)
shoot("10_肋骨のかご", (0, 0, 1.28), 0, 0, 0.70)
# 右の手のひら（手の虫様筋・掌側骨間筋が見えるよう、浅い屈筋・手掌の表の筋を隠す）と、右の前腕（骨と前腕骨間膜だけ）
PALM_SURF = ("浅指屈筋", "長掌筋", "短掌筋", "手掌腱膜", "短母指外転筋", "短母指屈筋", "母指対立筋", "小指外転筋", "短小指屈筋", "小指対立筋", "母指内転筋", "屈筋支帯")
VIEW = {"A": dict(palm=((-0.242, 0.0, 0.81), 38, -10, 0.17), fa1=((-0.221, 0.036, 0.99), 0, 0, 0.32), fa2=((-0.221, 0.036, 0.99), -90, 0, 0.32)),
        "T": dict(palm=((-0.80, -0.008, 1.432), -153, -50, 0.17), fa1=((-0.63, 0.035, 1.46), 0, -89, 0.32), fa2=((-0.63, 0.035, 1.46), 0, 0, 0.32))}[POSE]
show(hide_names(LOOK - {o for o in LOOK if "女性外皮" in CS[o]}, PALM_SURF))
shoot("11_右手のひら_深い層", *VIEW["palm"], (900, 800))
show(BONES | {o for o in LOOK if "前腕骨間膜" in o.name})
shoot("12_右前腕_骨と骨間膜_1", *VIEW["fa1"], (900, 800))
shoot("13_右前腕_骨と骨間膜_2", *VIEW["fa2"], (900, 800))
print("DONE", TAG)
