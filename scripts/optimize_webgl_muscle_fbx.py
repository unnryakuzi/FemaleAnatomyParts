import json
import sys
from pathlib import Path

import bpy


BASE_RATIOS = {
    "LOD_Rig_胴体": 0.22,
    "LOD_Rig_頭頸部": 0.28,
    "LOD_Rig_骨盤": 0.20,
    "LOD_Rig_右上腕": 0.18,
    "LOD_Rig_左上腕": 0.18,
    "LOD_Rig_右前腕": 0.16,
    "LOD_Rig_左前腕": 0.16,
    "LOD_Rig_右手": 0.12,
    "LOD_Rig_左手": 0.12,
    "LOD_Rig_右大腿": 0.18,
    "LOD_Rig_左大腿": 0.18,
    "LOD_Rig_右下腿": 0.16,
    "LOD_Rig_左下腿": 0.16,
    "LOD_Rig_右足": 0.12,
    "LOD_Rig_左足": 0.12,
}


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    def get_arg(flag, default=None, required=False):
        if flag not in argv:
            if required:
                raise SystemExit(f"missing required arg: {flag}")
            return default
        index = argv.index(flag) + 1
        if index >= len(argv):
            raise SystemExit(f"missing value for arg: {flag}")
        return argv[index]

    return {
        "input": get_arg("--input", required=True),
        "output": get_arg("--output", required=True),
        "scale": float(get_arg("--scale", "1.0")),
        "min_ratio": float(get_arg("--min-ratio", "0.05")),
    }


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablock_collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.images,
    ):
        for datablock in list(datablock_collection):
            if datablock.users == 0:
                datablock_collection.remove(datablock)


def import_fbx(path):
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)


def mesh_objects():
    return [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name in BASE_RATIOS]


def armature_object():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def add_decimate(obj, ratio):
    mod = obj.modifiers.new(name="BudgetDecimate", type="DECIMATE")
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    for index, existing in enumerate(obj.modifiers):
        if existing == mod:
            obj.modifiers.move(index, 0)
            break
    return mod


def cleanup_material_slots(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.material_slot_remove_unused()
    except RuntimeError:
        pass
    obj.select_set(False)


def apply_modifier(obj, name):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=name)
    obj.select_set(False)


def select_exportables(objects, armature):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if armature:
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
    elif objects:
        bpy.context.view_layer.objects.active = objects[0]


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
        bake_anim=False,
        use_armature_deform_only=True,
    )


def main():
    args = parse_args()
    input_path = Path(args["input"])
    output_path = Path(args["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    import_fbx(input_path)

    meshes = mesh_objects()
    armature = armature_object()
    report = {
        "input": str(input_path),
        "output": str(output_path),
        "scale": args["scale"],
        "min_ratio": args["min_ratio"],
        "meshes": [],
    }

    for obj in meshes:
        base_faces = len(obj.data.polygons)
        ratio = max(args["min_ratio"], BASE_RATIOS[obj.name] * args["scale"])
        mod = add_decimate(obj, ratio)
        apply_modifier(obj, mod.name)
        cleanup_material_slots(obj)
        report["meshes"].append(
            {
                "name": obj.name,
                "base_faces": base_faces,
                "final_faces": len(obj.data.polygons),
                "ratio": ratio,
            }
        )

    select_exportables(meshes, armature)
    export_fbx(output_path)

    report["output_bytes"] = output_path.stat().st_size
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
