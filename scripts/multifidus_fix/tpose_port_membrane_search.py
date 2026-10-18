# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 前腕骨間膜の置き方の候補（ねじりの角度のずらし Δφ・剛体の平行移動）ごとに、周りの骨・筋への干渉を数える。.blend は保存しない
#  内外の判定は interference.py と同じ（いちばん近い面の外向き法線の符号、1mm 以上で「中」）。速く回すため間引き（既定 2 点に 1 点）・交差回数の確認なし
# blender -b <tpose_port_arm6.py で作った .blend> -P tpose_port_membrane_search.py -- <出力 json> [間引き=2]
import bpy, sys, json, itertools, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; OUT = a[0]; STEP = int(a[1]) if len(a) > 1 else 2
base = lambda n: n.split("(")[0]
for o in bpy.context.scene.objects:
    if o.hide_viewport: o.hide_viewport = False
    for md in o.modifiers: md.show_viewport = False
for lc in bpy.context.view_layer.layer_collection.children: lc.exclude = False; lc.hide_viewport = False
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
obj = {base(o.name): o for o in bpy.data.objects if o.type == 'MESH'}
def wco(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world); return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
def rot(k, ang):
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]); return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K
ATTACH_MAX = 2.0                                               # 骨への付き（各骨に近い 10% の点の骨までの距離の中央値）の上限 mm。数字だけ追うと膜が骨から離れる
GRID_PHI = (0.0, 0.03, 0.06, 0.09, 0.12); GRID_U = (-0.003, -0.002, -0.001, 0.0, 0.001); GRID_V = (-0.004, -0.003, -0.002, -0.001, 0.0)
PARTNERS = ("尺骨", "橈骨", "深指屈筋", "短母指伸筋", "長母指外転筋", "長母指伸筋", "示指伸筋", "方形回内筋", "長母指屈筋", "回外筋", "浅指屈筋橈骨頭", "浅指屈筋上腕尺骨頭")
res = {}
for side in ("右", "左"):
    mem = obj[side + "前腕骨間膜"]; W0 = wco(mem)[::STEP]
    G0 = np.array(obj[side + "橈骨"].matrix_world); G4 = np.array(obj[side + "尺骨"].matrix_world)
    S = np.linalg.norm(G0[:3, :3], axis=0); Rrel = (G4[:3, :3] / S) @ (G0[:3, :3] / S).T; trel = G4[:3, 3] - Rrel @ G0[:3, 3]
    ang = float(np.arccos(np.clip((np.trace(Rrel) - 1) / 2, -1, 1))); ev, evec = np.linalg.eig(Rrel); k = np.real(evec[:, np.argmin(np.abs(ev - 1))]); k /= np.linalg.norm(k)
    if np.linalg.norm(rot(k, ang) - Rrel) > 1e-6: k = -k
    c = np.linalg.lstsq(np.eye(3) - Rrel + np.outer(k, k), trel - float(trel @ k) * k, rcond=None)[0]
    trees = []
    for p in PARTNERS:
        if side + p not in obj: continue
        Q = obj[side + p]; trees.append((p, BVHTree.FromObject(Q, dg), np.array(Q.matrix_world.inverted()), np.array(Q.matrix_world.to_3x3())))
    def score(W):
        out = {}
        for p, T, Mi, M3 in trees:
            L = W @ Mi[:3, :3].T + Mi[:3, 3]; MiT = np.linalg.inv(M3).T; c_ = 0
            for v in L:
                loc, n, _, _ = T.find_nearest(Vector(v))
                if loc is None: continue
                dw = M3 @ (np.array(loc) - v); nw = MiT @ np.array(n); nn = np.linalg.norm(nw)
                if nn and float(dw @ nw) / nn > 0.001: c_ += 1
            out[p] = round(c_ / len(W) * 100, 2)
        return out
    u = np.cross(k, [0, 0, 1.0]); u /= np.linalg.norm(u); v_ = np.cross(k, u)         # 軸に垂直な2方向
    bt = {p: BVHTree.FromObject(obj[side + p], dg) for p in ("橈骨", "尺骨")}            # 骨への付き: 今の置き方で各骨に近い 10% の点が、どれだけ離れるか
    def bone_d(W, p):
        Mi = np.array(obj[side + p].matrix_world.inverted()); M3 = np.array(obj[side + p].matrix_world.to_3x3()); L = W @ Mi[:3, :3].T + Mi[:3, 3]
        return np.array([np.linalg.norm(M3 @ (np.array(bt[p].find_nearest(Vector(x))[0]) - x)) for x in L])
    near = {p: np.argsort(bone_d(W0, p))[: len(W0) // 10] for p in bt}
    rows = []
    for dphi, du, dv in itertools.product(GRID_PHI, GRID_U, GRID_V):
        W = (W0 - c) @ rot(k, dphi * ang).T + c + du * u + dv * v_
        sc = score(W); att = {p: round(float(np.median(bone_d(W[near[p]], p))) * 1000, 2) for p in bt}
        rows.append(dict(dphi=dphi, du=du, dv=dv, total=round(sum(sc.values()), 2), per=sc, attach_mm=att))
    rows.sort(key=lambda r: r["total"])
    ok = [r for r in rows if max(r["attach_mm"].values()) <= ATTACH_MAX]
    res[side] = dict(axis=k.tolist(), u=u.tolist(), v=v_.tolist(), rows=rows, best_attached=ok[:8], now=next(r for r in rows if r["dphi"] == 0 and r["du"] == 0 and r["dv"] == 0))
    print(side, "今:", res[side]["now"]["total"], res[side]["now"]["attach_mm"], res[side]["now"]["per"], flush=True)
    for r in ok[:6]: print("    付き%.1fmm以内" % (ATTACH_MAX * 1), r["dphi"], r["du"], r["dv"], r["total"], r["attach_mm"], {k_: v for k_, v in r["per"].items() if v > 0}, flush=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("DONE")
