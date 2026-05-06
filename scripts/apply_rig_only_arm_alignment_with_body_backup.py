import json
import runpy
from pathlib import Path

import bpy


BODY_NAME = "Body_Tpose"
BACKUP_NAME = "Body_Tpose_CodexBackup"
BACKUP_COLLECTION_NAME = "Codex_Backups"
ALIGN_SCRIPT_PATH = r"C:\Users\abesh\Documents\Blender\MaleAnatomy\scripts\align_rig_arms_to_tpose_axis.py"


def ensure_backup_collection():
    collection = bpy.data.collections.get(BACKUP_COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(BACKUP_COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    return collection


def ensure_body_backup():
    body = bpy.data.objects.get(BODY_NAME)
    if body is None or body.type != "MESH":
        raise RuntimeError(f"{BODY_NAME} not found")

    backup = bpy.data.objects.get(BACKUP_NAME)
    if backup is None:
        backup = body.copy()
        backup.data = body.data.copy()
        backup.name = BACKUP_NAME
        backup.hide_select = True
        backup.hide_viewport = True
        backup.hide_render = True
        collection = ensure_backup_collection()
        collection.objects.link(backup)
    else:
        old_mesh = backup.data
        backup.data = body.data.copy()
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        backup.location = body.location.copy()
        backup.rotation_euler = body.rotation_euler.copy()
        backup.scale = body.scale.copy()
        backup.hide_viewport = True
        backup.hide_render = True
        backup.hide_select = True
    return body, backup


def restore_body_from_backup(body, backup, visible_state):
    old_mesh = body.data
    body.data = backup.data.copy()
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    body.location = backup.location.copy()
    body.rotation_euler = backup.rotation_euler.copy()
    body.scale = backup.scale.copy()
    body.hide_viewport = visible_state["hide_viewport"]
    body.hide_render = visible_state["hide_render"]


def main():
    body, backup = ensure_body_backup()
    before_state = {
        "hide_viewport": bool(body.hide_viewport),
        "hide_render": bool(body.hide_render),
        "location": list(body.location),
        "rotation_euler": list(body.rotation_euler),
        "scale": list(body.scale),
        "vertex_count": len(body.data.vertices),
        "polygon_count": len(body.data.polygons),
    }

    runpy.run_path(ALIGN_SCRIPT_PATH, run_name="__main__")

    restore_body_from_backup(body, backup, before_state)
    bpy.context.view_layer.update()

    armature = bpy.data.objects["Armature"]
    result = {
        "backup_object": backup.name,
        "body_restored": True,
        "body_state_after_restore": {
            "hide_viewport": bool(body.hide_viewport),
            "hide_render": bool(body.hide_render),
            "location": list(body.location),
            "rotation_euler": list(body.rotation_euler),
            "scale": list(body.scale),
            "vertex_count": len(body.data.vertices),
            "polygon_count": len(body.data.polygons),
        },
        "body_state_before_edit": before_state,
        "armature_pose": {
            "RightShoulder_z_deg": armature.pose.bones["RightShoulder"].rotation_euler.z * 57.29577951308232,
            "LeftShoulder_z_deg": armature.pose.bones["LeftShoulder"].rotation_euler.z * 57.29577951308232,
            "RightArm_z_deg": armature.pose.bones["RightArm"].rotation_euler.z * 57.29577951308232,
            "LeftArm_z_deg": armature.pose.bones["LeftArm"].rotation_euler.z * 57.29577951308232,
            "RightForeArm_z_deg": armature.pose.bones["RightForeArm"].rotation_euler.z * 57.29577951308232,
            "LeftForeArm_z_deg": armature.pose.bones["LeftForeArm"].rotation_euler.z * 57.29577951308232,
        },
    }

    report_path = Path(r"C:\Users\abesh\Documents\Blender\MaleAnatomy\Result\arm_alignment_with_body_restore_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
