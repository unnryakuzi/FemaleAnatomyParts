# 案1（大胸筋の腹部を他の大胸筋と同じ並び）で、乳房の下にのぞく端を隠す2通りを作る（別名で保存。マスターは触らない）
#  breast: 乳房（Breast_Base、片側＋ミラー）の下の縁を、のぞく所（x 40〜130mm）だけ最大 DROP mm 下げる。縁の頂点は下げた先の筋の表面（正面から光線）に載せる
#  lift:   大胸筋の腹部を LIFT mm 上へ（上腕骨から 30mm 以内は今のまま、90mm で全量）
# blender -b <案1の blend> -P pma_hide_variants.py -- <breast|lift> <量 mm> <保存先>
import bpy, bmesh, sys, math, numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
a = sys.argv[sys.argv.index("--") + 1:]; MODE, AMT, OUT = a[0], float(a[1]) / 1000, a[2]
sc = bpy.context.scene; vl = bpy.context.view_layer
base = lambda n: n.split("(")[0].split(".")[0]
def cs(d, d0, d1):
    t = min(max((d - d0) / (d1 - d0), 0), 1); return (1 + math.cos(math.pi * t)) / 2
if MODE == "breast":
    br = next(o for o in sc.objects if o.type == 'MESH' and o.name.startswith("Breast_Base"))
    for lc in vl.layer_collection.children: lc.exclude = False
    hidden = []
    for o in sc.objects:                                                    # 光線は筋・骨だけに当てる（乳房と見えない物は外す）
        if o.name in vl.objects and (o is br or o.type != 'MESH'): o.hide_set(True); hidden.append(o)
    vl.update(); dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new(); bm.from_mesh(br.data); bm.verts.ensure_lookup_table()
    ring0 = {v.index for e in bm.edges if e.is_boundary for v in e.verts}
    ring1 = {n.index for i in ring0 for e in bm.verts[i].link_edges for n in e.verts} - ring0
    ring2 = {n.index for i in ring1 for e in bm.verts[i].link_edges for n in e.verts} - ring0 - ring1
    M = br.matrix_world; Mi = M.inverted(); moved = 0
    for v in bm.verts:
        wgt = 1.0 if v.index in ring0 else 0.6 if v.index in ring1 else 0.25 if v.index in ring2 else 0.0
        if not wgt: continue
        w = M @ v.co
        if w.z > 1.33: continue                                              # 下半分だけ
        fx = cs(abs(w.x * 1000 - 82) / 1000, 0.0, 0.048)                     # x=82mm を中心に ±48mm でなめらかに 0 へ
        dz = AMT * wgt * fx
        if dz < 1e-5: continue
        nw = Vector((w.x, w.y, w.z - dz))
        if v.index in ring0:                                                 # 縁は下げた先の筋の表面に載せる
            hit = sc.ray_cast(dg, Vector((nw.x, nw.y - 0.3, nw.z)), Vector((0, 1, 0)), distance=0.6)
            if hit[0]: nw.y = hit[1].y - 0.0005
        v.co = Mi @ nw; moved += 1
    bm.to_mesh(br.data); bm.free(); br.data.update()
    for o in hidden: o.hide_set(False)
    print("乳房の頂点を動かした", moved)
else:
    hum = [o.matrix_world @ v.co for o in sc.objects if o.type == 'MESH' and "上腕骨" in o.name for v in o.data.vertices]
    kd = KDTree(len(hum))
    for i, p in enumerate(hum): kd.insert(p, i)
    kd.balance()
    for o in sc.objects:
        if o.type == 'MESH' and base(o.name) in ("右大胸筋腹部", "左大胸筋腹部"):
            M = np.array(o.matrix_world); Mi = np.linalg.inv(M); co = np.array([v.co for v in o.data.vertices]); W = co @ M[:3, :3].T + M[:3, 3]
            s = np.array([1 - cs(kd.find(Vector(p))[2], 0.030, 0.090) for p in W])
            W[:, 2] += AMT * s; o.data.vertices.foreach_set("co", (W @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
            print("上へ", o.name, "最大 %.1f mm" % (AMT * s.max() * 1000))
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True); print("SAVED", OUT)
