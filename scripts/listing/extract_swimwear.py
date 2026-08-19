# -*- coding: utf-8 -*-
"""下着(Swimwear_Top/Bottom)を「静的メッシュ」として小さな .blend に抽出する。

出どころ: C:/Users/abesh/Documents/Blender/FemaleAnatomyTexture/3DAnatomyFemaleTexture.blend
  - Swimwear_Top / Swimwear_Bottom は 併用_Armature の子で ARMATURE モディファイア付き。
  - モディファイアを外すと A ポーズのレスト形状に戻り臀部が突き抜ける（HANDOFF_bikini.md 誤り②）。
    → **depsgraph の評価後メッシュ（＝ポーズ適用後の T ポーズ形状）** を焼き取る。
  - このファイルは Hips のポーズに Y -3.7m の平行移動が入っている。素体ごと抜いて
    XY 中心を原点へ寄せ、Z はそのまま（足元 ≈ -0.03）で正規化する。

同時に素体 `併用_Body(...)` も `Ref_Body` として抜く。後段の fit_swimwear.py が
「出どころの素体 → 出品モデルの体」の対応から下着の配置を決めるため、参照体が要る。

usage:
  blender -b "C:/Users/abesh/Documents/Blender/FemaleAnatomyTexture/3DAnatomyFemaleTexture.blend" \
          -P scripts/listing/extract_swimwear.py
出力: scripts/listing/swimwear_src.blend
"""
import bpy, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "swimwear_src.blend")

SRC = {
    "Swimwear_Top": "Swimwear_Top",
    "Swimwear_Bottom": "Swimwear_Bottom",
    "併用_Body(左=編集/右=コントロール)": "Ref_Body",
}
# HANDOFF_bikini.md の実測値。Principled Base Color（リニア）そのまま。
SWIM_RGBA = (0.045, 0.045, 0.05, 1.0)


def baked_copy(src_obj, new_name):
    """評価後（モディファイア・ポーズ適用後）メッシュをワールド座標で焼いた新オブジェクト。"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = src_obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    me.transform(src_obj.matrix_world)          # ワールドへ焼き込む
    me.name = new_name + "_mesh"
    ob = bpy.data.objects.new(new_name, me)     # matrix_world は単位行列
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bbox(ob):
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for v in ob.data.vertices:
        for i in range(3):
            mn[i] = min(mn[i], v.co[i]); mx[i] = max(mx[i], v.co[i])
    return mn, mx


def main():
    made = {}
    for src_name, new_name in SRC.items():
        o = bpy.data.objects.get(src_name)
        if not o:
            print(f"@@@ ERROR missing object {src_name!r}")
            sys.exit(1)
        # 元と同名だと Blender が自動で .001 を付ける。元を先に改名して名前を空ける
        # （このファイルは保存しないので改名は在メモリのみ）
        if o.name == new_name:
            o.name = new_name + "_ORIG"
        nb = baked_copy(o, new_name)
        assert nb.name == new_name, f"name collision: {nb.name}"
        made[new_name] = nb
        mn, mx = bbox(nb)
        print(f"@@@ BAKED {new_name} verts={len(nb.data.vertices)} "
              f"bbox=({mn.x:.4f},{mn.y:.4f},{mn.z:.4f})-({mx.x:.4f},{mx.y:.4f},{mx.z:.4f})")

    # 素体の XY 中心を原点へ（Y -3.7m のポーズ移動を除去）。Z は触らない。
    rmn, rmx = bbox(made["Ref_Body"])
    shift = Vector((-(rmn.x + rmx.x) / 2.0, -(rmn.y + rmx.y) / 2.0, 0.0))
    print(f"@@@ SHIFT ({shift.x:.4f},{shift.y:.4f},{shift.z:.4f})")
    for ob in made.values():
        ob.data.transform(__import__("mathutils").Matrix.Translation(shift))
        ob.data.update()

    # 下着に頂点カラーを焼く。Workbench の color_type='VERTEX' は
    # マテリアルではなくカラーアトリビュートを見るため、これが無いと白く写る。
    mat = bpy.data.materials.new("Swimwear_Mat_Static")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = SWIM_RGBA
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.85
    for name in ("Swimwear_Top", "Swimwear_Bottom"):
        ob = made[name]
        me = ob.data
        me.materials.clear()
        me.materials.append(mat)
        attr = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
        attr.data.foreach_set("color", list(SWIM_RGBA) * len(me.vertices))
        me.update()
        mn, mx = bbox(ob)
        print(f"@@@ FINAL {name} bbox=({mn.x:.4f},{mn.y:.4f},{mn.z:.4f})-({mx.x:.4f},{mx.y:.4f},{mx.z:.4f})")
    rmn, rmx = bbox(made["Ref_Body"])
    print(f"@@@ FINAL Ref_Body bbox=({rmn.x:.4f},{rmn.y:.4f},{rmn.z:.4f})-({rmx.x:.4f},{rmx.y:.4f},{rmx.z:.4f})")

    bpy.data.libraries.write(OUT, set(made.values()), fake_user=True, compress=True)
    print(f"@@@ WROTE {OUT} ({os.path.getsize(OUT)} bytes)")
    print("@@@ DONE")


if __name__ == "__main__":
    main()
