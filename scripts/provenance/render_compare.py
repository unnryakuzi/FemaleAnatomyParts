# -*- coding: utf-8 -*-
"""製品メッシュと BodyParts3D v4.0 メッシュを Blender 上で並べて撮る。

  blender -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/provenance/render_compare.py

各パーツについて3枚:
  <part>_1_product.png  製品のみ（灰）
  <part>_2_bp3d.png     BP3D のみ（灰）  ※同一カメラなので形の違いがそのまま見える
  <part>_3_overlay.png  重ね（製品=灰 / BP3D=赤）。赤が見える＝BP3Dが製品より外側

位置合わせは bbox 中心＋最大辺スケール＋軸並べ替え24通りの総当たりで最良を選ぶ。
（製品側は常に無加工。BP3D 側だけを動かす）
"""
import itertools
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OBJ_ISA = os.path.join(ROOT, "refs", "BodyParts3D_v4.0", "obj_isa",
                       "isa_BP3D_4.0_obj_99")
OUT = os.path.join(ROOT, "refs", "BodyParts3D_v4.0", "compare")

# 製品オブジェクト名 -> BP3D の OBJ ファイル
TARGETS = [
    ("下顎骨(かがくこつ)", "mandible"),
    ("右上腕骨(みぎじょうわんこつ)", "right humerus"),
    ("右肩甲骨(みぎけんこうこつ)", "right scapula"),
    ("右大胸筋胸肋部(みぎだいきょうきんきょうろくぶ)", "sternocostal part of right pectoralis major"),
    ("右小胸筋(みぎしょうきょうきん)", "right pectoralis minor"),
    ("右腓腹筋外側頭(みぎひふくきんがいそくとう)", "lateral head of right gastrocnemius"),
]

RES = (1100, 900)


def build_bp3d_lookup():
    """OBJ ヘッダの English name -> ファイルパス"""
    m = {}
    for fn in os.listdir(OBJ_ISA):
        if not fn.endswith(".obj"):
            continue
        p = os.path.join(OBJ_ISA, fn)
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.startswith("#"):
                    break
                if "English name" in line:
                    m[line.split(":", 1)[1].strip().lower()] = p
                    break
    return m


def world_pts(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def bbox(pts):
    lo = Vector((min(p[i] for p in pts) for i in range(3)))
    hi = Vector((max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def import_obj(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o not in before]
    if len(new) > 1:                       # 念のため統合
        for o in new[1:]:
            bpy.data.objects.remove(o, do_unlink=True)
        new = new[:1]
    return new[0]


def fit_axes(src_ob, dst_pts):
    """src_ob(BP3D) を dst(製品) へ: 24通りの軸並べ替え×符号から最良を選ぶ。"""
    sp = world_pts(src_ob)
    slo, shi = bbox(sp)
    dlo, dhi = bbox(dst_pts)
    dc = (dlo + dhi) / 2
    dsize = max(dhi[i] - dlo[i] for i in range(3))

    # 比較用に間引いた点群
    ds = dst_pts[::max(1, len(dst_pts) // 3000)]

    best = None
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            if perm == (0, 1, 2) and signs == (1, 1, 1):
                pass
            # 並べ替え後の bbox
            plo = [0] * 3
            phi = [0] * 3
            for j in range(3):
                a, b = slo[perm[j]] * signs[j], shi[perm[j]] * signs[j]
                plo[j], phi[j] = min(a, b), max(a, b)
            ssize = max(phi[j] - plo[j] for j in range(3))
            if ssize <= 0:
                continue
            k = dsize / ssize
            pc = [(plo[j] + phi[j]) / 2 for j in range(3)]
            # サンプル点で残差
            err = 0.0
            step = max(1, len(sp) // 800)
            for p in sp[::step]:
                q = Vector(tuple(k * (p[perm[j]] * signs[j] - pc[j]) + dc[j]
                                 for j in range(3)))
                # dst 側の最近点は重いので bbox の詰まり具合で代用せず、粗い最近傍
                err += min((q - r).length_squared for r in ds[::7])
            if best is None or err < best[0]:
                best = (err, perm, signs, k, pc)

    _, perm, signs, k, pc = best
    M = Matrix()
    for j in range(3):
        row = [0.0, 0.0, 0.0]
        row[perm[j]] = k * signs[j]
        M[j][0], M[j][1], M[j][2] = row
        M[j][3] = dc[j] - k * pc[j]
    src_ob.matrix_world = M @ src_ob.matrix_world
    return perm, signs, k


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    d = sc.display.shading
    d.light = 'STUDIO'
    d.color_type = 'OBJECT'
    d.show_cavity = True
    d.show_object_outline = False
    sc.display.render_aa = '8'
    sc.world.color = (0.72, 0.72, 0.72) if sc.world else None
    for ob in bpy.data.objects:
        ob.hide_render = True


def make_camera():
    cam_data = bpy.data.cameras.new("CMP_Cam")
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new("CMP_Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def aim(cam, center, size, view):
    """view: 'front'(-Y から) / 'side'(+X から) / 'top'(+Z から)"""
    d = size * 3
    if view == "front":
        cam.location = center + Vector((0, -d, 0))
        cam.rotation_euler = (math.radians(90), 0, 0)
    elif view == "side":
        cam.location = center + Vector((d, 0, 0))
        cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    else:
        cam.location = center + Vector((0, 0, d))
        cam.rotation_euler = (0, 0, 0)
    cam.data.ortho_scale = size * 1.25


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    lookup = build_bp3d_lookup()
    setup_scene()
    cam = make_camera()

    GREY = (0.78, 0.78, 0.78, 1.0)
    RED = (0.85, 0.12, 0.10, 1.0)

    for pname, en in TARGETS:
        prod = bpy.data.objects.get(pname)
        if prod is None:
            print("!! 製品オブジェクトが見つからない:", pname)
            continue
        path = lookup.get(en.lower())
        if path is None:
            print("!! BP3D に該当なし:", en)
            continue

        bp = import_obj(path)
        bp.name = "BP3D_" + os.path.basename(path)
        dst = world_pts(prod)
        perm, signs, k = fit_axes(bp, dst)

        lo, hi = bbox(dst)
        center = (lo + hi) / 2
        size = max(hi[i] - lo[i] for i in range(3))
        prod.color = GREY
        bp.color = RED
        tag = en.replace(" ", "_")[:40]
        print("--- %s  軸=%s%s scale=%.4f" % (pname, perm, signs, k))

        for view in ("front", "side"):
            aim(cam, center, size, view)
            prod.hide_render = False
            bp.hide_render = True
            render(os.path.join(OUT, "%s_%s_1_product.png" % (tag, view)))
            prod.hide_render = True
            bp.hide_render = False
            bp.color = GREY
            render(os.path.join(OUT, "%s_%s_2_bp3d.png" % (tag, view)))
            bp.color = RED
            prod.hide_render = False
            render(os.path.join(OUT, "%s_%s_3_overlay.png" % (tag, view)))
            prod.hide_render = True
            bp.hide_render = True

        bpy.data.objects.remove(bp, do_unlink=True)

    print("\n出力先:", OUT)


main()
