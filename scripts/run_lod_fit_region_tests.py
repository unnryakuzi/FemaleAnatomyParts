import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


LOD_NAME = "LOD_Body"
TEST_COLLECTION_NAME = "LOD_Fit_Tests"
RESULT_REPORT = Path(r"C:\Users\abesh\Documents\Blender\MaleAnatomy\Result\lod_fit_region_tests_report.json")

TESTS = [
    {
        "name": "EasyUpperArm",
        "source_collections": ["Rig_右上腕", "Rig_左上腕"],
        "duplicate_name": "LOD_Body_FitTest_EasyUpperArm",
        "proxy_name": "Proxy_EasyUpperArm",
        "voxel_size": 0.012,
        "blend_factor": 0.72,
        "smooth_iterations": 6,
        "region": {
            "x_abs_min": 0.16,
            "x_abs_max": 0.56,
            "y_abs_max": 0.18,
            "z_min": 1.28,
            "z_max": 1.58,
        },
    },
    {
        "name": "HardTorso",
        "source_collections": ["Rig_胴体"],
        "duplicate_name": "LOD_Body_FitTest_HardTorso",
        "proxy_name": "Proxy_HardTorso",
        "voxel_size": 0.016,
        "blend_factor": 0.48,
        "smooth_iterations": 10,
        "region": {
            "x_abs_min": 0.0,
            "x_abs_max": 0.28,
            "y_abs_max": 0.25,
            "z_min": 0.92,
            "z_max": 1.60,
        },
    },
]


def ensure_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def remove_object_if_exists(name: str):
    obj = bpy.data.objects.get(name)
    if obj is None:
        return
    data = getattr(obj, "data", None)
    bpy.data.objects.remove(obj)
    if data and data.users == 0:
        if obj.type == "MESH":
            bpy.data.meshes.remove(data)


def make_proxy_from_collections(collection_names, proxy_name, voxel_size, parent_collection):
    remove_object_if_exists(proxy_name)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    source_count = 0

    for cname in collection_names:
        collection = bpy.data.collections.get(cname)
        if collection is None:
            continue
        for obj in collection.objects:
            if obj.type != "MESH":
                continue
            eval_obj = obj.evaluated_get(depsgraph)
            temp_mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=depsgraph)
            old_vert_count = len(bm.verts)
            bm.from_mesh(temp_mesh)
            new_verts = list(bm.verts)[old_vert_count:]
            if new_verts:
                bmesh.ops.transform(bm, verts=new_verts, matrix=eval_obj.matrix_world)
            bpy.data.meshes.remove(temp_mesh)
            source_count += 1

    mesh = bpy.data.meshes.new(f"{proxy_name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    proxy = bpy.data.objects.new(proxy_name, mesh)
    parent_collection.objects.link(proxy)

    # Outer-envelope proxy from the current visible Rig_ surfaces.
    remesh = proxy.modifiers.new(name="VoxelRemesh", type="REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = voxel_size
    remesh.use_smooth_shade = False
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.object.modifier_apply(modifier=remesh.name)

    smooth = proxy.modifiers.new(name="Smooth", type="SMOOTH")
    smooth.iterations = 8
    smooth.factor = 0.45
    bpy.ops.object.modifier_apply(modifier=smooth.name)

    proxy.display_type = "WIRE"
    proxy.hide_render = True

    return proxy, source_count


def build_region_vertex_group(obj, group_name, region):
    group = obj.vertex_groups.get(group_name)
    if group is None:
        group = obj.vertex_groups.new(name=group_name)
    else:
        for v in obj.data.vertices:
            try:
                group.remove([v.index])
            except RuntimeError:
                pass

    selected = []
    for v in obj.data.vertices:
        co = obj.matrix_world @ v.co
        if abs(co.x) < region["x_abs_min"]:
            continue
        if abs(co.x) > region["x_abs_max"]:
            continue
        if abs(co.y) > region["y_abs_max"]:
            continue
        if co.z < region["z_min"] or co.z > region["z_max"]:
            continue
        selected.append(v.index)
    if selected:
        group.add(selected, 1.0, "REPLACE")
    return group, selected


def duplicate_lod(name, parent_collection):
    source = bpy.data.objects[LOD_NAME]
    remove_object_if_exists(name)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = source.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=depsgraph)
    dup = bpy.data.objects.new(name, mesh)
    dup.matrix_world = eval_obj.matrix_world.copy()
    parent_collection.objects.link(dup)
    return dup


def apply_localized_shrinkwrap(obj, proxy, vertex_group_name, blend_factor, smooth_iterations):
    original = [v.co.copy() for v in obj.data.vertices]

    shrink = obj.modifiers.new(name="LocalizedShrinkwrap", type="SHRINKWRAP")
    shrink.wrap_method = "NEAREST_SURFACEPOINT"
    shrink.wrap_mode = "OUTSIDE_SURFACE"
    shrink.target = proxy
    shrink.vertex_group = vertex_group_name
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=shrink.name)

    smooth = obj.modifiers.new(name="LocalizedSmooth", type="CORRECTIVE_SMOOTH")
    smooth.vertex_group = vertex_group_name
    smooth.factor = 0.35
    smooth.iterations = smooth_iterations
    smooth.use_only_smooth = True
    bpy.ops.object.modifier_apply(modifier=smooth.name)

    group = obj.vertex_groups[vertex_group_name]
    affected = []
    for v in obj.data.vertices:
        weight = 0.0
        for g in v.groups:
            if g.group == group.index:
                weight = g.weight
                break
        if weight <= 0.0:
            continue
        new_co = v.co.copy()
        v.co = original[v.index].lerp(new_co, blend_factor * weight)
        affected.append((original[v.index] - v.co).length)
    return {
        "affected_count": len(affected),
        "max_displacement": max(affected) if affected else 0.0,
        "mean_displacement": (sum(affected) / len(affected)) if affected else 0.0,
    }


def main():
    test_collection = ensure_collection(TEST_COLLECTION_NAME)
    report = {}

    for test in TESTS:
        proxy, source_count = make_proxy_from_collections(
            test["source_collections"],
            test["proxy_name"],
            test["voxel_size"],
            test_collection,
        )
        lod_copy = duplicate_lod(test["duplicate_name"], test_collection)
        vg_name = f"VG_{test['name']}"
        _, selected = build_region_vertex_group(lod_copy, vg_name, test["region"])
        displacement = apply_localized_shrinkwrap(
            lod_copy,
            proxy,
            vg_name,
            test["blend_factor"],
            test["smooth_iterations"],
        )
        report[test["name"]] = {
            "duplicate_name": lod_copy.name,
            "proxy_name": proxy.name,
            "source_collections": test["source_collections"],
            "source_object_count": source_count,
            "region_vertex_count": len(selected),
            "blend_factor": test["blend_factor"],
            "voxel_size": test["voxel_size"],
            "displacement": displacement,
        }

    RESULT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    RESULT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
