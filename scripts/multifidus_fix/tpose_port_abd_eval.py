# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 腹の深い4層（腹直筋・内腹斜筋・腹横筋・錐体筋）を奥（+Y＝背中側）へ高さ z だけの関数でずらす候補ごとに、
#  色の焼き付けと同じ光線（01_ray_idmap.py の画素の位置・法線、外側 EXT から内向き DIST まで）で、4層が「最初に当たる」画素を数える。.blend は保存しない
#  ユーザー基準（10-18）「Tポーズ版は前の Tポーズと表層が合っていればよい。腹の筋の形が表層に影響するなら前の Tポーズに合わせて直す」
#  ずらし量 dy(z) = amp（z ≤ z0）→ コサインで 0（z1 で）。z だけの関数なので厚みは変わらない（CLAUDE.md「厚み保持の鉄則」）
# blender -b <候補 .blend> -P tpose_port_abd_eval.py -- <ray npz（前の Tポーズ）> <候補の json: {名前: [[amp_m, z0, z1], ...]}> <出力 json>
import bpy, sys, json, math, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; R = np.load(a[0]); CANDS = json.load(open(a[1], encoding="utf-8")); OUT = a[2]
EXT, DIST = 0.01, 0.03
ABD = ("腹直筋", "内腹斜筋", "腹横筋", "錐体筋")
BOX = (np.array([-0.22, -0.20, 0.86]), np.array([0.22, 0.20, 1.40]))          # 腹と鼠径部のまわり
dg = bpy.context.evaluated_depsgraph_get()
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("靱帯・腱", "骨格")]
parts = sorted({o for c in USE for o in c.all_objects if o.type == "MESH"}, key=lambda o: o.name) + [bpy.data.objects["Breast_Base"]]
br = bpy.data.objects["Breast_Base"]; sd = br.modifiers.new("SubD", "SUBSURF"); sd.levels = sd.render_levels = 2; dg.update()
def world(o):
    me = o.evaluated_get(dg).to_mesh(); M = np.array(o.matrix_world)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    me.calc_loop_triangles(); t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t)
    o.evaluated_get(dg).to_mesh_clear(); return co, t.reshape(-1, 3)
static_V, static_T, static_K, abd = [], [], [], []
for i, o in enumerate(parts):
    co, t = world(o)
    if np.any(co.min(0) > BOX[1]) or np.any(co.max(0) < BOX[0]): continue
    if any(s in o.name for s in ABD): abd.append((i, o, co, t)); continue
    static_T.append(t + sum(len(v) for v in static_V)); static_V.append(co); static_K += [i] * len(t)
SV = np.concatenate(static_V); ST = np.concatenate(static_T); SK = np.array(static_K)
bvh_s = BVHTree.FromPolygons(SV.tolist(), ST.tolist())
pos = R["pos"].astype(np.float64); nor = R["nor"].astype(np.float64)
sel = np.where(R["cov"] & np.all((pos > BOX[0]) & (pos < BOX[1]), axis=2))
P = pos[sel]; N = nor[sel]; N /= np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
print("画素", len(P), "静的パーツの三角形", len(ST), "4層", [o.name.split("(")[0] for _, o, _, _ in abd], flush=True)
def dy_of(z, amp, z0, z1):
    t = np.clip((z - z0) / max(z1 - z0, 1e-9), 0, 1); return amp * (1 + np.cos(np.pi * t)) / 2
res = {}
for cname, spec in CANDS.items():
    V, T, K = [], [], []
    for i, o, co, t in abd:
        c = co.copy(); key = next(s for s in ABD if s in o.name)
        if key in spec and len(spec[key]) == 3: amp, z0, z1 = spec[key]; c[:, 1] += dy_of(c[:, 2], amp, z0, z1)
        if key + "_t" in spec:                                               # 剛体の平行移動 [内側へ, 後ろへ(+Y), 上へ] m。内側 = 右なら +X、左なら -X
            dm, dyy, dz = spec[key + "_t"]; c[:, 0] += dm * (1 if o.name.startswith("右") else -1); c[:, 1] += dyy; c[:, 2] += dz
        T.append(t + sum(len(v) for v in V)); V.append(c); K += [i] * len(t)
    bvh_a = BVHTree.FromPolygons(np.concatenate(V).tolist(), np.concatenate(T).tolist()); KA = np.array(K)
    per = {}
    for p, n in zip(P, N):
        o_ = Vector(p + n * EXT); d = Vector(-n)
        hs = bvh_s.ray_cast(o_, d, DIST); ha = bvh_a.ray_cast(o_, d, DIST)
        if ha[0] is not None and (hs[0] is None or ha[3] < hs[3]):
            nm = parts[KA[ha[2]]].name.split("(")[0]; per[nm] = per.get(nm, 0) + 1
    res[cname] = dict(total=sum(per.values()), per=per)
    print(cname, res[cname]["total"], per, flush=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("DONE")
