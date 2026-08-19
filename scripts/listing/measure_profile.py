# -*- coding: utf-8 -*-
"""胴体の断面プロファイルを測る（読み取りのみ）。
usage: blender -b <file> -P profile_body.py -- <label> <col1,col2,...> <z0> <z1>
"""
import bpy, sys
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
label, cols, z0, z1 = a[0], a[1].split(','), float(a[2]), float(a[3])

objs = []
for cn in cols:
    c = bpy.data.collections.get(cn)
    if c:
        objs += [o for o in c.all_objects if o.type == 'MESH']
print(f"@@@ {label} target_objs={len(objs)} from {cols}")

pts = []
for o in objs:
    mw = o.matrix_world
    for v in o.data.vertices:
        w = mw @ v.co
        if z0 <= w.z <= z1:
            pts.append(w)
print(f"@@@ pts_in_range={len(pts)}")

STEP = 0.02
z = z0
while z < z1:
    band = [p for p in pts if z <= p.z < z + STEP]
    if band:
        xs = [p.x for p in band]; ys = [p.y for p in band]
        print(f"@@@ Z {z:.3f} n={len(band):6d} |X|max={max(abs(min(xs)),abs(max(xs))):.4f} "
              f"X=[{min(xs):+.4f},{max(xs):+.4f}] Y=[{min(ys):+.4f},{max(ys):+.4f}]")
    z += STEP

# 個別オブジェクトの bbox（外性器の特定用）
for o in objs:
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    print(f"@@@ SUB {o.name!r} bbox=({mn.x:+.4f},{mn.y:+.4f},{mn.z:+.4f})-({mx.x:+.4f},{mx.y:+.4f},{mx.z:+.4f})")
print("@@@ DONE")
