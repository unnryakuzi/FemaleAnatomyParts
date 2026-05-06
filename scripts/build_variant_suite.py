import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


TARGET_PREFIX = "LOD_Rig_"
OPEN_SHELL_MAX_DISTANCE = 4.0
OPEN_SHELL_EPSILON = 0.002
OPEN_SHELL_SPREAD = 0.35
ATLAS_SIZE = 512

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

VARIANTS = {
    "A_raw_control": {
        "label": "Raw 15-part control",
        "mode": "raw",
        "notes": "Current 15-part WebGL FBX without shell pruning or decimate.",
    },
    "B_open_shell": {
        "label": "Open-shell control",
        "mode": "open_shell",
        "notes": "Hidden inner faces removed, no further decimate or textures.",
    },
    "C_mesh_target4mb": {
        "label": "Mesh-only target",
        "mode": "mesh_only",
        "scale": 1.0,
        "min_ratio": 0.05,
        "notes": "Open-shell plus decimate floor that empirically lands near 4MB.",
    },
    "D_texture_shell": {
        "label": "Textured open-shell",
        "mode": "textured",
        "decimate": False,
        "notes": "Open-shell geometry plus baked 512 normal/AO atlas.",
    },
    "E_texture_target4mb": {
        "label": "Textured 4MB target",
        "mode": "textured",
        "decimate": True,
        "scale": 1.0,
        "min_ratio": 0.05,
        "notes": "Open-shell + decimate + baked 512 normal/AO atlas.",
    },
}


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--variants", default="all")
    parser.add_argument("--render-previews", action="store_true")
    parser.add_argument("--report-json", action="store_true")
    return parser.parse_args(argv)


def clear_scene():
    ensure_object_mode()
    for obj in list(bpy.data.objects):
        obj.hide_viewport = False
        obj.hide_render = False
        try:
            obj.hide_set(False)
        except RuntimeError:
            pass
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)
    for datablock_collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.images,
        bpy.data.cameras,
    ):
        for datablock in list(datablock_collection):
            if datablock.users == 0:
                datablock_collection.remove(datablock)


def import_fbx(path):
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)


def export_fbx(path, mesh_objects, armature):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    if armature:
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


def target_meshes(prefix=TARGET_PREFIX):
    return [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name.startswith(prefix)
    ]


def armature_object():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def base_name(obj):
    name = obj.get("source_name", obj.name)
    if name.endswith("__LP"):
        name = name[:-4]
    name = re.sub(r"\.\d{3}$", "", name)
    return name


def ensure_object_mode():
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def cleanup_material_slots(obj):
    ensure_object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.material_slot_remove_unused()
    except RuntimeError:
        pass
    obj.select_set(False)


def add_decimate(obj, ratio):
    mod = obj.modifiers.new(name="BudgetDecimate", type="DECIMATE")
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    for index, existing in enumerate(obj.modifiers):
        if existing == mod:
            obj.modifiers.move(index, 0)
            break
    return mod


def apply_modifier(obj, name):
    ensure_object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=name)
    obj.select_set(False)


def decimate_objects(objects, scale, min_ratio):
    report = []
    for obj in objects:
        src_name = base_name(obj)
        ratio = max(min_ratio, BASE_RATIOS[src_name] * scale)
        base_faces = len(obj.data.polygons)
        mod = add_decimate(obj, ratio)
        apply_modifier(obj, mod.name)
        cleanup_material_slots(obj)
        report.append(
            {
                "name": src_name,
                "base_faces": base_faces,
                "final_faces": len(obj.data.polygons),
                "ratio": ratio,
            }
        )
    return report


def orthonormal_basis(normal):
    if abs(normal.z) < 0.999:
        tangent = normal.cross(Vector((0.0, 0.0, 1.0)))
    else:
        tangent = normal.cross(Vector((1.0, 0.0, 0.0)))
    if tangent.length < 1e-6:
        tangent = Vector((1.0, 0.0, 0.0))
    tangent.normalize()
    bitangent = normal.cross(tangent)
    if bitangent.length < 1e-6:
        bitangent = Vector((0.0, 1.0, 0.0))
    bitangent.normalize()
    return tangent, bitangent


def sample_directions(normal, spread):
    tangent, bitangent = orthonormal_basis(normal)
    return [
        normal,
        (normal + tangent * spread).normalized(),
        (normal - tangent * spread).normalized(),
        (normal + bitangent * spread).normalized(),
        (normal - bitangent * spread).normalized(),
    ]


def ray_escapes(scene, depsgraph, obj, face_index, center, direction):
    origin = center + direction * OPEN_SHELL_EPSILON
    for _ in range(3):
        hit, location, _normal, hit_index, hit_obj, _matrix = scene.ray_cast(
            depsgraph,
            origin,
            direction,
            distance=OPEN_SHELL_MAX_DISTANCE,
        )
        if not hit:
            return True

        same_face = hit_obj == obj and hit_index == face_index
        if same_face and (location - origin).length <= OPEN_SHELL_EPSILON * 4.0:
            origin = origin + direction * OPEN_SHELL_EPSILON * 4.0
            continue

        return False

    return True


def prune_hidden_faces(obj, scene, depsgraph):
    mesh = obj.data
    world_matrix = obj.matrix_world
    normal_matrix = world_matrix.to_3x3()
    delete_indices = []

    for poly in mesh.polygons:
        center = world_matrix @ poly.center
        normal = (normal_matrix @ poly.normal).normalized()
        visible = False
        for direction in sample_directions(normal, OPEN_SHELL_SPREAD):
            if ray_escapes(scene, depsgraph, obj, poly.index, center, direction):
                visible = True
                break
        if not visible:
            delete_indices.append(poly.index)

    if delete_indices:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        faces_to_delete = [bm.faces[index] for index in delete_indices]
        bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")
        loose_verts = [vert for vert in bm.verts if not vert.link_faces]
        if loose_verts:
            bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

    return {
        "name": base_name(obj),
        "base_faces": len(mesh.polygons) + len(delete_indices),
        "deleted_faces": len(delete_indices),
        "final_faces": len(mesh.polygons),
    }


def apply_open_shell(objects):
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    report = []
    for obj in objects:
        report.append(prune_hidden_faces(obj, scene, depsgraph))
    return report


def measure_objects(mesh_objects):
    total_faces = sum(len(obj.data.polygons) for obj in mesh_objects)
    total_verts = sum(len(obj.data.vertices) for obj in mesh_objects)
    materials = set()
    for obj in mesh_objects:
        for material in obj.data.materials:
            if material:
                materials.add(material.name)
    return {
        "mesh_count": len(mesh_objects),
        "face_count": total_faces,
        "vertex_count": total_verts,
        "material_count": len(materials),
    }


def duplicate_mesh_objects(objects, suffix):
    duplicates = []
    for obj in objects:
        dup = obj.copy()
        dup.data = obj.data.copy()
        dup.name = f"{obj.name}{suffix}"
        dup.data.name = f"{obj.data.name}{suffix}"
        dup["source_name"] = base_name(obj)
        for collection in obj.users_collection:
            collection.objects.link(dup)
        duplicates.append(dup)
    return duplicates


def join_objects(objects, joined_name):
    ensure_object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_render = False
        try:
            obj.hide_set(False)
        except RuntimeError:
            pass
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = joined_name
    joined.data.name = f"{joined_name}_Mesh"
    joined.hide_viewport = False
    joined.hide_render = False
    return joined


def smart_uv_project(obj):
    ensure_object_mode()
    obj.hide_viewport = False
    obj.hide_render = False
    try:
        obj.hide_set(False)
    except RuntimeError:
        pass
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.02, area_weight=0.0)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")


def create_image(name, size):
    image = bpy.data.images.new(name=name, width=size, height=size, alpha=False, float_buffer=False)
    image.generated_color = (0.5, 0.5, 1.0, 1.0)
    return image


def create_separator_materials(part_names, normal_image, ao_image):
    materials = {}
    crimson = (0.55, 0.08, 0.06, 1.0)
    for part_name in part_names:
        mat = bpy.data.materials.new(name=f"SEP__{part_name}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (500, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (260, 0)
        base_rgb = nodes.new("ShaderNodeRGB")
        base_rgb.outputs[0].default_value = crimson
        base_rgb.location = (-220, 40)
        ao_tex = nodes.new("ShaderNodeTexImage")
        ao_tex.image = ao_image
        ao_tex.location = (-520, -120)
        normal_tex = nodes.new("ShaderNodeTexImage")
        normal_tex.image = normal_image
        normal_tex.image.colorspace_settings.name = "Non-Color"
        normal_tex.location = (-520, -340)

        # Keep bake target images detached from the shader graph to avoid
        # circular dependency warnings while baking into the same images.
        links.new(base_rgb.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        materials[part_name] = mat
    return materials


def create_shared_atlas_material(name, normal_image, ao_image):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (260, 0)
    base_rgb = nodes.new("ShaderNodeRGB")
    base_rgb.outputs[0].default_value = (0.55, 0.08, 0.06, 1.0)
    base_rgb.location = (-460, 80)
    ao_tex = nodes.new("ShaderNodeTexImage")
    ao_tex.image = ao_image
    ao_tex.location = (-460, -120)
    ao_mix = nodes.new("ShaderNodeMixRGB")
    ao_mix.blend_type = "MULTIPLY"
    ao_mix.inputs[0].default_value = 1.0
    ao_mix.location = (-120, 0)
    normal_tex = nodes.new("ShaderNodeTexImage")
    normal_tex.image = normal_image
    normal_tex.image.colorspace_settings.name = "Non-Color"
    normal_tex.location = (-460, -340)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (-120, -260)

    links.new(base_rgb.outputs["Color"], ao_mix.inputs[1])
    links.new(ao_tex.outputs["Color"], ao_mix.inputs[2])
    links.new(ao_mix.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def set_active_bake_image(materials, image):
    for material in materials:
        if not material or not material.use_nodes:
            continue
        image_nodes = [node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeTexImage"]
        for node in image_nodes:
            node.select = False
        target = next((node for node in image_nodes if node.image == image), None)
        if target:
            target.select = True
            material.node_tree.nodes.active = target


def save_image(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()


def bake_variant_textures(source_objects, low_objects, variant_dir, variant_id):
    texture_dir = variant_dir / "textures"
    normal_image = create_image(f"{variant_id}_NormalAtlas", ATLAS_SIZE)
    ao_image = create_image(f"{variant_id}_AOAtlas", ATLAS_SIZE)

    part_names = [base_name(obj) for obj in low_objects]
    separator_mats = create_separator_materials(part_names, normal_image, ao_image)
    for obj in low_objects:
        obj.data.materials.clear()
        obj.data.materials.append(separator_mats[base_name(obj)])

    joined_low = join_objects(low_objects, f"{variant_id}_LowJoined")
    smart_uv_project(joined_low)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 8
    scene.render.bake.use_clear = True
    scene.render.bake.margin = 8
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.02
    scene.render.bake.normal_space = "TANGENT"

    bpy.ops.object.select_all(action="DESELECT")
    for obj in source_objects:
        obj.select_set(True)
    joined_low.select_set(True)
    bpy.context.view_layer.objects.active = joined_low
    set_active_bake_image(joined_low.data.materials, normal_image)
    bpy.ops.object.bake(type="NORMAL")

    bpy.ops.object.select_all(action="DESELECT")
    joined_low.select_set(True)
    bpy.context.view_layer.objects.active = joined_low
    scene.render.bake.use_selected_to_active = False
    set_active_bake_image(joined_low.data.materials, ao_image)
    bpy.ops.object.bake(type="AO")

    normal_path = texture_dir / f"{variant_id}_normal.png"
    ao_path = texture_dir / f"{variant_id}_ao.png"
    save_image(normal_image, normal_path)
    save_image(ao_image, ao_path)

    shared_material = create_shared_atlas_material(f"{variant_id}_AtlasMaterial", normal_image, ao_image)

    ensure_object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    joined_low.select_set(True)
    bpy.context.view_layer.objects.active = joined_low
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")

    separated = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    export_objects = []
    for obj in separated:
        if not obj.data.materials:
            continue
        material_name = obj.data.materials[0].name
        if not material_name.startswith("SEP__"):
            continue
        part_name = material_name.replace("SEP__", "", 1)
        obj.name = part_name
        obj["source_name"] = part_name
        obj.data.materials.clear()
        obj.data.materials.append(shared_material)
        for modifier in list(obj.modifiers):
            if modifier.type == "ARMATURE":
                obj.modifiers.remove(modifier)
        export_objects.append(obj)

    return export_objects, [normal_path, ao_path]


def ensure_armature_modifier(mesh_objects, armature):
    if not armature:
        return
    for obj in mesh_objects:
        has_armature = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        if has_armature:
            continue
        mod = obj.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = armature
        mod.use_vertex_groups = True


def apply_preview_colors(objects):
    for obj in objects:
        obj.color = (0.66, 0.14, 0.12, 1.0)


def bbox_world(objects):
    mins = Vector((math.inf, math.inf, math.inf))
    maxs = Vector((-math.inf, -math.inf, -math.inf))
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


def ensure_camera(name, location, ortho_scale, target):
    camera_data = bpy.data.cameras.new(name)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_scale
    camera_obj = bpy.data.objects.new(name, camera_data)
    bpy.context.scene.collection.objects.link(camera_obj)
    camera_obj.location = location
    look_at(camera_obj, target)
    return camera_obj


def render_previews(variant_dir, export_objects):
    if not export_objects:
        return

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1600
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_xray = False

    visible_names = {obj.name for obj in export_objects}
    for obj in scene.objects:
        if obj.type not in {"MESH", "ARMATURE", "CAMERA"}:
            obj.hide_render = True
            obj.hide_viewport = True
            continue
        obj.hide_render = obj.type == "MESH" and obj.name not in visible_names
        obj.hide_viewport = obj.hide_render

    apply_preview_colors(export_objects)
    mins, maxs = bbox_world(export_objects)
    center = (mins + maxs) * 0.5
    size = maxs - mins
    ortho_scale = max(size.x, size.z) * 1.35
    depth = max(size.y, size.x, size.z) * 2.0

    front = ensure_camera(f"{variant_dir.name}_Front", Vector((center.x, center.y - depth, center.z)), ortho_scale, center)
    side = ensure_camera(f"{variant_dir.name}_Side", Vector((center.x + depth, center.y, center.z)), ortho_scale, center)
    back = ensure_camera(f"{variant_dir.name}_Back", Vector((center.x, center.y + depth, center.z)), ortho_scale, center)

    for label, camera in (("front", front), ("side", side), ("back", back)):
        scene.camera = camera
        scene.render.filepath = str(variant_dir / f"preview_{label}.png")
        bpy.ops.render.render(write_still=True)


def copy_input_variant(input_path, variant_dir):
    model_path = variant_dir / "model.fbx"
    shutil.copy2(input_path, model_path)
    return model_path


def build_raw_variant(input_path, variant_dir, render_images):
    clear_scene()
    import_fbx(input_path)
    meshes = target_meshes()
    armature = armature_object()
    model_path = copy_input_variant(input_path, variant_dir)
    if render_images:
        render_previews(variant_dir, meshes)
    return {
        "export_objects": meshes,
        "armature": armature,
        "model_path": model_path,
        "textures": [],
        "steps": [],
    }


def build_open_shell_variant(input_path, variant_dir, render_images):
    clear_scene()
    import_fbx(input_path)
    meshes = target_meshes()
    armature = armature_object()
    shell_report = apply_open_shell(meshes)
    model_path = variant_dir / "model.fbx"
    export_fbx(model_path, meshes, armature)
    if render_images:
        render_previews(variant_dir, meshes)
    return {
        "export_objects": meshes,
        "armature": armature,
        "model_path": model_path,
        "textures": [],
        "steps": [{"name": "open_shell", "report": shell_report}],
    }


def build_mesh_only_variant(input_path, variant_dir, render_images, scale, min_ratio):
    clear_scene()
    import_fbx(input_path)
    meshes = target_meshes()
    armature = armature_object()
    shell_report = apply_open_shell(meshes)
    decimate_report = decimate_objects(meshes, scale=scale, min_ratio=min_ratio)
    model_path = variant_dir / "model.fbx"
    export_fbx(model_path, meshes, armature)
    if render_images:
        render_previews(variant_dir, meshes)
    return {
        "export_objects": meshes,
        "armature": armature,
        "model_path": model_path,
        "textures": [],
        "steps": [
            {"name": "open_shell", "report": shell_report},
            {"name": "decimate", "report": decimate_report},
        ],
    }


def build_textured_variant(input_path, variant_dir, render_images, do_decimate, scale, min_ratio):
    clear_scene()
    import_fbx(input_path)
    source_meshes = target_meshes()
    armature = armature_object()

    low_meshes = duplicate_mesh_objects(source_meshes, "__LP")
    for obj in low_meshes:
        obj.name = f"{base_name(obj)}__LP"

    shell_report = apply_open_shell(low_meshes)
    steps = [{"name": "open_shell", "report": shell_report}]

    if do_decimate:
        decimate_report = decimate_objects(low_meshes, scale=scale, min_ratio=min_ratio)
        steps.append({"name": "decimate", "report": decimate_report})

    export_objects, texture_paths = bake_variant_textures(source_meshes, low_meshes, variant_dir, variant_dir.name)
    ensure_armature_modifier(export_objects, armature)

    model_path = variant_dir / "model.fbx"
    export_fbx(model_path, export_objects, armature)
    if render_images:
        render_previews(variant_dir, export_objects)

    return {
        "export_objects": export_objects,
        "armature": armature,
        "model_path": model_path,
        "textures": texture_paths,
        "steps": steps + [{"name": "bake", "report": {"atlas_size": ATLAS_SIZE}}],
    }


def bytes_of(paths):
    total = 0
    for path in paths:
        if Path(path).exists():
            total += Path(path).stat().st_size
    return total


def write_variant_metrics(variant_id, config, variant_dir, build_result):
    mesh_stats = measure_objects(build_result["export_objects"])
    texture_bytes = bytes_of(build_result["textures"])
    metrics = {
        "variant_id": variant_id,
        "label": config["label"],
        "method": config["mode"],
        "source_input": str(build_result["model_path"]),
        "fbx_bytes": build_result["model_path"].stat().st_size,
        "texture_bytes": texture_bytes,
        "total_bytes": build_result["model_path"].stat().st_size + texture_bytes,
        "texture_count": len(build_result["textures"]),
        "textures": [str(path) for path in build_result["textures"]],
        "notes": config["notes"],
        "steps": build_result["steps"],
    }
    metrics.update(mesh_stats)
    metrics_path = variant_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def write_comparison_files(outdir, metrics):
    json_path = outdir / "comparison.json"
    json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Variant Comparison",
        "",
        "| Variant | Method | FBX Bytes | Texture Bytes | Total Bytes | Faces | Verts | Materials | Textures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for entry in metrics:
        lines.append(
            "| {variant_id} | {method} | {fbx_bytes} | {texture_bytes} | {total_bytes} | {face_count} | {vertex_count} | {material_count} | {texture_count} |".format(
                **entry
            )
        )
    (outdir / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_variants(raw_value):
    if raw_value == "all":
        return list(VARIANTS.keys())
    requested = []
    for part in raw_value.split(","):
        name = part.strip()
        if not name:
            continue
        if name not in VARIANTS:
            raise SystemExit(f"unknown variant: {name}")
        requested.append(name)
    return requested


def build_variant(input_path, outdir, variant_id, render_images):
    config = VARIANTS[variant_id]
    variant_dir = outdir / variant_id
    if variant_dir.exists():
        shutil.rmtree(variant_dir)
    variant_dir.mkdir(parents=True, exist_ok=True)

    if config["mode"] == "raw":
        result = build_raw_variant(input_path, variant_dir, render_images)
    elif config["mode"] == "open_shell":
        result = build_open_shell_variant(input_path, variant_dir, render_images)
    elif config["mode"] == "mesh_only":
        result = build_mesh_only_variant(
            input_path,
            variant_dir,
            render_images,
            scale=config["scale"],
            min_ratio=config["min_ratio"],
        )
    elif config["mode"] == "textured":
        result = build_textured_variant(
            input_path,
            variant_dir,
            render_images,
            do_decimate=config["decimate"],
            scale=config.get("scale", 1.0),
            min_ratio=config.get("min_ratio", 0.05),
        )
    else:
        raise SystemExit(f"unsupported mode: {config['mode']}")

    return write_variant_metrics(variant_id, config, variant_dir, result)


def main():
    args = parse_args()
    input_path = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    metrics = []
    for variant_id in resolve_variants(args.variants):
        metrics.append(build_variant(input_path, outdir, variant_id, args.render_previews))

    write_comparison_files(outdir, metrics)

    if args.report_json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        for entry in metrics:
            print(
                f"{entry['variant_id']}: total={entry['total_bytes']} "
                f"fbx={entry['fbx_bytes']} textures={entry['texture_bytes']}"
            )


if __name__ == "__main__":
    main()
