# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 腹の深い4層が焼き付けの光線で最初に当たる画素について、
#  その4層が表層（前の Tポーズにもあるパーツ）より何 mm 手前に出ているか（同じ光線で表層に当たる距離 − 4層に当たる距離）を測る。.blend は保存しない
#  表層が光線の範囲（外側 EXT〜内側 DIST−EXT）に無い画素は「表層なし」として、4層が体の表面から何 mm の深さにあるかを出す
# blender -b <候補 .blend> -P tpose_port_abd_depth.py -- <ray npz（前の Tポーズ）> <出力 npz>
import bpy, sys, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; R = np.load(a[0]); OUT = a[1]
EXT, DIST, FAR = 0.01, 0.03, 0.08
ABD = ("腹直筋", "内腹斜筋", "腹横筋", "錐体筋")
BOX = (np.array([-0.22, -0.20, 0.86]), np.array([0.22, 0.20, 1.40]))
dg = bpy.context.evaluated_depsgraph_get()
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格")]
parts = sorted({o for c in USE for o in c.all_objects if o.type == "MESH"}, key=lambda o: o.name) + [bpy.data.objects["Breast_Base"]]
br = bpy.data.objects["Breast_Base"]; sd = br.modifiers.new("SubD", "SUBSURF"); sd.levels = sd.render_levels = 2; dg.update()
def build(objs):
    V, T, K = [], [], []
    for i, o in objs:
        me = o.evaluated_get(dg).to_mesh(); M = np.array(o.matrix_world)
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        me.calc_loop_triangles(); t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t)
        o.evaluated_get(dg).to_mesh_clear()
        if np.any(co.min(0) > BOX[1]) or np.any(co.max(0) < BOX[0]): continue
        T.append(t.reshape(-1, 3) + sum(len(v) for v in V)); V.append(co); K += [i] * (len(t) // 3)
    return BVHTree.FromPolygons(np.concatenate(V).tolist(), np.concatenate(T).tolist()), np.array(K)
bs, ks = build([(i, o) for i, o in enumerate(parts) if not any(s in o.name for s in ABD)])
ba, ka = build([(i, o) for i, o in enumerate(parts) if any(s in o.name for s in ABD)])
pos = R["pos"].astype(np.float64); nor = R["nor"].astype(np.float64)
sel = np.where(R["cov"] & np.all((pos > BOX[0]) & (pos < BOX[1]), axis=2))
rows = []
for y, x in zip(*sel):
    p = pos[y, x]; n = nor[y, x] / max(np.linalg.norm(nor[y, x]), 1e-12); o_ = Vector(p + n * EXT); d = Vector(-n)
    ha = ba.ray_cast(o_, d, DIST)
    if ha[0] is None: continue
    hs = bs.ray_cast(o_, d, FAR)
    if hs[0] is not None and hs[3] <= ha[3]: continue                      # 表層が先 → 4層は見えない
    rows.append((y, x, ka[ha[2]], ha[3], hs[3] if hs[0] is not None else np.nan, ks[hs[2]] if hs[0] is not None else -1, *ha[0]))
A = np.array(rows, dtype=np.float64)
names = np.array([o.name.split("(")[0] for o in parts] + [""], dtype=object)
np.savez(OUT, rows=A, names=names.astype(str))
print("見える画素", len(A))
for nm in sorted(set(names[A[:, 2].astype(int)])):
    m = names[A[:, 2].astype(int)] == nm; dd = (A[m, 4] - A[m, 3]) * 1000; has = np.isfinite(dd)
    print("  %-6s %5d  表層あり %5d: 手前に出ている量 中央 %.1f / 90%%点 %.1f / 最大 %.1f mm   表層なし %5d: 体の表面からの深さ 中央 %.1f mm"
          % (nm, m.sum(), has.sum(), np.median(dd[has]) if has.any() else np.nan, np.percentile(dd[has], 90) if has.any() else np.nan,
             dd[has].max() if has.any() else np.nan, (~has).sum(), np.median((A[m][~has, 3] - EXT) * 1000) if (~has).any() else np.nan), flush=True)
