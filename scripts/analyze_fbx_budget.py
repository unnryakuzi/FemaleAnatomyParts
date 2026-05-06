import argparse
import json
from pathlib import Path

import bpy


def iter_mesh_objects():
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            yield obj


def face_counts_by_material(obj):
    counts = {}
    mesh = obj.data
    materials = mesh.materials
    for poly in mesh.polygons:
        index = poly.material_index
        name = materials[index].name if index < len(materials) and materials[index] else f"material_{index}"
        counts[name] = counts.get(name, 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="LOD_")
    args, _ = parser.parse_known_args()

    meshes = []
    total_faces = 0
    total_verts = 0
    total_material_slots = 0

    for obj in iter_mesh_objects():
        if args.prefix and not obj.name.startswith(args.prefix):
            continue
        mesh = obj.data
        material_faces = face_counts_by_material(obj)
        entry = {
            "name": obj.name,
            "verts": len(mesh.vertices),
            "edges": len(mesh.edges),
            "faces": len(mesh.polygons),
            "materials": [mat.name if mat else None for mat in mesh.materials],
            "material_face_counts": material_faces,
        }
        meshes.append(entry)
        total_faces += entry["faces"]
        total_verts += entry["verts"]
        total_material_slots += len(entry["materials"])

    summary = {
        "filepath": bpy.data.filepath,
        "mesh_count": len(meshes),
        "total_faces": total_faces,
        "total_verts": total_verts,
        "total_material_slots": total_material_slots,
        "meshes": sorted(meshes, key=lambda x: x["faces"], reverse=True),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
