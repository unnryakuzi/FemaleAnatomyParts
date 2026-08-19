# -*- coding: utf-8 -*-
"""配布用 4形式(blend/fbx/glb/obj)の書き出し。MCP/GUI 不要のヘッドレス版。

  blender -b <master.blend> -P scripts/listing/export_dist.py -- <female|male> <version> [options]

例:
  blender -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/listing/export_dist.py -- male v1.2.0

version は素の "v1.2.0" を渡す。出力先ディレクトリ名（男性だけ Man_ が付く）と
ファイル名の規則は既存パッケージに合わせて自動で組み立てる:
  male   -> 配布パッケージ_Man_v1.2.0/models/MaleAnatomy_v1.2.0.{blend,fbx,glb,obj}
  female -> 配布パッケージ_v1.67.0/models/FemaleAnatomy_v1.67.0.{...}

options:
  --outdir DIR     出力先（既定 <root>/配布パッケージ_<version>/models）
  --formats LIST   blend,fbx,glb,obj のカンマ区切り（既定は全部）

★設定の根拠（2026-08-19 に配布済み v1.1.0 / v1.67.0 の成果物を実測して確定）:
  - 可視フィルタは掛けない。v1.1.0.glb は 937 ノード＝全 MESH。
    use_visible / use_renderable は False。
  - それでも非表示のままだとエクスポータが黙って落とす。書き出し前に全解除する
    （.blend コピーは解除前に取るので購入者が開いたときの表示状態は元のまま）:
      hide_viewport(モニタ) = depsgraph から外れ fbx/glb/obj すべてで欠落
      hide_get(目)          = wm.obj_export だけが落とす（fbx/glb は残る）
    ※実際 v1.2.0 の初回書き出しで .obj だけ 937 になり、glb 939 と食い違った。
  - MESH のみ。v1.1.0.glb は cameras 0 / lights 0（glTF 既定）。FBX も MESH に揃える。
  - 頂点カラーが色の実体（UV 無し・マテリアルは Anatomy_VertexColor 1個）。
    glb=COLOR_0 / fbx=LayerElementColor(SRGB) / obj=v 行末尾 RGB(export_colors=True)。
  - obj の .mtl は Kd に筋の代表色が入る＝頂点カラー非対応ビューア用フォールバック。
"""
import bpy
import json
import os
import struct
import sys
import time

ROOT = r"C:\Users\abesh\Documents\Blender\MaleAnatomy"


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(argv) < 2:
        raise SystemExit("usage: -- <female|male> <version> [--outdir DIR] [--formats blend,fbx,glb,obj]")
    model, version = argv[0], argv[1]
    outdir, formats = None, ["blend", "fbx", "glb", "obj"]
    i = 2
    while i < len(argv):
        if argv[i] == "--outdir":
            outdir = argv[i + 1]
            i += 2
        elif argv[i] == "--formats":
            formats = [x.strip() for x in argv[i + 1].split(",") if x.strip()]
            i += 2
        else:
            raise SystemExit("unknown option: " + argv[i])
    # 既存パッケージの命名規則: ディレクトリは男性だけ Man_ が付き、ファイル名には付かない
    dirtag = ("Man_" + version) if model == "male" else version
    if outdir is None:
        outdir = os.path.join(ROOT, "配布パッケージ_" + dirtag, "models")
    prefix = {"female": "FemaleAnatomy_", "male": "MaleAnatomy_"}[model]
    return model, version, outdir, formats, prefix + version


def unhide_for_export():
    """非表示を全解除。解除しないと形式ごとにバラバラに欠落する。

    実測(2026-08-19):
      hide_viewport(モニタ) = depsgraph から外れ、fbx/glb/obj すべてで欠落
      hide_get(目)          = wm.obj_export だけが落とす。fbx/glb は use_visible=False
                              なら残る。→ .obj だけパーツ数が減る事故になる
    """
    n = 0
    for o in bpy.context.scene.objects:
        if o.hide_viewport:
            o.hide_viewport = False
            n += 1
        if o.hide_get():
            o.hide_set(False)
            n += 1
    for lc in bpy.context.view_layer.layer_collection.children:
        if lc.hide_viewport or lc.exclude:
            lc.hide_viewport = False
            lc.exclude = False
            n += 1
    bpy.context.view_layer.update()
    return n


def select_meshes():
    bpy.ops.object.select_all(action="DESELECT")
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    return meshes


def main():
    model, version, outdir, formats, stem = parse_args()
    os.makedirs(outdir, exist_ok=True)
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    print("[export_dist] model=%s version=%s outdir=%s" % (model, version, outdir))

    # 1) .blend は「表示状態を触る前」に保存する（購入者が開いたときの見え方を保つ）
    if "blend" in formats:
        p = os.path.join(outdir, stem + ".blend")
        t = time.time()
        # compress=True 必須。マスターも配布済み v1.1.0 も zstd 圧縮(先頭 28 B5 2F FD)で、
        # 非圧縮にすると 644MB -> 1.89GB に膨らむ。
        bpy.ops.wm.save_as_mainfile(filepath=p, copy=True, compress=True)
        print("[blend] %s  %.1f MB  %.0fs" % (p, os.path.getsize(p) / 1e6, time.time() - t))

    # 2) ここから先はメッシュ形式。depsgraph から落ちないよう可視化してから書き出す
    n = unhide_for_export()
    meshes = select_meshes()
    print("[export_dist] hide_viewport 解除 %d 件 / MESH %d 個を書き出し対象に" % (n, len(meshes)))

    if "fbx" in formats:
        p = os.path.join(outdir, stem + ".fbx")
        t = time.time()
        bpy.ops.export_scene.fbx(
            filepath=p,
            use_selection=False,
            use_visible=False,
            object_types={"MESH"},
            use_mesh_modifiers=True,
            mesh_smooth_type="FACE",
            colors_type="SRGB",       # 頂点カラーを保持
            use_custom_props=True,    # 3言語ラベル等のカスタムプロパティを user property へ
            add_leaf_bones=False,
            bake_space_transform=False,
            axis_forward="-Z",
            axis_up="Y",
            path_mode="AUTO",
        )
        print("[fbx] %s  %.1f MB  %.0fs" % (p, os.path.getsize(p) / 1e6, time.time() - t))

    if "glb" in formats:
        p = os.path.join(outdir, stem + ".glb")
        t = time.time()
        bpy.ops.export_scene.gltf(
            filepath=p,
            export_format="GLB",
            use_selection=False,
            use_visible=False,
            use_renderable=False,
            use_active_collection=False,
            export_extras=True,       # カスタムプロパティを node.extras へ
            export_cameras=False,
            export_lights=False,
            export_animations=False,
            export_apply=False,       # モディファイアは 0 個なので不要（シェイプキー保護）
            export_yup=True,
        )
        print("[glb] %s  %.1f MB  %.0fs" % (p, os.path.getsize(p) / 1e6, time.time() - t))

    if "obj" in formats:
        p = os.path.join(outdir, stem + ".obj")
        t = time.time()
        bpy.ops.wm.obj_export(
            filepath=p,
            export_selected_objects=False,
            apply_modifiers=True,
            export_normals=True,
            export_uv=True,           # UV は無いので vt 行は出ない
            export_materials=True,
            export_colors=True,       # ★既定 False。v 行末尾に RGB を出すのに必須
            export_triangulated_mesh=False,
            export_object_groups=False,
            export_material_groups=False,
            forward_axis="NEGATIVE_Z",
            up_axis="Y",
            global_scale=1.0,
            path_mode="AUTO",
        )
        print("[obj] %s  %.1f MB  %.0fs" % (p, os.path.getsize(p) / 1e6, time.time() - t))

    verify(outdir, stem, formats, len(meshes))


def verify(outdir, stem, formats, expect):
    """書き出した実物を読み直して数と色を確認する（サイズだけ見て済ませない）。

    途中で assert 中断すると後続形式が検査されないので、問題は貯めて最後に出す。
    """
    print("[verify] 期待パーツ数 = %d" % expect)
    bad = []

    def check(cond, msg):
        if not cond:
            bad.append(msg)
            print("[verify] NG: " + msg)

    if "glb" in formats:
        p = os.path.join(outdir, stem + ".glb")
        with open(p, "rb") as f:
            f.read(12)
            ln, _ = struct.unpack("<II", f.read(8))
            j = json.loads(f.read(ln))
        nodes = j.get("nodes", [])
        attrs = j["meshes"][0]["primitives"][0]["attributes"]
        n_lab = sum(1 for n in nodes if "name_ja" in n.get("extras", {}))
        print("[verify][glb] nodes=%d meshes=%d materials=%d COLOR_0=%s name_ja=%d"
              % (len(nodes), len(j.get("meshes", [])), len(j.get("materials", [])),
                 "COLOR_0" in attrs, n_lab))
        check(len(nodes) == expect, "glb ノード数 %d != %d" % (len(nodes), expect))
        check("COLOR_0" in attrs, "glb に頂点カラーが無い")
        check(n_lab > 0, "glb にラベル(name_ja)が無い")
    if "obj" in formats:
        p = os.path.join(outdir, stem + ".obj")
        o_cnt = 0
        rgb_ok = False
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("o "):
                    o_cnt += 1
                elif not rgb_ok and line.startswith("v "):
                    rgb_ok = len(line.split()) == 7   # x y z r g b
        print("[verify][obj] o行=%d 頂点RGB=%s" % (o_cnt, rgb_ok))
        check(o_cnt == expect, "obj オブジェクト数 %d != %d" % (o_cnt, expect))
        check(rgb_ok, "obj の v 行に頂点カラーが無い（export_colors）")
    if "fbx" in formats:
        p = os.path.join(outdir, stem + ".fbx")
        data = open(p, "rb").read()
        n_model = data.count(b"Model::")
        n_col = data.count(b"LayerElementColor")
        n_lab = data.count(b"name_ja")
        print("[verify][fbx] %.1f MB Model::=%d LayerElementColor=%d name_ja=%d"
              % (os.path.getsize(p) / 1e6, n_model, n_col, n_lab))
        check(n_col > 0, "fbx に頂点カラーレイヤーが無い")
        check(n_lab > 0, "fbx にラベル(name_ja)が無い")
        del data

    if bad:
        raise SystemExit("[verify] 失敗 %d 件: %s" % (len(bad), " / ".join(bad)))
    print("[verify] OK")


main()
