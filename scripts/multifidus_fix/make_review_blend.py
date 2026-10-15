# v1.68.0 で編集した所を色分けした確認用 .blend を別名で保存する（マスターは保存しない）
#  頂点カラー「編集箇所」を全メッシュに作り、ビューポートをその色で表示する
#    赤 = 首・背中の27個（男性版の形のまま、付着する骨と同じ変換で置き直した）
#    橙 = 腹壁の深い4層（Tポーズ版から）／緑 = そのうち恥骨の上で作り直した頂点／黄緑 = 腹横筋を肋骨のかごの内側へ戻した頂点
#    水色 = 下腿骨間膜（Tポーズ版から）／青 = Man_All から足した腕の6個
#    黄 = 多裂筋（首の部分だけ位置を修正）／紫 = 踵骨腱（骨格 → 靱帯・腱 へ移しただけ）／灰 = 変更なし
# blender -b 3DAnatomyFemale.blend -P make_review_blend.py -- <added.json> <腹壁修正前の work/wb dir> <保存先 .blend> [腹横筋の肋骨修正前の work/after2 dir]
import bpy, sys, json, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; ADDED, WB, OUT = a[:3]; WR = a[3] if len(a) > 3 else None
added = set(json.load(open(ADDED, encoding="utf-8")))
ARM = ("右前腕骨間膜", "左前腕骨間膜", "右手の虫様筋", "左手の虫様筋", "右掌側骨間筋", "左掌側骨間筋")
ABD = ("腹直筋", "内腹斜筋", "腹横筋", "錐体筋")
fj = json.load(open(WB + "/female.json", encoding="utf-8")); F = np.load(WB + "/female.npz")
rj, R = (json.load(open(WR + "/female.json", encoding="utf-8")), np.load(WR + "/female.npz")) if WR else (None, None)
C = dict(red=(0.85, 0.08, 0.05, 1), pink=(1.0, 0.35, 0.7, 1), orange=(1.0, 0.55, 0.1, 1), green=(0.1, 0.8, 0.2, 1), lime=(0.65, 0.95, 0.1, 1),
         cyan=(0.2, 0.75, 0.9, 1), blue=(0.1, 0.3, 0.95, 1), yellow=(1.0, 0.85, 0.0, 1), purple=(0.6, 0.2, 0.85, 1), grey=(0.62, 0.62, 0.62, 1))
Z_PUBIS = 1.03   # 恥骨の上の作り直しは z<=1.025m（blend_lower.py の z1）。それより上の動きは緑にしない
LEGEND = """v1.68.0 で編集したパーツ（頂点カラー「編集箇所」で色分け。ビューポートはソリッド表示・カラー＝頂点）
開いたときは変更していない筋を隠してある（骨と歯は表示）。ビューポートで Alt+H を押すと全部表示に戻る
赤   首・背中の25個: 男性版の形のまま、付着する骨と同じ変換で置き直した（頭半棘筋・頚半棘筋・頚回旋筋・頚最長筋・大小後頭直筋・横突間筋・棘間筋・大小菱形筋・肩甲挙筋・鎖骨下筋・胸腸肋筋）
桃   下後鋸筋（左右）: 上と同じ置き方のうえで、広背筋と脊柱起立筋のすき間に合わせて薄くした
橙   腹壁の深い4層（腹直筋・内腹斜筋・腹横筋・錐体筋）: Tポーズ版から（腹横筋は上の部分を肋骨のかごの内側へ戻した）
緑   そのうち恥骨の上で作り直した頂点
黄緑 腹横筋の上の部分: 肋骨のかごの外側に出ていたのを内側へ戻した頂点
水色 下腿骨間膜: Tポーズ版から
青   Man_All から足した腕の6個（前腕骨間膜・手の虫様筋・掌側骨間筋）
黄   多裂筋: 販売中の元の形のまま、首の部分だけ下げて上端を第2頚椎の高さに
紫   踵骨腱: 骨格 → 靱帯・腱 へコレクションを移しただけ（形は不変）
灰   変更なし
"""
lin = lambda c: tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) if i < 3 else x for i, x in enumerate(c))
cnt = {}
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    me = o.data; n = len(me.vertices); b = o.name.split("(")[0]
    if o.name in added:
        key = "blue" if b in ARM else "orange" if any(x in b for x in ABD) else "cyan" if "下腿骨間膜" in b else "pink" if "下後鋸筋" in b else "red"
    elif b in ("右多裂筋", "左多裂筋"):
        key = "yellow"
    elif "踵骨腱" in b:
        key = "purple"
    else:
        key = "grey"
    col = np.tile(lin(C[key]), (n, 1))
    if key == "orange" and b in fj["full"]:
        co = np.empty(n * 3); me.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
        w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        if rj is not None and b in rj["full"]:   # 腹横筋: 肋骨のかごの内側へ戻した頂点を黄緑に（肋骨修正の前と比べる）
            pre_r = R["w_%d" % rj["full"][b]].astype(np.float64)
            mr = np.linalg.norm(w - pre_r, axis=1) > 1e-4
            col[mr] = lin(C["lime"]); cnt["lime(頂点)"] = cnt.get("lime(頂点)", 0) + int(mr.sum())
        pre = F["w_%d" % fj["full"][b]].astype(np.float64)   # 恥骨の上で作り直した頂点を緑に（腹壁修正の前と比べ、z で恥骨まわりに限る）
        base_pos = R["w_%d" % rj["full"][b]].astype(np.float64) if (rj is not None and b in rj["full"]) else w
        mv = (np.linalg.norm(base_pos - pre, axis=1) > 1e-4) & (pre[:, 2] <= Z_PUBIS)
        col[mv] = lin(C["green"]); cnt["green(頂点)"] = cnt.get("green(頂点)", 0) + int(mv.sum())
    cnt[key] = cnt.get(key, 0) + 1
    at = me.color_attributes.get("編集箇所") or me.color_attributes.new("編集箇所", 'FLOAT_COLOR', 'POINT')
    at.data.foreach_set("color", col.astype(np.float32).ravel())
    me.color_attributes.active_color = at
    me.color_attributes.render_color_index = me.color_attributes.find("編集箇所")
print("色分け", cnt)
for o in bpy.data.objects:
    if o.name.startswith(("Swimwear_", "CURRENT_", "DIAG_")) and o.name in bpy.context.view_layer.objects:
        o.hide_set(True)
# 編集したパーツが見えるように、変更していない筋・腱・皮膚（灰）を目のアイコンで隠す。骨と歯は位置の目安に残す（Alt+H で全部戻る）
BONES = {o for c in bpy.data.collections if c.name in ("骨格", "歯") for o in c.all_objects}
grey_hidden = 0
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name not in bpy.context.view_layer.objects or o in BONES:
        continue
    at = o.data.color_attributes.get("編集箇所")
    if at is None:
        continue
    c0 = at.data[0].color
    if abs(c0[0] - c0[1]) < 1e-4 and abs(c0[1] - c0[2]) < 1e-4 and "踵骨腱" not in o.name:   # 灰＝変更なし
        o.hide_viewport = False; o.hide_set(True); grey_hidden += 1
    else:
        o.hide_viewport = False; o.hide_set(False)
print("変更なしで隠したパーツ", grey_hidden)
from mathutils import Quaternion, Vector
import math
back34 = Quaternion((0, 0, 1), math.radians(35)) @ Quaternion((0.0, 0.0, 0.70710678, 0.70710678))   # 背面から右へ35°
for sc in bpy.data.screens:
    for ar in sc.areas:
        for sp in ar.spaces:
            if sp.type == 'VIEW_3D':
                sp.shading.type = 'SOLID'; sp.shading.color_type = 'VERTEX'; sp.overlay.show_overlays = True
                r3 = sp.region_3d
                r3.view_perspective = 'ORTHO'; r3.view_rotation = back34; r3.view_location = Vector((0.0, 0.07, 1.25)); r3.view_distance = 1.3
bpy.context.scene.display.shading.color_type = 'VERTEX'
txt = bpy.data.texts.get("凡例_今回の編集") or bpy.data.texts.new("凡例_今回の編集")
txt.clear(); txt.write(LEGEND)
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, compress=True)
print("SAVED", OUT)
