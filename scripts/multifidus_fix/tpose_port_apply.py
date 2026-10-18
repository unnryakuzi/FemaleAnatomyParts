# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: tpose_port_take.py の npz を Tポーズ版に書き込み、別名で保存する（元のファイルは上書きしない）
#  頂点の並び・行列が同じことを1個ずつ確かめてから、頂点（ローカル座標）・色を写し、コレクションを移す（踵骨腱 骨格→靱帯・腱）
#  パーツのオブジェクト・メッシュ・材質・プロパティ（restored_from_male など）はTポーズ版のまま
# blender -b 3DAnatomyFemale_Tpose_final_20261014.blend -P tpose_port_apply.py -- <plan.json> <take npz> <保存先 .blend>
import bpy, sys, os, json, hashlib, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; PLAN = json.load(open(a[0], encoding="utf-8")); X = np.load(a[1]); OUT = os.path.abspath(a[2])
def h(x): return hashlib.md5(np.ascontiguousarray(x).tobytes()).hexdigest()[:16]
assert os.path.normcase(OUT) != os.path.normcase(os.path.abspath(bpy.data.filepath)), "元のファイルには保存しない"
assert not os.path.exists(OUT) or os.environ.get("FORCE") == "1", "保存先が既にある（上書きするなら FORCE=1）: " + OUT
for r in PLAN["move"]:
    n = r["n"]; o = bpy.data.objects[n]; me = o.data; co = X["co__" + n]
    assert len(me.vertices) == len(co), (n, len(me.vertices), len(co))
    assert np.array_equal(np.array(o.matrix_world, np.float64), X["M__" + n]), ("行列が違う", n)
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
    assert h(lv) == bytes(X["topo__" + n]).decode(), ("面のつながりが違う", n)
    assert not me.shape_keys and not o.modifiers and o.parent is None, ("シェイプキー・モディファイア・親は想定外", n)
    me.vertices.foreach_set("co", co.ravel()); me.update()
for r in PLAN["color"]:
    me = bpy.data.objects[r["n"]].data
    for k in r["attrs"]:
        at = me.color_attributes[k]; c = X["col__%s__%s" % (r["n"], k)]; assert len(at.data) == len(c), (r["n"], k)
        at.data.foreach_set("color", c.ravel())
    me.update()
for r in PLAN["colls"]:
    o = bpy.data.objects[r["n"]]
    for c in r["to"]:
        if o.name not in bpy.data.collections[c].objects: bpy.data.collections[c].objects.link(o)
    for c in r["frm"]:
        if c not in r["to"]: bpy.data.collections[c].objects.unlink(o)
print("APPLIED move=%d color=%d colls=%d" % (len(PLAN["move"]), len(PLAN["color"]), len(PLAN["colls"])))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
