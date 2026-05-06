import json

import bpy


def obj_entry(obj):
    return {
        "name": obj.name,
        "type": obj.type,
        "verts": len(obj.data.vertices) if obj.type == "MESH" else None,
        "faces": len(obj.data.polygons) if obj.type == "MESH" else None,
        "collections": [c.name for c in obj.users_collection],
    }


def main():
    collections = []
    for col in bpy.data.collections:
        type_counts = {}
        mesh_faces = 0
        mesh_verts = 0
        for obj in col.objects:
            type_counts[obj.type] = type_counts.get(obj.type, 0) + 1
            if obj.type == "MESH":
                mesh_faces += len(obj.data.polygons)
                mesh_verts += len(obj.data.vertices)
        collections.append({
            "name": col.name,
            "object_count": len(col.objects),
            "type_counts": type_counts,
            "mesh_faces": mesh_faces,
            "mesh_verts": mesh_verts,
        })

    data = {
        "filepath": bpy.data.filepath,
        "object_count": len(bpy.data.objects),
        "mesh_count": len([o for o in bpy.data.objects if o.type == "MESH"]),
        "collections": sorted(collections, key=lambda x: x["mesh_faces"], reverse=True),
        "top_meshes": sorted(
            [obj_entry(o) for o in bpy.data.objects if o.type == "MESH"],
            key=lambda x: x["faces"],
            reverse=True,
        )[:50],
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
