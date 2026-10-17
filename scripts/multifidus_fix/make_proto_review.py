# 試作（肋骨のかごの広げ直し・腹壁の深い層の作り直し）の確認用 .blend を別名で保存する（マスターは保存しない）
#  動かしたパーツを「肋骨と腹壁_新版(試作)」コレクションへ移し、今の形の複製（名前_旧）を「肋骨と腹壁_旧版(比較用)」へ（目のアイコンで切替）。
#  大胸筋の腹部のもう一つの案（肋軟骨と同じだけ動かす＝見た目は今のまま）の複製（名前_案2）を「大胸筋の腹部_案2(比較用)」へ。
#  頂点カラー「変更量」: 灰=動いていない → 黄=3mm → 赤=15mm 以上、緑=男性の形から作り直した腹壁の4層、水色=今の形、紫=案2
# blender -b 3DAnatomyFemale.blend -P make_proto_review.py -- <候補 npz> <案2 の npz> <保存先 .blend>
import bpy, sys, numpy as np, math
from mathutils import Quaternion, Vector
a = sys.argv[sys.argv.index("--") + 1:]; CAND, CAND_D, OUT = a[:3]
X = np.load(CAND); XD = np.load(CAND_D)
ABD = ("腹直筋", "内腹斜筋", "腹横筋", "錐体筋"); PMA = ("右大胸筋腹部", "左大胸筋腹部")
lin = lambda c: np.array([(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c[:3]] + [1.0])
GREY, YEL, RED, GREEN, CYAN, PURPLE = (lin(c) for c in ((0.62, 0.62, 0.62), (1.0, 0.85, 0.0), (0.85, 0.08, 0.05), (0.1, 0.8, 0.2), (0.45, 0.75, 1.0), (0.6, 0.25, 0.85)))
def heat(mm):
    t1 = np.clip(mm / 3.0, 0, 1)[:, None]; t2 = np.clip((mm - 3.0) / 12.0, 0, 1)[:, None]
    c = GREY * (1 - t1) + YEL * t1; return c * (1 - t2) + RED * t2
def setcol(o, col):
    me = o.data; at = me.color_attributes.get("変更量") or me.color_attributes.new("変更量", 'FLOAT_COLOR', 'POINT')
    at.data.foreach_set("color", col.astype(np.float32).ravel()); me.color_attributes.active_color = at
    me.color_attributes.render_color_index = me.color_attributes.find("変更量")
def world(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world); return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
def setworld(o, w):
    Mi = np.array(o.matrix_world.inverted()); o.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
sc = bpy.context.scene
cols = {}
for nm in ("肋骨と腹壁_新版(試作)", "肋骨と腹壁_旧版(比較用)", "大胸筋の腹部_案2(比較用)"):
    c = bpy.data.collections.new(nm); sc.collection.children.link(c); cols[nm] = c
NEW, OLD, ALT = cols.values()
moved = set()
for k in X.files:
    o = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.split("(")[0] == k)
    w0 = world(o); w1 = X[k].astype(np.float64)
    old = o.copy(); old.data = o.data.copy(); old.name = k + "_旧"; OLD.objects.link(old); setcol(old, np.tile(CYAN, (len(w0), 1)))
    setworld(o, w1)
    for c in list(o.users_collection): c.objects.unlink(o)
    NEW.objects.link(o); moved.add(o)
    setcol(o, np.tile(GREEN, (len(w0), 1)) if any(t in k for t in ABD) else heat(np.linalg.norm(w1 - w0, axis=1) * 1000))
    if k in PMA and k in XD.files:
        d = o.copy(); d.data = o.data.copy(); d.name = k + "_案2"; ALT.objects.link(d); setworld(d, XD[k].astype(np.float64)); setcol(d, np.tile(PURPLE, (len(w0), 1)))
print("動かしたパーツ", len(moved))
BONES = {o for c in bpy.data.collections if c.name in ("骨格", "歯") for o in c.all_objects}
special = moved | set(OLD.objects) | set(ALT.objects)
hidden = 0
for o in bpy.data.objects:
    if o.type != 'MESH' or o in special: continue
    setcol(o, np.tile(GREY, (len(o.data.vertices), 1)))
    if o.name in bpy.context.view_layer.objects and o not in BONES:
        o.hide_viewport = False; o.hide_set(True); hidden += 1
for o in bpy.data.objects:
    if o.name.startswith(("Swimwear_", "CURRENT_", "DIAG_")) and o.name in bpy.context.view_layer.objects: o.hide_set(True)
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name in (OLD.name, ALT.name): lc.hide_viewport = True                      # 目のアイコンで切替（collection.hide_viewport は触らない）
print("変更なしで隠した筋", hidden)
front34 = Quaternion((0, 0, 1), math.radians(-35)) @ Quaternion((0.70710678, 0.70710678, 0, 0))
for scr in bpy.data.screens:
    for ar in scr.areas:
        for sp in ar.spaces:
            if sp.type == 'VIEW_3D':
                sp.shading.type = 'SOLID'; sp.shading.color_type = 'VERTEX'; sp.overlay.show_overlays = True
                r3 = sp.region_3d; r3.view_perspective = 'ORTHO'; r3.view_rotation = front34; r3.view_location = Vector((0.0, 0.0, 1.22)); r3.view_distance = 1.2
sc.display.shading.color_type = 'VERTEX'
txt = bpy.data.texts.get("凡例_試作") or bpy.data.texts.new("凡例_試作")
txt.clear(); txt.write("""試作: 肋骨のかごを外側の筋に合わせて広げ、腹壁の深い層を男性の形から作り直した（マスターは変更していない）
色（頂点カラー「変更量」。ビューポートはソリッド表示・カラー＝頂点）
  灰=動かしていない ／ 黄=約3mm ／ 赤=15mm 以上 動かした（肋骨・肋軟骨・胸骨・肋間筋・小胸筋・胸横筋・大胸筋の腹部ほか）
  緑=腹壁の深い4層（内腹斜筋・腹横筋・腹直筋・錐体筋）: 男性の形から作り直した
  水色=今の形（比較用）／ 紫=大胸筋の腹部の案2（肋軟骨と同じだけ動かす。見た目は今のまま）
アウトライナー
  「肋骨と腹壁_新版(試作)」 試作の形（動かしたパーツはここへ移してある）
  「肋骨と腹壁_旧版(比較用)」 今の形。目のアイコンで表示し、新版の目を消すと見比べられる
  「大胸筋の腹部_案2(比較用)」 大胸筋の腹部のもう一つの案
変更していない筋は隠してある（ビューポートで Alt+H を押すと全部表示）
""")
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, compress=True)
print("SAVED", OUT)
