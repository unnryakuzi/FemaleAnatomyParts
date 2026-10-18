# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 指定したパーツを、別の .blend（前の Tポーズ版）の頂点・色に戻す
#  ユーザー基準（10-18）「Tポーズ版は、前の Tポーズと表層の筋が合っていればよい」。表層の筋（例: 大胸筋の腹部）は前の形に戻す
#  take: 戻し元の .blend で、パーツのローカル頂点・行列・頂点カラーを npz に書く（.blend は保存しない）
#  put : 戻し先の .blend で、行列・面のつながりが同じことを確かめてから書き込み、保存する
# blender -b <戻し元 .blend> -P tpose_port_restore.py -- take <パーツ名（base, カンマ区切り）> <npz>
# blender -b <戻し先 .blend> -P tpose_port_restore.py -- put  <npz> <保存先 .blend（戻し先と同じなら INPLACE=1）>
import bpy, sys, os, hashlib, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; MODE = a[0]
def h(x): return hashlib.md5(np.ascontiguousarray(x).tobytes()).hexdigest()[:16]
base = lambda n: n.split("(")[0]
if MODE == "take":
    names = set(a[1].split(",")); out = {}
    for o in (o for o in bpy.data.objects if o.type == 'MESH' and base(o.name) in names):
        me = o.data; co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
        out["co__" + o.name] = co.reshape(-1, 3); out["M__" + o.name] = np.array(o.matrix_world, np.float64)
        out["topo__" + o.name] = np.frombuffer(h(lv).encode(), np.uint8)
        for at in me.color_attributes:
            buf = np.empty(len(at.data) * 4, np.float32); at.data.foreach_get("color", buf); out["col__%s__%s" % (o.name, at.name)] = buf.reshape(-1, 4)
    assert {base(k[4:]) for k in out if k.startswith("co__")} == names, "見つからないパーツがある"
    np.savez(a[2], **out); print("TAKEN", sorted(names))
else:
    X = np.load(a[1]); OUT = os.path.abspath(a[2])
    if os.path.normcase(OUT) == os.path.normcase(os.path.abspath(bpy.data.filepath)): assert os.environ.get("INPLACE") == "1", "同じファイルに保存するなら INPLACE=1"
    for k in (k for k in X.files if k.startswith("co__")):
        n = k[4:]; o = bpy.data.objects[n]; me = o.data; co = X[k]
        assert len(co) == len(me.vertices), n
        assert np.array_equal(np.array(o.matrix_world, np.float64), X["M__" + n]), ("行列が違う", n)
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv); assert h(lv) == bytes(X["topo__" + n]).decode(), ("面のつながりが違う", n)
        me.vertices.foreach_set("co", co.ravel())
        for c in (c for c in X.files if c.startswith("col__%s__" % n)):
            at = me.color_attributes[c.split("__")[2]]; at.data.foreach_set("color", X[c].ravel())
        me.update(); print("PUT", n)
    if os.path.normcase(OUT) == os.path.normcase(os.path.abspath(bpy.data.filepath)): bpy.ops.wm.save_mainfile()
    else: bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
    print("SAVED", OUT)
