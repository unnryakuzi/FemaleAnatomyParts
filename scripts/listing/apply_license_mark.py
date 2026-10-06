# -*- coding: utf-8 -*-
"""配布モデルに「2026-10 ライセンス版」の識別情報を埋め込む（書き出し前に同じ Blender セッションで流す）。

  blender -b <配布済み.blend> -P scripts/listing/apply_license_mark.py -P scripts/listing/export_dist.py -- male v1.2.1

- シーンに kabe_tech_license（文面）と kabe_tech_license_id を入れる
- MESH / EMPTY / ARMATURE の全オブジェクトに kt_license = MARK_ID を入れる
  → .blend はそのまま、.fbx は user property、.glb は node.extras / scene.extras に載る
  （export_dist.py は use_custom_props=True / export_extras=True で書き出す）
- .obj はカスタムプロパティを持てないので、書き出し後に stamp_obj_header() で先頭コメントを入れる

旧版（CC BY-SA 2.1 JP で配布した版）にはこの印が無い。印の有無で新旧を見分ける。
ファイルは保存しない（保存は export_dist.py の save_as_mainfile(copy=True) が行う）。
"""
MARK_ID = "KT-L2026-10"
MARK_TEXT = (
    "Kabe-Tech license 2026-10 (" + MARK_ID + "). "
    "Derived from BodyParts3D (c) The Database Center for Life Science, "
    "licensed under CC BY 4.0. Redistribution, resale or sharing of this model data "
    "(including modified versions) is prohibited. / "
    "本モデルは BodyParts3D（CC 表示 4.0 国際）を改変して作成。"
    "本モデルのデータそのもの（改変したものを含む）の再配布・転売・共有は禁止。"
)


def apply():
    import bpy  # stamp_glb.py から定数だけ読めるよう、bpy は関数内で読む
    n = 0
    for sc in bpy.data.scenes:
        sc["kabe_tech_license"] = MARK_TEXT
        sc["kabe_tech_license_id"] = MARK_ID
    for o in bpy.data.objects:
        if o.type in ("MESH", "EMPTY", "ARMATURE"):
            o["kt_license"] = MARK_ID
            n += 1
    print("[license_mark] %s を %d オブジェクトとシーン %d 個に付与" % (MARK_ID, n, len(bpy.data.scenes)))
    return n


if __name__ == "__main__":
    apply()
