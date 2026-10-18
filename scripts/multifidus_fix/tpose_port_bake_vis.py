# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 2つの焼いた色（bake_color.py の PNG）で色が変わる画素を、
#  「外から見えるか」（体の外へ5方向に光線を飛ばし、どれかが体に当たらず抜ければ見える）と「水着の下か」（外向きに 3cm 以内で水着に当たる）で分けて数える
#  焼き直すかの判断用。パーツの名前は 01_ray_idmap.py の npz（最初に当たったパーツ）から。.blend は保存しない
# blender -b female_uv4k.blend -P tpose_port_bake_vis.py -- <色 A.png> <色 B.png> <ray A.npz> <ray B.npz> <出力 npz> [しきい値=24]
import bpy, sys, json, collections, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; PA, PB, RA, RB, OUT = a[:5]; TH = int(a[5]) if len(a) > 5 else 24
def png(p):
    im = bpy.data.images.load(p); w, h = im.size; px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
    return px.reshape(h, w, 4)                       # 下の行から（npz と同じ向き）
def names(p):
    nm = [n.split("(")[0] for n, _ in json.load(open(p[:-4] + "_names.json", encoding="utf-8"))] + ["乳房", "(なし)"]
    return np.array(nm, object)
A, B = png(PA), png(PB); R = np.load(RA); S = np.load(RB); na, nb = names(RA), names(RB)
fa = na[np.where(R["first"] >= 0, R["first"], len(na) - 1)]; fb = nb[np.where(S["first"] >= 0, S["first"], len(nb) - 1)]
cov = R["cov"] & S["cov"]
to8 = lambda x: np.round(np.clip(x, 0, 1) ** (1 / 2.2) * 255)       # 比べるのは見た目の明るさで（おおよその sRGB）
d = np.abs(to8(A[..., :3]) - to8(B[..., :3])).max(2) > TH
d |= (A[..., 3] > 0.5) != (B[..., 3] > 0.5)                         # 当たる／当たらないが変わる画素も
d &= cov
ys, xs = np.where(d); print("色が変わる画素", len(ys), "／ 表面", int(cov.sum()), flush=True)
body = bpy.data.objects["Body"]; dg = bpy.context.evaluated_depsgraph_get()
def bvh(objs):
    V, T = [], []
    for o in objs:
        me = o.evaluated_get(dg).to_mesh(); M = np.array(o.matrix_world)
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        me.calc_loop_triangles(); t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t)
        T.append(t.reshape(-1, 3) + sum(len(v) for v in V)); V.append(co); o.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(np.concatenate(V).tolist(), np.concatenate(T).tolist())
SW = [o for o in bpy.data.objects if o.type == "MESH" and ("Swimwear" in o.name or "水着" in o.name)]
print("水着", [o.name for o in SW], flush=True)
Tb = bvh([body]); Ts = bvh(SW) if SW else None
pos = S["pos"].astype(np.float64); nor = S["nor"].astype(np.float64)
vis = np.zeros(len(ys), bool); sw = np.zeros(len(ys), bool)
for i, (y, x) in enumerate(zip(ys, xs)):
    p = pos[y, x]; n = nor[y, x] / max(np.linalg.norm(nor[y, x]), 1e-12)
    t1 = np.cross(n, (0, 0, 1) if abs(n[2]) < 0.9 else (1, 0, 0)); t1 /= np.linalg.norm(t1); t2 = np.cross(n, t1)
    o_ = Vector(p + n * 0.002)
    for dd in (n, n + 0.84 * t1, n - 0.84 * t1, n + 0.84 * t2, n - 0.84 * t2):   # 法線と、そこから 40° 傾けた4方向
        if Tb.ray_cast(o_, Vector(dd / np.linalg.norm(dd)), 1.0)[0] is None: vis[i] = True; break
    if Ts is not None: sw[i] = Ts.ray_cast(Vector(p + n * 0.0002), Vector(n), 0.03)[0] is not None
np.savez(OUT, ys=ys, xs=xs, vis=vis, sw=sw, fa=fa[ys, xs].astype(str), fb=fb[ys, xs].astype(str))
def show(lab, m):
    print("\n== %s: %d 画素" % (lab, m.sum()))
    for (u, v), c in collections.Counter(zip(fa[ys, xs][m], fb[ys, xs][m])).most_common(14): print("   %5d  %s → %s" % (c, u, v))
show("外から見えない（体の内側の面など）", ~vis)
show("外から見える・水着の下", vis & sw)
show("外から見える・水着の外", vis & ~sw)
P = pos[ys, xs]; m = vis & ~sw; arm = np.abs(P[:, 0]) > 0.25
k = m & arm; print("   水着の外 %-22s %5d 画素" % ("腕・手 |x|>0.25", k.sum()), dict(collections.Counter(fb[ys, xs][k]).most_common(5)))
for lab, z0, z1 in (("頭・首 z>1.40", 1.40, 9), ("胸 1.15-1.40", 1.15, 1.40), ("腹 0.95-1.15", 0.95, 1.15), ("下腹部・鼠径部 0.85-0.95", 0.85, 0.95), ("脚 <0.85", -9, 0.85)):
    k = m & ~arm & (P[:, 2] >= z0) & (P[:, 2] < z1); print("   水着の外 %-22s %5d 画素" % (lab, k.sum()), dict(collections.Counter(fb[ys, xs][k]).most_common(5)))
print("DONE", flush=True)
