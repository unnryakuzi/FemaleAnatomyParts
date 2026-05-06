import json
import sys
from pathlib import Path

import bpy


INCLUDE_COLLECTION_PREFIX = "Rig_"
EXCLUDE_COLLECTIONS = {"Rig_未分類"}


def mesh_face_count(obj):
    return len(obj.data.polygons) if obj.type == "MESH" else 0


def target_meshes():
    meshes = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        collections = {c.name for c in obj.users_collection}
        if not any(name.startswith(INCLUDE_COLLECTION_PREFIX) for name in collections):
            continue
        if collections & EXCLUDE_COLLECTIONS:
            continue
        meshes.append(obj)
    return meshes


def find_armature():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def set_selection(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def add_decimate(obj, ratio):
    mod = obj.modifiers.new(name=f"BudgetDecimate_{ratio:.3f}", type="DECIMATE")
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    for index, existing in enumerate(obj.modifiers):
        if existing == mod:
            obj.modifiers.move(index, 0)
            break
    return mod


def remove_modifier(obj, mod):
    if mod and mod.name in obj.modifiers:
        obj.modifiers.remove(mod)


def export_fbx(path):
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        bake_space_transform=True,
        axis_forward="-Z",
        axis_up="Y",
        object_types={"ARMATURE", "MESH"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
        use_triangles=False,
        path_mode="AUTO",
        embed_textures=False,
    )


def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    if "--outdir" not in argv or "--ratios" not in argv:
        raise SystemExit("usage: --outdir <dir> --ratios <ratio1> <ratio2> ...")

    outdir = Path(argv[argv.index("--outdir") + 1])
    ratio_index = argv.index("--ratios") + 1
    ratios = [float(value) for value in argv[ratio_index:]]

    outdir.mkdir(parents=True, exist_ok=True)

    meshes = target_meshes()
    armature = find_armature()
    selected = list(meshes)
    if armature:
        selected.append(armature)

    base_faces = sum(mesh_face_count(obj) for obj in meshes)
    base_verts = sum(len(obj.data.vertices) for obj in meshes)

    results = {
        "filepath": bpy.data.filepath,
        "mesh_count": len(meshes),
        "base_faces": base_faces,
        "base_verts": base_verts,
        "armature": armature.name if armature else None,
        "exports": [],
    }

    for ratio in ratios:
        modifiers = []
        for obj in meshes:
            modifiers.append((obj, add_decimate(obj, ratio)))

        path = outdir / f"muscle_budget_r{ratio:.3f}.fbx"
        set_selection(selected)
        export_fbx(path)

        results["exports"].append({
            "ratio": ratio,
            "output": str(path),
            "bytes": path.stat().st_size,
        })

        for obj, mod in modifiers:
            remove_modifier(obj, mod)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
