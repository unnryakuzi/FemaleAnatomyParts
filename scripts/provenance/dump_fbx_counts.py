# -*- coding: utf-8 -*-
"""always3d の未加工配布FBXを読み、メッシュごとの頂点/面数を JSON に出す。

  blender -b --factory-startup -P scripts/provenance/dump_fbx_counts.py -- <fbx> <out.json>
"""
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)

out = []
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    me = ob.data
    co = [ob.matrix_world @ v.co for v in me.vertices]
    if not co:
        continue
    out.append({
        "name": ob.name,
        "verts": len(me.vertices),
        "faces": len(me.polygons),
        "bmin": [min(c[i] for c in co) for i in range(3)],
        "bmax": [max(c[i] for c in co) for i in range(3)],
    })

with open(dst, "w", encoding="utf-8", newline="") as f:
    json.dump(out, f, ensure_ascii=False)
print("FBX meshes:", len(out), "->", dst)
