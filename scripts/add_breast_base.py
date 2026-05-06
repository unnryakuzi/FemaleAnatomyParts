import bpy
import bmesh
import datetime
import math
import os
from collections import deque


BODY_NAME = "Body_Tpose"
BREAST_NAME = "Breast_Base"


def save_backup():
    backup_dir = bpy.path.abspath("//backups")
    os.makedirs(backup_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(bpy.data.filepath))[0] or "unsaved_scene"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{base}_pre_breast_headless_{stamp}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=backup_path, copy=True)
    print(f"backup_path={backup_path}")


def face_in_breast_patch(face):
    center = face.calc_center_median()
    dx = (center.x - 0.088) / 0.095
    dz = (center.z - 1.205) / 0.150
    return (
        0.012 <= center.x <= 0.190
        and 1.070 <= center.z <= 1.355
        and center.y >= 0.060
        and dx * dx + dz * dz <= 1.0
    )


def build_patch_mesh(body_obj):
    bm = bmesh.new()
    bm.from_mesh(body_obj.data)
    bm.faces.ensure_lookup_table()

    keep_faces = [face for face in bm.faces if face_in_breast_patch(face)]
    if not keep_faces:
        raise RuntimeError("No chest patch faces matched the Breast_Base mask.")

    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face not in keep_faces], context="FACES")
    loose_verts = [vert for vert in bm.verts if not vert.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    center_x = 0.090
    center_z = 1.190
    radius_x = 0.092
    radius_z = 0.125
    max_forward = 0.050
    max_drop = 0.018
    max_outer = 0.006

    boundary_verts = {vert for edge in bm.edges if len(edge.link_faces) == 1 for vert in edge.verts}

    for vert in bm.verts:
        if vert in boundary_verts:
            continue

        dx = (vert.co.x - center_x) / radius_x
        dz = (vert.co.z - center_z) / radius_z
        d2 = dx * dx + dz * dz
        if d2 >= 1.20:
            continue

        base = max(0.0, 1.0 - d2 / 1.20)
        weight = base * base
        lower_bias = max(0.0, (center_z - vert.co.z) / radius_z)
        upper_bias = max(0.0, (vert.co.z - center_z) / radius_z)

        vert.co.y += max_forward * weight * (1.0 - 0.30 * upper_bias)
        vert.co.z -= max_drop * weight * (0.25 + 0.75 * lower_bias)
        vert.co.x += max_outer * weight * dx

    interior_verts = [vert for vert in bm.verts if vert not in boundary_verts]
    for _ in range(4):
        bmesh.ops.smooth_vert(
            bm,
            verts=interior_verts,
            factor=0.20,
            use_axis_x=True,
            use_axis_y=True,
            use_axis_z=True,
        )

    mesh = bpy.data.meshes.new(BREAST_NAME)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def build_boundary_group(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    boundary = {vert.index for edge in bm.edges if len(edge.link_faces) == 1 for vert in edge.verts}
    neighbors = {vert.index: {edge.other_vert(vert).index for edge in vert.link_edges} for vert in bm.verts}

    ring_distance = {index: 0 for index in boundary}
    queue = deque(boundary)
    while queue:
        current = queue.popleft()
        if ring_distance[current] >= 3:
            continue
        for nxt in neighbors[current]:
            if nxt not in ring_distance:
                ring_distance[nxt] = ring_distance[current] + 1
                queue.append(nxt)

    bm.free()

    group = obj.vertex_groups.new(name="ShrinkwrapBoundary")
    for vertex_index in range(len(obj.data.vertices)):
        if vertex_index not in ring_distance:
            continue
        weight = max(0.0, 1.0 - (ring_distance[vertex_index] / 3.0))
        if weight > 0.0:
            group.add([vertex_index], weight, "REPLACE")

    return group.name


def ensure_material(obj, body_obj):
    obj.data.materials.clear()
    if body_obj.data.materials:
        obj.data.materials.append(body_obj.data.materials[0])


def configure_modifiers(obj, body_obj, boundary_group_name):
    mirror = obj.modifiers.new(name="Mirror_X", type="MIRROR")
    mirror.use_axis[0] = True
    mirror.use_axis[1] = False
    mirror.use_axis[2] = False
    mirror.use_clip = False
    mirror.use_mirror_merge = False

    subsurf = obj.modifiers.new(name="Breast_Subd", type="SUBSURF")
    subsurf.levels = 1
    subsurf.render_levels = 2
    subsurf.subdivision_type = "CATMULL_CLARK"

    shrink = obj.modifiers.new(name="Boundary_Shrinkwrap", type="SHRINKWRAP")
    shrink.target = body_obj
    shrink.wrap_method = "NEAREST_SURFACEPOINT"
    shrink.wrap_mode = "ABOVE_SURFACE"
    shrink.offset = 0.0005
    shrink.vertex_group = boundary_group_name


def main():
    if not bpy.data.filepath:
        raise RuntimeError("The current Blender file must be saved before running this script.")

    body_obj = bpy.data.objects.get(BODY_NAME)
    if body_obj is None or body_obj.type != "MESH":
        raise RuntimeError(f"{BODY_NAME} mesh not found.")

    existing = bpy.data.objects.get(BREAST_NAME)
    if existing is not None:
        bpy.data.objects.remove(existing, do_unlink=True)

    existing_mesh = bpy.data.meshes.get(BREAST_NAME)
    if existing_mesh is not None and existing_mesh.users == 0:
        bpy.data.meshes.remove(existing_mesh)

    save_backup()

    mesh = build_patch_mesh(body_obj)
    breast_obj = bpy.data.objects.new(BREAST_NAME, mesh)
    breast_obj.matrix_world = body_obj.matrix_world.copy()
    bpy.context.scene.collection.objects.link(breast_obj)

    ensure_material(breast_obj, body_obj)
    boundary_group_name = build_boundary_group(breast_obj)
    configure_modifiers(breast_obj, body_obj, boundary_group_name)

    for polygon in breast_obj.data.polygons:
        polygon.use_smooth = True

    bpy.ops.wm.save_mainfile()

    print(f"created_object={breast_obj.name}")
    print(f"vertex_count={len(breast_obj.data.vertices)}")
    print(f"face_count={len(breast_obj.data.polygons)}")
    print(f"modifiers={[modifier.type for modifier in breast_obj.modifiers]}")


if __name__ == "__main__":
    main()
