import bpy
import bmesh
import datetime
import os
from collections import deque


BODY_NAME = "Body_Tpose"
HEAD_NAME = "Head_Base"

# 頭部face選択基準:
# - Z > 1.54: 首より上（ほぼ頭部のみ）
# - Z > 1.47 かつ |X| < 0.22: 首の中心部（肩を除外）
HEAD_Z_UPPER = 1.54
HEAD_Z_LOWER = 1.47
HEAD_X_LIMIT = 0.22


def save_backup():
    backup_dir = bpy.path.abspath("//backups")
    os.makedirs(backup_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(bpy.data.filepath))[0] or "unsaved_scene"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{base}_pre_head_extract_{stamp}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=backup_path, copy=True)
    print(f"backup_path={backup_path}")


def face_in_head(face):
    c = face.calc_center_median()
    return c.z > HEAD_Z_UPPER or (c.z > HEAD_Z_LOWER and abs(c.x) < HEAD_X_LIMIT)


def build_head_mesh(body_obj):
    bm = bmesh.new()
    bm.from_mesh(body_obj.data)
    bm.faces.ensure_lookup_table()

    keep_faces = [f for f in bm.faces if face_in_head(f)]
    if not keep_faces:
        raise RuntimeError("No head faces matched the selection criteria.")

    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep_faces], context="FACES")
    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

    mesh = bpy.data.meshes.new(HEAD_NAME)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def build_boundary_group(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    boundary = {v.index for e in bm.edges if len(e.link_faces) == 1 for v in e.verts}
    neighbors = {v.index: {e.other_vert(v).index for e in v.link_edges} for v in bm.verts}

    ring_distance = {i: 0 for i in boundary}
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
    for vi in range(len(obj.data.vertices)):
        if vi not in ring_distance:
            continue
        weight = max(0.0, 1.0 - ring_distance[vi] / 3.0)
        if weight > 0.0:
            group.add([vi], weight, "REPLACE")

    return group.name


def ensure_material(obj, body_obj):
    obj.data.materials.clear()
    if body_obj.data.materials:
        obj.data.materials.append(body_obj.data.materials[0])


def configure_modifiers(obj, body_obj, boundary_group_name):
    subsurf = obj.modifiers.new(name="Head_Subd", type="SUBSURF")
    subsurf.levels = 1
    subsurf.render_levels = 2
    subsurf.subdivision_type = "CATMULL_CLARK"

    shrink = obj.modifiers.new(name="Boundary_Shrinkwrap", type="SHRINKWRAP")
    shrink.target = body_obj
    shrink.wrap_method = "NEAREST_SURFACEPOINT"
    shrink.wrap_mode = "ABOVE_SURFACE"
    shrink.offset = 0.0003
    shrink.vertex_group = boundary_group_name


def main():
    if not bpy.data.filepath:
        raise RuntimeError("The current Blender file must be saved before running this script.")

    body_obj = bpy.data.objects.get(BODY_NAME)
    if body_obj is None or body_obj.type != "MESH":
        raise RuntimeError(f"{BODY_NAME} mesh not found.")

    existing = bpy.data.objects.get(HEAD_NAME)
    if existing is not None:
        bpy.data.objects.remove(existing, do_unlink=True)

    existing_mesh = bpy.data.meshes.get(HEAD_NAME)
    if existing_mesh is not None and existing_mesh.users == 0:
        bpy.data.meshes.remove(existing_mesh)

    save_backup()

    mesh = build_head_mesh(body_obj)
    head_obj = bpy.data.objects.new(HEAD_NAME, mesh)
    head_obj.matrix_world = body_obj.matrix_world.copy()
    bpy.context.scene.collection.objects.link(head_obj)

    ensure_material(head_obj, body_obj)
    boundary_group_name = build_boundary_group(head_obj)
    configure_modifiers(head_obj, body_obj, boundary_group_name)

    for polygon in head_obj.data.polygons:
        polygon.use_smooth = True

    bpy.ops.wm.save_mainfile()

    print(f"created_object={head_obj.name}")
    print(f"vertex_count={len(head_obj.data.vertices)}")
    print(f"face_count={len(head_obj.data.polygons)}")
    print(f"modifiers={[m.type for m in head_obj.modifiers]}")


if __name__ == "__main__":
    main()
