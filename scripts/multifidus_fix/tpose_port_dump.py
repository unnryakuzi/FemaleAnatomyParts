# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 全メッシュの照合用ダンプ。.blend は保存しない
#  <out>.json = パーツごとの頂点数・頂点/面/ワールド座標のハッシュ・行列・モディファイア・色・コレクション・プロパティ
#  <out>.npz  = パーツごとのワールド座標（float32、キー = json の "key"）
# blender -b <blend> -P tpose_port_dump.py -- <出力の接頭辞（拡張子なし）>
import bpy, sys, json, hashlib, numpy as np
out = sys.argv[sys.argv.index("--") + 1]
def h(a): return hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()[:16]
d = {"file": bpy.data.filepath, "objects": {}}
W = {}
for i, o in enumerate(o for o in bpy.data.objects if o.type == 'MESH'):
    me = o.data; n = len(me.vertices)
    co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
    M = np.array(o.matrix_world, np.float64)
    w = (co.astype(np.float64) @ M[:3, :3].T + M[:3, 3]).astype(np.float32)
    key = "o%04d" % i; W[key] = w
    cols = {}
    for a in me.color_attributes:
        buf = np.empty(len(a.data) * 4, np.float32); a.data.foreach_get("color", buf)
        cols[a.name] = dict(domain=a.domain, type=a.data_type, n=len(a.data), hash=h(buf.round(5)))
    d["objects"][o.name] = dict(
        key=key, base=o.name.split("(")[0], nv=n, nf=len(me.polygons), nl=len(me.loops),
        cohash=h(co), topo=h(lv), whash=h(w.round(5)),
        cen=w.mean(0).tolist() if n else None, mn=w.min(0).tolist() if n else None, mx=w.max(0).tolist() if n else None,
        M=[[float(x) for x in r] for r in o.matrix_world], Mb=[[float(x) for x in r] for r in o.matrix_basis],
        parent=o.parent.name if o.parent else None, ptype=o.parent_type if o.parent else None,
        mods=[dict(n=m.name, t=m.type) for m in o.modifiers],
        colls=[c.name for c in o.users_collection], mats=[m.name if m else None for m in me.materials],
        cols=cols, props={k: str(o[k])[:80] for k in o.keys() if not k.startswith("_")},
        hide=dict(eye=o.hide_get() if o.name in bpy.context.view_layer.objects else None, vp=o.hide_viewport, rd=o.hide_render),
        mesh=me.name, users=me.users)
d["n_mesh"] = len(d["objects"])
d["other"] = {o.name: o.type for o in bpy.data.objects if o.type != 'MESH'}
d["colls"] = {c.name: [ch.name for ch in c.children] for c in bpy.data.collections}
json.dump(d, open(out + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
np.savez(out + ".npz", **W)
print("DUMPED", d["n_mesh"], sum(v["nv"] for v in d["objects"].values()))
