# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 焼いた色（bake_color.py の PNG）を体（female_uv4k.blend の Body）に貼って撮る（.blend は保存しない）
#  パーツを変えたときに、商品の見た目（体の表面の色）がどこで変わるかを見る用。水着は外して撮る（水着の下も見る）
# blender -b female_uv4k.blend -P tpose_port_body_render.py -- <出力フォルダ> <タグ> <色の PNG>
import bpy, sys, os, math
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index("--") + 1:]; OUT, TAG, PNG = os.path.abspath(a[0]), a[1], os.path.abspath(a[2]); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; body = bpy.data.objects["Body"]
img = bpy.data.images.load(PNG); img.alpha_mode = "NONE"
m = bpy.data.materials.new("_tex"); m.use_nodes = True; nt = m.node_tree
tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img; tn.interpolation = "Closest"
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"); nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"]); nt.nodes.active = tn
body.data.materials.clear(); body.data.materials.append(m)
for o in sc.objects: o.hide_render = not (o.name == "Body" or o.name.endswith("眼球"))
sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "FLAT"; sh.color_type = "TEXTURE"; sh.show_cavity = False
sc.world = sc.world or bpy.data.worlds.new("W"); sc.world.color = (0.72, 0.72, 0.72); sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
cam = bpy.data.objects.new("_bc", bpy.data.cameras.new("_bc")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = "ORTHO"; cam.data.clip_end = 20
def shoot(name, ctr, yaw, pitch, scale, res=(900, 900)):
    q = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(90 - pitch), 4, 'X')
    cam.matrix_world = Matrix.Translation(Vector(ctr)) @ q @ Matrix.Translation((0, 0, 3)); cam.data.ortho_scale = scale
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (name, TAG)); bpy.ops.render.render(write_still=True); print("SHOT", name, TAG, flush=True)
shoot("41_体_胸と腹_正面", (0, -0.05, 1.15), 0, 0, 0.62)
shoot("42_体_下腹部_前の下から", (0, -0.05, 1.00), 0, -35, 0.45)
shoot("43_体_右横", (-0.05, 0.0, 1.15), -90, 0, 0.62)
shoot("44_体_左前斜め", (0.05, -0.04, 1.10), 45, 0, 0.55)
print("DONE", TAG)
