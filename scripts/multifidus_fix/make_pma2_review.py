# 大胸筋の腹部・案2 の確認用 .blend を別名で保存する（マスターは保存しない）
#  入力は案2を当てた試作（trial_pma_d.blend）。大胸筋の腹部を、ほかの筋・骨・腱の中に 1mm 以上入っている頂点＝赤、それ以外＝水色に塗る（頂点カラー「埋まり」）
#  埋めている相手の筋（前鋸筋・外腹斜筋・腹直筋・烏口腕筋）を「まわりの筋」コレクションへ移し、目のアイコン1つで隠せるようにする
#  案1 の大胸筋の腹部（名前_案1、同じ塗り分け）を「大胸筋の腹部_案1(比較用)」へ（最初は隠す）
# blender -b trial_pma_d.blend -P make_pma2_review.py -- <案1 の npz> <保存先 .blend>
import bpy, sys, math, numpy as np
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; NPZ1, OUT = a
X1 = np.load(NPZ1)
sc = bpy.context.scene; vl = bpy.context.view_layer
base = lambda n: n.split("(")[0].split(".")[0]
PMA = ("右大胸筋腹部", "左大胸筋腹部"); NEIGH = ("前鋸筋", "外腹斜筋", "腹直筋", "烏口腕筋")
for lc in vl.layer_collection.children: lc.exclude = False
pma = [o for o in sc.objects if o.type == 'MESH' and base(o.name) in PMA]
copies = []
for o in pma:
    c = o.copy(); c.data = o.data.copy(); c.name = base(o.name) + "_案1"
    w = X1[base(o.name)].astype(np.float64); Mi = np.array(o.matrix_world.inverted())
    c.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); c.data.update(); copies.append(c)
col1 = bpy.data.collections.new("大胸筋の腹部_案1(比較用)"); sc.collection.children.link(col1)
for c in copies: col1.objects.link(c)
col2 = bpy.data.collections.new("大胸筋の腹部_案2"); sc.collection.children.link(col2)
for o in pma:
    for c in list(o.users_collection): c.objects.unlink(o)
    col2.objects.link(o)
coln = bpy.data.collections.new("まわりの筋（前鋸筋・外腹斜筋・腹直筋・烏口腕筋）"); sc.collection.children.link(coln)
neigh = [o for o in sc.objects if o.type == 'MESH' and base(o.name)[:1] in "右左" and base(o.name)[1:] in NEIGH]
for o in neigh:
    for c in list(o.users_collection): c.objects.unlink(o)
    coln.objects.link(o)
print("まわりの筋", [o.name.split("(")[0] for o in neigh])
vl.update(); dg = bpy.context.evaluated_depsgraph_get()
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格", coln.name)]
parts = sorted({o for c in USE for o in c.all_objects if o.type == 'MESH'}, key=lambda o: o.name)
for o in parts:
    if o.hide_viewport: o.hide_viewport = False
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
CY, RD = np.array(lin((0.25, 0.8, 1.0))), np.array(lin((0.95, 0.1, 0.1)))
trees = {}
skip = set(pma) | set(copies)
for P in pma + copies:
    W = wv(P); lo, hi = W.min(0) - 0.002, W.max(0) + 0.002; inside = np.zeros(len(W), bool); who = {}
    for Q in parts:
        if Q in skip: continue
        q = wv(Q)
        if np.any(q.min(0) > hi) or np.any(q.max(0) < lo): continue
        sel = np.where(np.all((W > q.min(0)) & (W < q.max(0)), 1))[0]
        if not len(sel): continue
        if Q not in trees: trees[Q] = (BVHTree.FromObject(Q, dg), np.array(Q.matrix_world.inverted()), np.array(Q.matrix_world.to_3x3()))
        T, Mi, M3 = trees[Q]; MiT = np.linalg.inv(M3).T; L = W[sel] @ Mi[:3, :3].T + Mi[:3, 3]
        for i, v in zip(sel, L):
            if inside[i]: continue
            loc, n, _, _ = T.find_nearest(Vector(v))
            if loc is None: continue
            dw = M3 @ (np.array(loc) - v); nw = MiT @ np.array(n); nn = np.linalg.norm(nw)
            if nn and float(dw @ nw) / nn > 0.001 and parity(T, v): inside[i] = True; who[base(Q.name)] = who.get(base(Q.name), 0) + 1
    col = np.where(inside[:, None], RD, CY)
    at = P.data.color_attributes.get("埋まり") or P.data.color_attributes.new("埋まり", 'FLOAT_COLOR', 'POINT')
    at.data.foreach_set("color", col.astype(np.float32).ravel()); P.data.color_attributes.active_color = at
    P.data.color_attributes.render_color_index = P.data.color_attributes.find("埋まり")
    print(P.name.split("(")[0], "埋まっている頂点 %.1f%%" % (inside.mean() * 100), sorted(who.items(), key=lambda x: -x[1])[:5])
for lc in vl.layer_collection.children:
    if lc.name == col1.name: lc.hide_viewport = True
for o in sc.objects:
    if o.name.startswith(("Swimwear_", "CURRENT_", "DIAG_")) and o.name in vl.objects: o.hide_set(True)
v34 = Quaternion((0, 0, 1), math.radians(-30)) @ Quaternion((1, 0, 0), math.radians(80))
for scr in bpy.data.screens:
    for ar in scr.areas:
        for sp in ar.spaces:
            if sp.type == 'VIEW_3D':
                sp.shading.type = 'SOLID'; sp.shading.color_type = 'VERTEX'; sp.overlay.show_overlays = True
                r3 = sp.region_3d; r3.view_perspective = 'ORTHO'; r3.view_rotation = v34; r3.view_location = Vector((0.0, -0.03, 1.30)); r3.view_distance = 0.55
sc.display.shading.color_type = 'VERTEX'
txt = bpy.data.texts.get("凡例_案2") or bpy.data.texts.new("凡例_案2")
txt.clear(); txt.write("""大胸筋の腹部・案2（下の肋軟骨と同じだけ外へ動かす。見た目は今のまま）の確認用（マスターは変更していない）
大胸筋の腹部の色（頂点カラー「埋まり」）: 赤＝ほかの筋・骨の中に 1mm 以上めり込んでいる所 ／ 水色＝表に出ている所
それ以外は商品と同じ色。肋骨のかご・腹壁の深い層は試作の形
アウトライナー
  「まわりの筋（前鋸筋・外腹斜筋・腹直筋・烏口腕筋）」 目のアイコンを消すと、大胸筋の腹部の赤い所（この筋の中に埋まっている所）が見える
  「大胸筋の腹部_案2」 案2 の大胸筋の腹部
  「大胸筋の腹部_案1(比較用)」 案1 の大胸筋の腹部（同じ塗り分け）。案2 の目を消してこちらを入れると見比べられる
  乳房は「女性外皮」コレクションの目で隠せる
""")
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, compress=True)
print("SAVED", OUT)
