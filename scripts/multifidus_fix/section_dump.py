# 指定した高さ z の水平断面（三角形と平面の交線）を、パーツの種類ごとに書き出す。.blend は保存しない
#  種類: 肋骨（肋骨・肋軟骨）／外形の筋（外腹斜筋・前鋸筋・広背筋・大胸筋・僧帽筋・腹直筋・白線）／腹横筋／肋間筋
#  z は「第N肋骨の最も外側の点の高さ」で指定する（男女で同じ肋骨の高さを比べるため）
# blender -b <blend> -P section_dump.py -- <出力 json> <肋骨の番号をカンマ区切り 例 6,7,8,9,10>
import bpy, sys, json, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; OUT = a[0]; LEVELS = [int(x) for x in a[1].split(",")]
base = lambda n: n.split("(")[0].split(".")[0]
KAN = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}
def kind(b):
    if ("肋骨" in b or "肋軟骨" in b) and "挙筋" not in b: return "rib"
    if any(s in b for s in ("外腹斜筋", "前鋸筋", "広背筋", "大胸筋", "僧帽筋", "腹直筋", "白線")): return "shell"
    if "腹横筋" in b: return "ta"
    if "肋間筋" in b: return "ic"
    return None
objs = [(o, kind(base(o.name))) for o in bpy.data.objects if o.type == 'MESH' and kind(base(o.name))]
def world(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
def tris(o):
    me = o.data; me.calc_loop_triangles(); t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t); return t.reshape(-1, 3)
cache = {o: (world(o), tris(o)) for o, k in objs}
res = {}
for lv in LEVELS:
    rib = next(o for o, k in objs if base(o.name) == "右第%s肋骨" % KAN[lv])
    W = cache[rib][0]; z = float(W[np.argmin(W[:, 0]), 2])   # 右の肋骨の最も外側（x 最小）の高さ
    segs = {}
    for o, k in objs:
        V, T = cache[o]
        if V[:, 2].min() > z or V[:, 2].max() < z: continue
        d = V[:, 2] - z; dt = d[T]; s = np.sign(dt)
        m = (s.min(1) < 0) & (s.max(1) > 0)
        for tri, dd in zip(T[m], dt[m]):
            pts = []
            for i, j in ((0, 1), (1, 2), (2, 0)):
                if (dd[i] < 0) != (dd[j] < 0):
                    t_ = dd[i] / (dd[i] - dd[j]); p = V[tri[i]] + t_ * (V[tri[j]] - V[tri[i]]); pts.append([round(float(p[0]), 5), round(float(p[1]), 5)])
            if len(pts) == 2: segs.setdefault(k, []).append(pts)
    res[str(lv)] = dict(z=z, segs=segs)
    print("level", lv, "z", round(z, 3), {k: len(v) for k, v in segs.items()}, flush=True)
json.dump(res, open(OUT, "w", encoding="utf-8"))
print("DONE")
