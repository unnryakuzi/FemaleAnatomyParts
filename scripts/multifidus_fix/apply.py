# transfer.py / transfer_parts.py の結果（ワールド座標）を女性マスターの同名パーツの頂点に書き込む。頂点数・並びは同じなので頂点カラー等はそのまま
# blender -b 3DAnatomyFemale.blend -P apply.py -- <multifidus_new_*.npz> <保存先 .blend（マスターと同じパスなら上書き保存）>
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; NPZ, OUT = a
X = np.load(NPZ)
for k in X.files:   # npz のキー＝パーツの base 名（多裂筋・錐体筋など）
    o = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.split("(")[0] == k)
    w = X[k].astype(np.float64); assert len(w) == len(o.data.vertices), (k, len(w), len(o.data.vertices))
    Mi = np.array(o.matrix_world.inverted(), np.float64)
    loc = w @ Mi[:3, :3].T + Mi[:3, 3]
    o.data.vertices.foreach_set("co", loc.astype(np.float32).ravel()); o.data.update()
    print("SET", o.name, len(w))
if bpy.path.abspath(OUT) == bpy.data.filepath:
    bpy.ops.wm.save_mainfile()
else:
    bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print("SAVED", OUT)
