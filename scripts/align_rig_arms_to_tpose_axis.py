import json
from pathlib import Path

import bpy
from mathutils import Vector


ARMATURE_NAME = "Armature"

SIDE_CONFIG = {
    "Right": {
        "shoulder_bone": "RightShoulder",
        "arm_bone": "RightArm",
        "forearm_bone": "RightForeArm",
        "hand_collection": "Rig_右手",
        "target_shoulder_z_degrees": -9.639572775328896,
        "target_arm_z_degrees": -0.8,
        "target_forearm_z_degrees": -2.8,
    },
    "Left": {
        "shoulder_bone": "LeftShoulder",
        "arm_bone": "LeftArm",
        "forearm_bone": "LeftForeArm",
        "hand_collection": "Rig_左手",
        "target_shoulder_z_degrees": 9.633158615209359,
        "target_arm_z_degrees": 0.8,
        "target_forearm_z_degrees": 2.8,
    },
}


def avg_collection_center(collection_name: str) -> Vector:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    collection = bpy.data.collections[collection_name]
    centers = []
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        eval_obj = obj.evaluated_get(depsgraph)
        bbox = [eval_obj.matrix_world @ Vector(corner) for corner in eval_obj.bound_box]
        centers.append(sum(bbox, Vector()) / 8.0)
    if not centers:
        raise RuntimeError(f"No mesh objects found in collection: {collection_name}")
    return sum(centers, Vector()) / len(centers)


def main():
    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError(f"Armature '{ARMATURE_NAME}' not found")

    results = {}
    for side, cfg in SIDE_CONFIG.items():
        shoulder = armature.pose.bones[cfg["shoulder_bone"]]
        arm_bone = armature.pose.bones[cfg["arm_bone"]]
        forearm_bone = armature.pose.bones[cfg["forearm_bone"]]
        shoulder.rotation_mode = "XYZ"
        arm_bone.rotation_mode = "XYZ"
        forearm_bone.rotation_mode = "XYZ"
        hand_center_before = avg_collection_center(cfg["hand_collection"])
        shoulder.rotation_euler.z = 0.0
        arm_bone.rotation_euler.z = 0.0
        forearm_bone.rotation_euler.z = 0.0
        shoulder.rotation_euler.z = cfg["target_shoulder_z_degrees"] / 57.29577951308232
        arm_bone.rotation_euler.z = cfg["target_arm_z_degrees"] / 57.29577951308232
        forearm_bone.rotation_euler.z = cfg["target_forearm_z_degrees"] / 57.29577951308232
        bpy.context.view_layer.update()

        hand_center_after = avg_collection_center(cfg["hand_collection"])
        results[side] = {
            "target_shoulder_z_degrees": cfg["target_shoulder_z_degrees"],
            "target_arm_z_degrees": cfg["target_arm_z_degrees"],
            "target_forearm_z_degrees": cfg["target_forearm_z_degrees"],
            "shoulder_rotation_z_degrees_after": shoulder.rotation_euler.z * 57.29577951308232,
            "arm_rotation_z_degrees_after": arm_bone.rotation_euler.z * 57.29577951308232,
            "forearm_rotation_z_degrees_after": forearm_bone.rotation_euler.z * 57.29577951308232,
            "hand_center_before": list(hand_center_before),
            "hand_center_after": list(hand_center_after),
        }

    report_path = Path(r"C:\Users\abesh\Documents\Blender\MaleAnatomy\Result\arm_alignment_report_rig_only.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
