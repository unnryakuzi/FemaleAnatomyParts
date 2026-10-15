# 腸骨稜まわりの水平断面（寛骨・外腹斜筋・内腹斜筋・腹横筋・腹直筋・白線）を書き出す。.blend は保存しない
#  高さは「寛骨のいちばん上（腸骨稜の頂点）から何 mm 下か」で指定する（男女で同じ所を比べるため）
# blender -b <blend> -P pelvis_section.py -- <出力 json> <腸骨稜から下の mm をカンマ区切り 例 -40,-20,0,20,40,60> [候補 npz]
import bpy, sys, json, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; OUT = a[0]; DOWN = [float(x) / 1000 for x in a[1].split(",")]
CAND = np.load(a[2]) if len(a) > 2 else None
base = lambda n: n.split("(")[0].split(".")[0]
KIND = {"寛骨": "bone", "外腹斜筋": "eo", "内腹斜筋": "io", "腹横筋": "ta", "腹直筋": "ra", "白線": "la", "錐体筋": "py"}
def kind(b):
    if "肋骨" in b and "挙筋" not in b or "肋軟骨" in b: return "rib"
    return next((v for k, v in KIND.items() if k in b), None)
objs = [(o, kind(base(o.name))) for o in bpy.data.objects if o.type == 'MESH' and kind(base(o.name))]
def world(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
    W = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    if CAND is not None and base(o.name) in CAND.files: W = CAND[base(o.name)].astype(float)
    return W
def tris(o):
    me = o.data; me.calc_loop_triangles(); t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t); return t.reshape(-1, 3)
cache = {o: (world(o), tris(o)) for o, k in objs}
top = max(cache[o][0][:, 2].max() for o, k in objs if k == "bone")
res = {"top": float(top), "levels": {}}
for dz in DOWN:
    z = top - dz; segs = {}
    for o, k in objs:
        V, T = cache[o]
        if V[:, 2].min() > z or V[:, 2].max() < z: continue
        dt = V[:, 2][T] - z; m = (dt.min(1) < 0) & (dt.max(1) > 0)
        for tri, dd in zip(T[m], dt[m]):
            pts = []
            for i, j in ((0, 1), (1, 2), (2, 0)):
                if (dd[i] < 0) != (dd[j] < 0):
                    t_ = dd[i] / (dd[i] - dd[j]); p = V[tri[i]] + t_ * (V[tri[j]] - V[tri[i]]); pts.append([round(float(p[0]), 5), round(float(p[1]), 5)])
            if len(pts) == 2: segs.setdefault(k, []).append(pts)
    res["levels"]["%d" % round(dz * 1000)] = dict(z=z, segs=segs)
    print("level", round(dz * 1000), "z", round(z, 3), {k: len(v) for k, v in segs.items()}, flush=True)
json.dump(res, open(OUT, "w", encoding="utf-8")); print("DONE top", round(top, 3))
