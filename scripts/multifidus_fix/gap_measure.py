# 下後鋸筋の正中寄りで、広背筋の内面と胸最長筋の外面のすき間（前後方向）と、下後鋸筋の厚みを測る。.blend は保存しない
#  (x, z) の格子ごとに、体の後ろ（+Y）から -Y へ光線を飛ばし、各パーツに入る点・出る点の y を拾う
# blender -b <blend> -P gap_measure.py -- <下後鋸筋の npz（キー=右下後鋸筋/左下後鋸筋、ワールド座標）または -> <出力 json>
import bpy, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]; SPI = np.load(a[0]) if a[0] != "-" else None; OUT = a[1]
base = lambda n: n.split("(")[0].split(".")[0]
for o in bpy.context.scene.objects:
    for md in o.modifiers: md.show_viewport = False
    o.hide_viewport = False
bpy.context.view_layer.update()
def obj(b): return next(o for o in bpy.data.objects if o.type == 'MESH' and base(o.name) == b)
def setco(o, w):
    Mi = np.array(o.matrix_world.inverted()); o.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
if SPI is not None:
    for k in SPI.files: setco(obj(k), SPI[k].astype(np.float64))
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
def tree(o):
    t = BVHTree.FromObject(o, dg); M = o.matrix_world.copy(); return t, M, M.inverted()
def hits(tr, x, z):
    t, M, Mi = tr; ys = []; org = Vector((x, 1.0, z)); d = Vector((0, -1, 0))
    for _ in range(12):
        lo = Mi @ org; ld = (Mi.to_3x3() @ d).normalized()
        h = t.ray_cast(lo, ld, 1.0e6)   # 局所座標はワールドの約100倍の単位なので長めに
        if h[0] is None: break
        wp = M @ h[0]; ys.append(wp.y); org = wp + d * 1e-5
    return ys
res = {}
for side, sg in (("右", -1), ("左", 1)):
    lat, lon, spi = tree(obj(side + "広背筋")), tree(obj(side + "胸最長筋")), tree(obj(side + "下後鋸筋"))
    w = np.array([obj(side + "下後鋸筋").matrix_world @ v.co for v in obj(side + "下後鋸筋").data.vertices])
    zs = np.arange(w[:, 2].min(), w[:, 2].max(), 0.01); rows = []
    for z in zs:
        for ax in np.arange(0.010, 0.060, 0.005):
            x = sg * ax; hl, hn, hs = hits(lat, x, z), hits(lon, x, z), hits(spi, x, z)
            if not hs: continue
            lat_in = hl[1] if len(hl) >= 2 else None          # 広背筋に入って出た点（内面）
            lon_out = hn[0] if hn else None                    # 胸最長筋の外面
            gap = (lat_in - lon_out) * 1000 if (lat_in is not None and lon_out is not None) else None
            thick = (hs[0] - hs[1]) * 1000 if len(hs) >= 2 else None
            rows.append(dict(x=round(ax * 1000), z=round(float(z), 3), gap=None if gap is None else round(gap, 1), spi_thick=None if thick is None else round(thick, 1),
                             spi_out=round((hs[0] - (lat_in if lat_in is not None else hs[0])) * 1000, 1), spi_in=round(((hs[1] if len(hs) > 1 else hs[0]) - (lon_out if lon_out is not None else -9)) * 1000, 1)))
    res[side] = rows
    g = [r["gap"] for r in rows if r["gap"] is not None]; t = [r["spi_thick"] for r in rows if r["spi_thick"] is not None]
    print(side, "列数", len(rows), "すき間 mm 中央値 %.1f / 10%%点 %.1f / 最小 %.1f" % (np.median(g), np.percentile(g, 10), min(g)), " 下後鋸筋の厚み mm 中央値 %.1f / 90%%点 %.1f" % (np.median(t), np.percentile(t, 90)))
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("DONE")
