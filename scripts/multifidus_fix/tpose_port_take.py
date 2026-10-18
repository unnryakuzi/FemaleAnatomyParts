# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: マスターから、plan の「移す」パーツの頂点（ローカル座標そのまま）と変わった色を取り出す。.blend は保存しない
#  行列はマスターと Tポーズ版でビット一致しているので（tpose_port_plan.py で確認）、ローカル座標を写せばワールド座標もビット一致する
# blender -b 3DAnatomyFemale.blend -P tpose_port_take.py -- <plan.json> <出力 npz>
import bpy, sys, json, hashlib, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; PLAN = json.load(open(a[0], encoding="utf-8")); OUT = a[1]
def h(x): return hashlib.md5(np.ascontiguousarray(x).tobytes()).hexdigest()[:16]
out = {}
for r in PLAN["move"]:
    o = bpy.data.objects[r["n"]]; me = o.data
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
    out["co__" + r["n"]] = co.reshape(-1, 3); out["M__" + r["n"]] = np.array(o.matrix_world, np.float64)
    out["topo__" + r["n"]] = np.frombuffer(h(lv).encode(), np.uint8)
for r in PLAN["color"]:
    me = bpy.data.objects[r["n"]].data
    for k in r["attrs"]:
        at = me.color_attributes[k]; buf = np.empty(len(at.data) * 4, np.float32); at.data.foreach_get("color", buf)
        out["col__%s__%s" % (r["n"], k)] = buf.reshape(-1, 4)
for r in PLAN["keep_arm"]:   # 腕の6個（マスターは Man_All の頂点＋同じ側の肩甲骨の行列）。Tポーズ版の手・前腕の行列で置き直す用（tpose_port_arm6.py）
    o = bpy.data.objects[r["n"]]; me = o.data
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
    out["arm__" + r["n"]] = co.reshape(-1, 3); out["armM__" + r["n"]] = np.array(o.matrix_world, np.float64)
for o in (o for c in ("筋肉_右前腕", "筋肉_左前腕") if c in bpy.data.collections for o in bpy.data.collections[c].objects if o.type == 'MESH'):
    # 前腕の筋（マスター）。Tポーズ版で前腕の筋にかけたねじり φ(s) を当てはめる用（tpose_port_arm6.py）
    co = np.empty(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get("co", co)
    out["fa__" + o.name] = co.reshape(-1, 3); out["faM__" + o.name] = np.array(o.matrix_world, np.float64)
np.savez(OUT, **out)
print("TAKEN", len(PLAN["move"]), "parts,", len(PLAN["color"]), "colors ->", OUT)
