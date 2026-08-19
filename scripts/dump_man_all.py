import bpy, json, sys

out = {"tree": [], "collections": {}, "scene_root_objects": []}

def walk(col, depth=0):
    out["tree"].append({"name": col.name, "depth": depth,
                        "direct": len(col.objects), "all": len(col.all_objects)})
    out["collections"][col.name] = [o.name for o in col.objects]
    for c in col.children:
        walk(c, depth+1)

walk(bpy.context.scene.collection)
out["scene_root_objects"] = [o.name for o in bpy.context.scene.collection.objects]

dst = r"C:\Users\abesh\Documents\Blender\MaleAnatomy\scripts\man_all_structure.json"
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("DUMPED ->", dst)
