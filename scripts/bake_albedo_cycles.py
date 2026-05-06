"""
Cyclesベイクスクリプト — Blenderのテキストエディタから実行
Blender 5.0対応: 3Dビューポートのコンテキストオーバーライドを使用
"""
import bpy

OBJ_NAME  = 'LOD_Body'
MAT_NAME  = 'Muscle_Fiber_PoseManiacs'
UV_NAME   = 'UV_Bake'
IMG_NAME  = 'LOD_Baked_Albedo'
IMG_RES   = 1024
SAVE_PATH = r'C:\Users\abesh\Documents\Blender\MaleAnatomy\Result\LOD_Baked_Albedo.png'
SAMPLES   = 32

# ── オブジェクト準備 ──
obj = bpy.data.objects.get(OBJ_NAME)
assert obj, f"'{OBJ_NAME}' not found"

bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
obj.data.uv_layers.active = obj.data.uv_layers[UV_NAME]

# ── ベイクターゲット画像 ──
if IMG_NAME in bpy.data.images:
    bpy.data.images.remove(bpy.data.images[IMG_NAME])
bake_img = bpy.data.images.new(IMG_NAME, IMG_RES, IMG_RES, alpha=False)
bake_img.colorspace_settings.name = 'sRGB'

# ── マテリアルにベイクターゲットノードを設定 ──
mat   = bpy.data.materials[MAT_NAME]
nodes = mat.node_tree.nodes

node = nodes.get('BAKE_ALBEDO_TARGET')
if not node:
    node = nodes.new('ShaderNodeTexImage')
    node.name     = 'BAKE_ALBEDO_TARGET'
    node.location = (400, -500)
node.image = bake_img

for n in nodes: n.select = False
node.select = True
nodes.active = node

# ── Cycles 設定 ──
scene = bpy.context.scene
scene.render.engine                 = 'CYCLES'
scene.cycles.samples                = SAMPLES
scene.cycles.device                 = 'CPU'
scene.render.bake.use_pass_direct   = False
scene.render.bake.use_pass_indirect = False
scene.render.bake.use_pass_color    = True
scene.render.bake.margin            = 16

# ── 3Dビューポートのコンテキストを取得してベイク ──
view3d_area   = None
view3d_region = None

for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    view3d_area   = area
                    view3d_region = region
                    found_window  = window
                    break

if view3d_area is None:
    raise RuntimeError("3D Viewport not found. Please open a 3D Viewport panel.")

print("Baking Diffuse Color... please wait")

with bpy.context.temp_override(
    window=found_window,
    screen=found_window.screen,
    area=view3d_area,
    region=view3d_region,
    scene=scene,
    view_layer=bpy.context.view_layer,
    active_object=obj,
):
    bpy.ops.object.bake(type='DIFFUSE')

print("Bake complete!")

# ── 保存 ──
bake_img.filepath_raw = SAVE_PATH
bake_img.file_format  = 'PNG'
bake_img.save()
print(f"Saved: {SAVE_PATH}")

scene.render.engine = 'BLENDER_EEVEE'
print("Done.")
