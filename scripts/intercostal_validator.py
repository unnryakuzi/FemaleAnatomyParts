bl_info = {
    "name": "Intercostal Validator",
    "author": "Claude",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Anatomy",
    "description": "肋間筋ペアのはがれ自動検査・DIAGマーカー配置",
    "category": "Object",
}

import bpy
import bmesh
import math
import statistics
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SAI_PREFIX = "最内肋間筋"
GAI_PREFIX = "外肋間筋"
MARKER_COLL = "_DIAG_突抜マーカー"
MARKER_NAME_PREFIX = "DIAG_AUTO_"


def find_intercostal_objs():
    sais, gais = [], []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if "DIAG" in o.name:
            continue
        if o.name.startswith(SAI_PREFIX):
            sais.append(o)
        elif o.name.startswith(GAI_PREFIX):
            gais.append(o)
    return sais, gais


def world_bbox_center(o):
    bb = [o.matrix_world @ Vector(b) for b in o.bound_box]
    cx = sum(v.x for v in bb) / 8
    cy = sum(v.y for v in bb) / 8
    cz = sum(v.z for v in bb) / 8
    return Vector((cx, cy, cz))


def pair_sai_to_gai(sais, gais):
    gai_centers = [(g, world_bbox_center(g)) for g in gais]
    pairs = []
    for s in sais:
        sc = world_bbox_center(s)
        best = min(gai_centers, key=lambda gc: (gc[1] - sc).length)
        pairs.append((s, best[0], (best[1] - sc).length))
    return pairs


def build_bvh(obj, depsgraph):
    ev = obj.evaluated_get(depsgraph)
    bm = bmesh.new()
    bm.from_mesh(ev.data)
    bm.transform(obj.matrix_world)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def get_marker_collection():
    coll = bpy.data.collections.get(MARKER_COLL)
    if coll is None:
        coll = bpy.data.collections.new(MARKER_COLL)
        bpy.context.scene.collection.children.link(coll)
    return coll


def clear_auto_markers():
    removed = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(MARKER_NAME_PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
            removed += 1
    return removed


def cluster_points(points, radius=0.015):
    """単純な貪欲クラスタリング: radius以内の点を1クラスタにまとめる"""
    clusters = []
    used = [False] * len(points)
    for i, p in enumerate(points):
        if used[i]:
            continue
        cluster = [p]
        used[i] = True
        for j in range(i + 1, len(points)):
            if used[j]:
                continue
            if (points[j] - p).length < radius:
                cluster.append(points[j])
                used[j] = True
        clusters.append(cluster)
    return clusters


def measure_pair(sai, gai, depsgraph, threshold=0.005):
    bvh = build_bvh(gai, depsgraph)
    mw = sai.matrix_world
    problem_points = []
    all_dists = []
    for v in sai.data.vertices:
        pw = mw @ v.co
        loc, n, fi, d = bvh.find_nearest(pw)
        if d is None:
            continue
        all_dists.append(d)
        if d > threshold:
            problem_points.append(pw)
    return all_dists, problem_points


class INTERCOSTAL_OT_scan_all(bpy.types.Operator):
    bl_idname = "intercostal.scan_all"
    bl_label = "全ペアスキャン"
    bl_description = "全肋間筋ペアを検査してDIAGマーカーを自動配置"

    threshold_mm: bpy.props.FloatProperty(name="閾値(mm)", default=5.0, min=0.1, max=50.0)
    cluster_radius_mm: bpy.props.FloatProperty(name="クラスタ半径(mm)", default=15.0, min=1.0, max=100.0)
    min_cluster_size: bpy.props.IntProperty(name="最小頂点数", default=10, min=1)
    clear_first: bpy.props.BoolProperty(name="既存AUTOマーカーを削除", default=True)

    def execute(self, context):
        if self.clear_first:
            n = clear_auto_markers()
            self.report({"INFO"}, f"既存AUTOマーカー {n}個削除")

        sais, gais = find_intercostal_objs()
        if not sais or not gais:
            self.report({"ERROR"}, f"sai={len(sais)}, gai={len(gais)} - 対象不足")
            return {"CANCELLED"}

        pairs = pair_sai_to_gai(sais, gais)
        depsgraph = context.evaluated_depsgraph_get()
        coll = get_marker_collection()
        threshold = self.threshold_mm / 1000.0
        cluster_r = self.cluster_radius_mm / 1000.0

        problem_pairs = 0
        markers_placed = 0
        report_lines = []

        for sai, gai, _ in pairs:
            dists, problems = measure_pair(sai, gai, depsgraph, threshold)
            if not problems:
                continue
            clusters = cluster_points(problems, radius=cluster_r)
            clusters = [c for c in clusters if len(c) >= self.min_cluster_size]
            if not clusters:
                continue
            problem_pairs += 1
            mean_d = statistics.mean(dists) * 1000
            max_d = max(dists) * 1000
            report_lines.append(
                f"{sai.name[-6:]} <-> {gai.name[-6:]}: "
                f"problems={len(problems)}, clusters={len(clusters)}, "
                f"mean={mean_d:.2f}mm, max={max_d:.2f}mm"
            )
            for ci, cluster in enumerate(clusters):
                cx = sum(p.x for p in cluster) / len(cluster)
                cy = sum(p.y for p in cluster) / len(cluster)
                cz = sum(p.z for p in cluster) / len(cluster)
                marker = bpy.data.objects.new(
                    name=f"{MARKER_NAME_PREFIX}{sai.name[-3:]}_{ci:02d}",
                    object_data=None,
                )
                marker.empty_display_type = "SPHERE"
                marker.empty_display_size = 0.005
                marker.location = (cx, cy, cz)
                coll.objects.link(marker)
                markers_placed += 1

        msg = f"スキャン完了: {problem_pairs}ペアではがれ検出、マーカー{markers_placed}個配置"
        self.report({"INFO"}, msg)
        for line in report_lines:
            print(f"  {line}")
        print(msg)
        return {"FINISHED"}


class INTERCOSTAL_OT_clear_markers(bpy.types.Operator):
    bl_idname = "intercostal.clear_markers"
    bl_label = "AUTOマーカー全削除"
    bl_description = "DIAG_AUTO_*マーカーを全削除"

    def execute(self, context):
        n = clear_auto_markers()
        self.report({"INFO"}, f"{n}個削除")
        return {"FINISHED"}


class INTERCOSTAL_OT_inspect_active(bpy.types.Operator):
    bl_idname = "intercostal.inspect_active"
    bl_label = "選択ペア詳細"
    bl_description = "アクティブな最内肋間筋について対応外肋への距離分布を出力"

    def execute(self, context):
        sai = context.active_object
        if sai is None or not sai.name.startswith(SAI_PREFIX):
            self.report({"ERROR"}, "最内肋間筋を選択してください")
            return {"CANCELLED"}
        _, gais = find_intercostal_objs()
        if not gais:
            return {"CANCELLED"}
        sc = world_bbox_center(sai)
        gai = min(gais, key=lambda g: (world_bbox_center(g) - sc).length)
        depsgraph = context.evaluated_depsgraph_get()
        dists, problems = measure_pair(sai, gai, depsgraph, threshold=0.005)
        if not dists:
            return {"CANCELLED"}
        msg = (
            f"{sai.name} <-> {gai.name}: "
            f"n={len(dists)}, mean={statistics.mean(dists)*1000:.2f}mm, "
            f"median={statistics.median(dists)*1000:.2f}mm, "
            f"max={max(dists)*1000:.2f}mm, "
            f">3mm={100*sum(1 for d in dists if d>0.003)/len(dists):.1f}%, "
            f">5mm={100*sum(1 for d in dists if d>0.005)/len(dists):.1f}%"
        )
        self.report({"INFO"}, msg)
        print(msg)
        return {"FINISHED"}


class INTERCOSTAL_PT_panel(bpy.types.Panel):
    bl_label = "肋間筋検査"
    bl_idname = "INTERCOSTAL_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anatomy"

    def draw(self, context):
        layout = self.layout
        layout.operator("intercostal.scan_all", icon="VIEWZOOM")
        layout.operator("intercostal.inspect_active", icon="INFO")
        layout.separator()
        layout.operator("intercostal.clear_markers", icon="TRASH")


CLASSES = (
    INTERCOSTAL_OT_scan_all,
    INTERCOSTAL_OT_clear_markers,
    INTERCOSTAL_OT_inspect_active,
    INTERCOSTAL_PT_panel,
)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
