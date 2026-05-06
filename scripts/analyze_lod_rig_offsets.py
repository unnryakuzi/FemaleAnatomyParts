import json
import statistics
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils.bvhtree import BVHTree


LOD_NAME = "LOD_Body"
RIG_PREFIX = "Rig_"
DEFAULT_REPORT = Path(bpy.path.abspath("//Result/lod_rig_offset_report.json"))


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    report_path = DEFAULT_REPORT
    if "--report" in argv:
        idx = argv.index("--report")
        if idx + 1 < len(argv):
            report_path = Path(argv[idx + 1])
    return report_path


def world_bvh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    bm.free()
    eval_obj.to_mesh_clear()
    return tree


def rig_mesh_objects():
    seen = set()
    result = []
    for coll in bpy.data.collections:
        if not coll.name.startswith(RIG_PREFIX):
            continue
        for obj in coll.all_objects:
            if obj.type != "MESH" or obj.name in seen:
                continue
            seen.add(obj.name)
            result.append((coll.name, obj))
    return result


def sample_signed_distances(obj, tree):
    world = obj.matrix_world
    signed = []
    for vert in obj.data.vertices:
        point = world @ vert.co
        nearest = tree.find_nearest(point)
        if nearest is None or nearest[0] is None or nearest[1] is None:
            continue
        nearest_co, normal, _index, distance = nearest
        direction = point - nearest_co
        sign = 1.0 if direction.dot(normal) >= 0.0 else -1.0
        signed.append(distance * sign)
    return signed


def summarize(values):
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return {}

    def pct(p):
        idx = min(count - 1, max(0, round((count - 1) * p)))
        return ordered[idx]

    positives = [v for v in ordered if v > 0.0]
    negatives = [v for v in ordered if v < 0.0]
    return {
        "count": count,
        "min_signed": ordered[0],
        "max_signed": ordered[-1],
        "mean_signed": statistics.fmean(ordered),
        "median_signed": pct(0.5),
        "p90_signed": pct(0.9),
        "p95_signed": pct(0.95),
        "outside_ratio": len(positives) / count,
        "inside_ratio": len(negatives) / count,
        "max_outside": max(positives) if positives else 0.0,
        "max_inside": min(negatives) if negatives else 0.0,
    }


def main():
    report_path = parse_args()
    lod_obj = bpy.data.objects.get(LOD_NAME)
    if lod_obj is None or lod_obj.type != "MESH":
        raise SystemExit(f"{LOD_NAME} mesh not found")

    tree = world_bvh(lod_obj)
    entries = []
    for collection_name, obj in rig_mesh_objects():
        signed = sample_signed_distances(obj, tree)
        stats = summarize(signed)
        if not stats:
            continue
        stats["collection"] = collection_name
        stats["object_name"] = obj.name
        entries.append(stats)

    entries.sort(key=lambda item: item["max_outside"], reverse=True)
    report = {
        "lod_object": LOD_NAME,
        "rig_object_count": len(entries),
        "top_outside": entries[:25],
        "top_inside": sorted(entries, key=lambda item: item["max_inside"])[:25],
        "by_collection": {},
    }

    for entry in entries:
        bucket = report["by_collection"].setdefault(entry["collection"], [])
        bucket.append(entry)

    for name, bucket in report["by_collection"].items():
        report["by_collection"][name] = {
            "object_count": len(bucket),
            "mean_outside_ratio": statistics.fmean(item["outside_ratio"] for item in bucket),
            "mean_inside_ratio": statistics.fmean(item["inside_ratio"] for item in bucket),
            "max_outside": max(item["max_outside"] for item in bucket),
            "max_inside": min(item["max_inside"] for item in bucket),
            "worst_outside_objects": sorted(bucket, key=lambda item: item["max_outside"], reverse=True)[:5],
            "worst_inside_objects": sorted(bucket, key=lambda item: item["max_inside"])[:5],
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
