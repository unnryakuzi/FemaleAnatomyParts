# -*- coding: utf-8 -*-
"""blend の主要寸法を測る（読み取りのみ・保存しない）。
usage: blender -b <file.blend> -P inspect_blend.py -- <label>
"""
import bpy, sys, json
from mathutils import Vector

label = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "?"

def wbbox(objs):
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    n = 0
    for o in objs:
        if o.type != 'MESH':
            continue
        n += 1
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    return mn, mx, n

sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == 'MESH']
mn, mx, n = wbbox(meshes)
print(f"@@@ {label} meshes={n} collections={len(bpy.data.collections)}")
print(f"@@@ ALL_BBOX min=({mn.x:.4f},{mn.y:.4f},{mn.z:.4f}) max=({mx.x:.4f},{mx.y:.4f},{mx.z:.4f}) size=({mx.x-mn.x:.4f},{mx.y-mn.y:.4f},{mx.z-mn.z:.4f})")
print(f"@@@ COLLECTIONS {sorted(c.name for c in bpy.data.collections)[:60]}")

# 注目オブジェクト（水着・素体・生殖器）
KEY = ('swimwear', 'bra', 'underwear', 'body', '外皮', '生殖', 'skin')
for o in sc.objects:
    if o.type != 'MESH':
        continue
    ln = o.name.lower()
    if any(k in ln or k in o.name for k in KEY):
        a, b, _ = wbbox([o])
        print(f"@@@ OBJ {o.name!r} verts={len(o.data.vertices)} "
              f"bbox=({a.x:.4f},{a.y:.4f},{a.z:.4f})-({b.x:.4f},{b.y:.4f},{b.z:.4f}) "
              f"dim=({b.x-a.x:.4f},{b.y-a.y:.4f},{b.z-a.z:.4f}) "
              f"mods={[m.type for m in o.modifiers]} parent={o.parent.name if o.parent else None}")

# 生殖器コレクションの範囲（男性のフィット目標）
for cn in ('生殖器', '外皮'):
    c = bpy.data.collections.get(cn)
    if c:
        objs = [o for o in c.all_objects if o.type == 'MESH']
        a, b, k = wbbox(objs)
        print(f"@@@ COL {cn!r} n={k} bbox=({a.x:.4f},{a.y:.4f},{a.z:.4f})-({b.x:.4f},{b.y:.4f},{b.z:.4f})")
        print(f"@@@ COL_MEMBERS {cn!r} {[o.name for o in objs][:20]}")
print("@@@ DONE")
