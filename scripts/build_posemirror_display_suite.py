import argparse
import json
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTDIR = ROOT / "Result" / "PoseMirrorDisplaySuite"
EXISTING_VARIANTS_DIR = ROOT / "3DAnatomyman_Japanese_fbx" / "variants"


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    return parser.parse_args(argv)


def ensure_object_mode():
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def export_fbx(path, mesh_objects, armature):
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    if armature is not None:
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
    elif mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]

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


def duplicate_lod_body():
    source = bpy.data.objects.get("LOD_Body")
    armature = bpy.data.objects.get("Armature")
    if source is None or armature is None:
        raise SystemExit("LOD_Body or Armature not found in current blend")

    dup = source.copy()
    dup.data = source.data.copy()
    dup.name = "PoseMirror_A_BodyDisplay"
    dup.data.name = "PoseMirror_A_BodyDisplay_Mesh"
    bpy.context.scene.collection.objects.link(dup)

    for mod in list(dup.modifiers):
        if mod.type != "ARMATURE":
            dup.modifiers.remove(mod)
    if not any(mod.type == "ARMATURE" for mod in dup.modifiers):
        mod = dup.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = armature
        mod.use_vertex_groups = True
    else:
        for mod in dup.modifiers:
            if mod.type == "ARMATURE":
                mod.object = armature
                mod.use_vertex_groups = True

    material = bpy.data.materials.new(name="PoseMirror_A_Clay")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (320, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (40, 0)
    bsdf.inputs["Base Color"].default_value = (0.72, 0.69, 0.66, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.82
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    dup.data.materials.clear()
    dup.data.materials.append(material)
    return dup, material, armature


def bbox_world(objects):
    mins = Vector((float("inf"), float("inf"), float("inf")))
    maxs = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, world_corner.x)
            mins.y = min(mins.y, world_corner.y)
            mins.z = min(mins.z, world_corner.z)
            maxs.x = max(maxs.x, world_corner.x)
            maxs.y = max(maxs.y, world_corner.y)
            maxs.z = max(maxs.z, world_corner.z)
    return mins, maxs


def look_at(obj, target):
    direction = target - obj.location
    quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = quat.to_euler()


def make_camera(name, location, ortho_scale, target):
    camera_data = bpy.data.cameras.new(name)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_scale
    camera_obj = bpy.data.objects.new(name, camera_data)
    bpy.context.scene.collection.objects.link(camera_obj)
    camera_obj.location = location
    look_at(camera_obj, target)
    return camera_obj


def render_previews(objects, variant_dir):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1600
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_xray = False

    visible_names = {obj.name for obj in objects}
    prior_render = {}
    prior_view = {}
    for obj in scene.objects:
        prior_render[obj.name] = obj.hide_render
        prior_view[obj.name] = obj.hide_viewport
        if obj.type not in {"MESH", "ARMATURE", "CAMERA", "LIGHT"}:
            obj.hide_render = True
            obj.hide_viewport = True
            continue
        if obj.type == "MESH" and obj.name not in visible_names:
            obj.hide_render = True
            obj.hide_viewport = True

    mins, maxs = bbox_world(objects)
    center = (mins + maxs) * 0.5
    size = maxs - mins
    ortho_scale = max(size.x, size.z) * 1.35
    depth = max(size.y, size.x, size.z) * 2.0

    cameras = {
        "preview_front.png": make_camera("PM_A_Front", Vector((center.x, center.y - depth, center.z)), ortho_scale, center),
        "preview_side.png": make_camera("PM_A_Side", Vector((center.x + depth, center.y, center.z)), ortho_scale, center),
        "preview_back.png": make_camera("PM_A_Back", Vector((center.x, center.y + depth, center.z)), ortho_scale, center),
    }

    original_camera = scene.camera
    try:
        for filename, camera in cameras.items():
            scene.camera = camera
            scene.render.filepath = str(variant_dir / filename)
            bpy.ops.render.render(write_still=True)
    finally:
        scene.camera = original_camera
        for camera in cameras.values():
            bpy.data.objects.remove(camera, do_unlink=True)
        for name, value in prior_render.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_render = value
        for name, value in prior_view.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_viewport = value


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def folder_size(path):
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def export_a_variant(outdir):
    variant_dir = outdir / "A_lod_body_display"
    variant_dir.mkdir(parents=True, exist_ok=True)

    body, material, armature = duplicate_lod_body()
    mesh_data = body.data
    model_path = variant_dir / "model.fbx"

    try:
        export_fbx(model_path, [body], armature)
        render_previews([body], variant_dir)
        metrics = {
            "variant_id": "A_lod_body_display",
            "label": "Body display",
            "method": "lod_body",
            "notes": "Single-shell LOD_Body export aimed at PoseManiacs-like readability.",
            "fbx_bytes": model_path.stat().st_size,
            "texture_bytes": 0,
            "total_bytes": model_path.stat().st_size,
            "texture_count": 0,
            "mesh_count": 1,
            "face_count": len(body.data.polygons),
            "vertex_count": len(body.data.vertices),
            "material_count": len(body.data.materials),
            "textures": [],
        }
        write_json(variant_dir / "metrics.json", metrics)
        return metrics
    finally:
        bpy.data.objects.remove(body, do_unlink=True)
        if material.users == 0:
            bpy.data.materials.remove(material)
        if mesh_data.users == 0:
            bpy.data.meshes.remove(mesh_data)


def package_existing_variant(src_name, dst_name, label, notes, outdir):
    src_dir = EXISTING_VARIANTS_DIR / src_name
    dst_dir = outdir / dst_name
    copy_tree(src_dir, dst_dir)

    metrics_path = dst_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["variant_id"] = dst_name
    metrics["label"] = label
    metrics["notes"] = notes
    metrics["source_variant"] = src_name
    metrics["package_total_bytes"] = folder_size(dst_dir)
    write_json(metrics_path, metrics)
    return metrics


def write_summary(outdir, metrics_list):
    write_json(outdir / "comparison.json", metrics_list)

    lines = [
        "# PoseMirror Display Variant Suite",
        "",
        "| Variant | Label | Method | FBX Bytes | Package Bytes | Faces | Verts | Notes |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for entry in metrics_list:
        package_bytes = entry.get("package_total_bytes", entry["total_bytes"])
        lines.append(
            f"| {entry['variant_id']} | {entry['label']} | {entry['method']} | "
            f"{entry['fbx_bytes']} | {package_bytes} | {entry['face_count']} | "
            f"{entry['vertex_count']} | {entry['notes']} |"
        )

    (outdir / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    metrics = []
    metrics.append(export_a_variant(outdir))
    metrics.append(
        package_existing_variant(
            src_name="C_mesh_target4mb",
            dst_name="B_muscle_mesh_target4mb",
            label="Open-shell muscle mesh",
            notes="Existing 4MB-class open-shell decimated anatomy mesh for pose readability comparison.",
            outdir=outdir,
        )
    )
    metrics.append(
        package_existing_variant(
            src_name="E_texture_target4mb",
            dst_name="C_muscle_textured_target",
            label="Textured muscle mesh",
            notes="Existing textured anatomy mesh with baked normal/AO for higher perceived detail.",
            outdir=outdir,
        )
    )
    write_summary(outdir, metrics)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
