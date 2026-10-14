# v1.68.0 で編集した所を色分けした確認用 .blend を別名で保存する（マスターは保存しない）
#  頂点カラー「編集箇所」を全メッシュに作り、ビューポートをその色で表示する
#    赤   = Tポーズ版から足した37個 / 青 = Man_All から足した腕の6個 / 黄 = 多裂筋（位置を修正）
#    緑   = 腹壁の深い4層で、下端を移し直した頂点 / 紫 = 踵骨腱（骨格 → 靱帯・腱 へ移しただけ）/ 灰 = 変更なし
# blender -b 3DAnatomyFemale.blend -P make_review_blend.py -- <added.json> <腹壁修正前の work/wb dir> <保存先 .blend>
import bpy, sys, json, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; ADDED, WB, OUT = a
added = set(json.load(open(ADDED, encoding="utf-8")))
ARM = ("右前腕骨間膜", "左前腕骨間膜", "右手の虫様筋", "左手の虫様筋", "右掌側骨間筋", "左掌側骨間筋")
fj = json.load(open(WB + "/female.json", encoding="utf-8")); F = np.load(WB + "/female.npz")
C = dict(red=(0.85, 0.08, 0.05, 1), blue=(0.1, 0.35, 0.95, 1), yellow=(1.0, 0.85, 0.0, 1), green=(0.1, 0.8, 0.2, 1),
         purple=(0.6, 0.2, 0.85, 1), grey=(0.62, 0.62, 0.62, 1))
srgb2lin = lambda c: tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) if i < 3 else x for i, x in enumerate(c))
cnt = {}
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    me = o.data; n = len(me.vertices); base = o.name.split("(")[0]
    col = np.tile(srgb2lin(C["grey"]), (n, 1))
    if o.name in added:
        col[:] = srgb2lin(C["blue"] if base in ARM else C["red"]); key = "blue" if base in ARM else "red"
        if base in fj["full"]:   # 腹壁の深い4層: 修正前と比べて動いた頂点を緑に
            pre = F["w_%d" % fj["full"][base]].astype(np.float64)
            co = np.empty(n * 3); me.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
            w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
            mv = np.linalg.norm(w - pre, axis=1) > 1e-4
            col[mv] = srgb2lin(C["green"]); cnt["green(頂点)"] = cnt.get("green(頂点)", 0) + int(mv.sum())
    elif base in ("右多裂筋", "左多裂筋"):
        col[:] = srgb2lin(C["yellow"]); key = "yellow"
    elif "踵骨腱" in base:
        col[:] = srgb2lin(C["purple"]); key = "purple"
    else:
        key = "grey"
    cnt[key] = cnt.get(key, 0) + 1
    at = me.color_attributes.get("編集箇所") or me.color_attributes.new("編集箇所", 'FLOAT_COLOR', 'POINT')
    at.data.foreach_set("color", col.astype(np.float32).ravel())
    me.color_attributes.active_color = at
    me.color_attributes.render_color_index = me.color_attributes.find("編集箇所")
print("色分け", cnt)
# 検討用の下着とガイド線は隠す
for o in bpy.data.objects:
    if o.name.startswith(("Swimwear_", "CURRENT_", "DIAG_")) and o.name in bpy.context.view_layer.objects:
        o.hide_set(True)
for sc in bpy.data.screens:
    for ar in sc.areas:
        for sp in ar.spaces:
            if sp.type == 'VIEW_3D':
                sp.shading.type = 'SOLID'; sp.shading.color_type = 'VERTEX'; sp.overlay.show_overlays = True
bpy.context.scene.display.shading.color_type = 'VERTEX'
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, compress=True)
print("SAVED", OUT)
