import argparse
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


DEFAULT_PREFIX = "LOD_Rig_"
DEFAULT_MAX_DISTANCE = 4.0
DEFAULT_EPSILON = 0.002
DEFAULT_SPREAD = 0.35


def parse_args():
    argv = []
    if "--" in bpy.app.driver_namespace.get("_argv", []):
        argv = bpy.app.driver_namespace["_argv"]
    else:
        import sys

        argv = sys.argv

    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--max-distance", type=float, default=DEFAULT_MAX_DISTANCE)
    parser.add_argument("--epsilon", type=float, default=DEFAULT_EPSILON)
    parser.add_argument("--spread", type=float, default=DEFAULT_SPREAD)
    parser.add_argument("--report", default="")
    return parser.parse_args(argv)


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


def target_meshes(prefix):
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


def select_exportables(objects, armature):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if armature:
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
    elif objects:
        bpy.context.view_layer.objects.active = objects[0]


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


def ray_escapes(scene, depsgraph, obj, face_index, center, direction, epsilon, max_distance):
    origin = center + direction * epsilon
    for _ in range(3):
        hit, location, _normal, hit_index, hit_obj, _matrix = scene.ray_cast(
            depsgraph,
            origin,
            direction,
            distance=max_distance,
        )
        if not hit:
            return True

        same_face = hit_obj == obj and hit_index == face_index
        if same_face and (location - origin).length <= epsilon * 4.0:
            origin = origin + direction * epsilon * 4.0
            continue

        return False

    return True


def prune_hidden_faces(obj, scene, depsgraph, epsilon, max_distance, spread):
    mesh = obj.data
    world_matrix = obj.matrix_world
    normal_matrix = world_matrix.to_3x3()
    delete_indices = []

    for poly in mesh.polygons:
        center = world_matrix @ poly.center
        normal = (normal_matrix @ poly.normal).normalized()
        visible = False
        for direction in sample_directions(normal, spread):
            if ray_escapes(scene, depsgraph, obj, poly.index, center, direction, epsilon, max_distance):
                visible = True
                break
        if not visible:
            delete_indices.append(poly.index)

    if not delete_indices:
        return {
            "name": obj.name,
            "base_faces": len(mesh.polygons),
            "deleted_faces": 0,
            "final_faces": len(mesh.polygons),
        }

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
        "name": obj.name,
        "base_faces": len(mesh.polygons) + len(delete_indices),
        "deleted_faces": len(delete_indices),
        "final_faces": len(mesh.polygons),
    }


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()
    import_fbx(input_path)

    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    meshes = target_meshes(args.prefix)
    armature = armature_object()

    report = {
        "input": str(input_path),
        "output": str(output_path),
        "prefix": args.prefix,
        "epsilon": args.epsilon,
        "max_distance": args.max_distance,
        "spread": args.spread,
        "meshes": [],
    }

    total_base_faces = 0
    total_final_faces = 0

    for obj in meshes:
        entry = prune_hidden_faces(
            obj=obj,
            scene=scene,
            depsgraph=depsgraph,
            epsilon=args.epsilon,
            max_distance=args.max_distance,
            spread=args.spread,
        )
        total_base_faces += entry["base_faces"]
        total_final_faces += entry["final_faces"]
        report["meshes"].append(entry)

    report["base_faces"] = total_base_faces
    report["final_faces"] = total_final_faces
    report["deleted_faces"] = total_base_faces - total_final_faces

    select_exportables(meshes, armature)
    export_fbx(output_path)

    report["output_bytes"] = output_path.stat().st_size

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
