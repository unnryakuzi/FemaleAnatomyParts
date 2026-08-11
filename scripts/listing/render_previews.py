# -*- coding: utf-8 -*-
"""
ヘッドレス（blender -b）でプレビュー画像を一括レンダーする。MCP/GUI不要。

使い方:
  blender -b 3DAnatomyFemale.blend            -P scripts/listing/render_previews.py -- female
  blender -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/listing/render_previews.py -- male
  （末尾に shot名の一部を足すと、そのショットだけ撮る: ... -- female 01_front）

要点:
  - bpy.ops.render.opengl ではなく Workbench を「レンダーエンジン」にして render.render()。
    → ウィンドウ無しでも動く。可視化は hide_render で制御（hide_get/viewportではない）。
  - 頂点カラーは scene.display.shading.color_type='VERTEX' で再現。
  - 背景は 0.72 グレーで出し、後段の normalize_and_thumbs.py で 184 に正規化する。
  - 出力は config.json の previews_dir / preview_order に従う。

環境変数:
  PREVIEW_OUT  出力先を上書き（試し撮り用）
  MANNEQUIN=1  マネキン調（無彩色）で撮る。頂点カラー(肌色)を使わず濃灰マット＋cavityで
               陰影を出す。BOOTHの年齢制限判定は商品ページの画像を見ているため、
               肌色のécorché＝「裸の人体」と読まれるのを避ける用途（2026-08-10）。
  AGESAFE=1    全年齢版の掲載画像を撮る。生殖器(13オブジェクト)を隠し、外皮ショット
               (07_skin＝肌色の全裸レンダー)を撮らない。MANNEQUIN=1 と併用する。
"""
import bpy, sys, os, json, math
from mathutils import Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
ROOT = CFG["root"]

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
MODEL = argv[0] if argv else "female"
SHOT_FILTER = argv[1] if len(argv) > 1 else None
MANNEQUIN = os.environ.get("MANNEQUIN") == "1"
AGESAFE = os.environ.get("AGESAFE") == "1"

# 可視化プリセット: shot_type -> 表示するコレクション名の集合（他は hide_render=True）
PRESETS = {
    "female": {
        "muscle":   {"骨格", "女性外皮", "筋肉", "歯", "靱帯・腱"},
        "skeleton": {"骨格", "歯"},
    },
    "male": {
        "muscle":   {"骨格", "表層筋", "深層筋", "歯", "靱帯・腱"},
        "skeleton": {"骨格", "歯"},
        "organs":   {"臓器"},
        "vessels":  {"血管", "脳・神経"},
        "skin":     {"外皮"},
    },
}
ALWAYS_HIDE = {"_RenderSetup", "_ガイドライン"}
# AGESAFE=1 のとき追加で隠すコレクション。SHOW側のコレクションに入れ子で入っていても
# 名前で引いて差し引くので確実に消える（男性の生殖器は13オブジェクト）。
AGESAFE_HIDE = {"生殖器"}
# AGESAFE=1 で撮らないショット preset（外皮＝全裸の肌色レンダー。全年齢版では出せない）
AGESAFE_DROP_PRESETS = {"skin"}

# ショット定義: 出力ファイル名 -> (preset, camera, closeup_target)
# camera: front / front34 / back。closeup_target: None=全身, 'torso'/'forearm'=寄り
SHOTS = {
    "female": [
        ("01_front.png",          "muscle",   "front",   None),
        ("02_front34.png",        "muscle",   "front34", None),
        ("03_back.png",           "muscle",   "back",    None),
        ("04_skeleton_front.png", "skeleton", "front",   None),
        ("05_torso_closeup.png",  "muscle",   "front",   "torso"),
        ("06_forearm_tendon.png", "muscle",   "front",   "forearm"),
    ],
    "male": [
        ("01_muscle_front.png",   "muscle",   "front",   None),
        ("02_muscle_front34.png", "muscle",   "front34", None),
        ("03_muscle_back.png",    "muscle",   "back",    None),
        ("04_skeleton_front.png", "skeleton", "front",   None),
        ("05_organs.png",         "organs",   "front",   None),
        ("06_vessels_nerves.png", "vessels",  "front",   None),
        ("07_skin.png",           "skin",     "front",   None),
        ("08_torso_closeup.png",  "muscle",   "front",   "torso"),
    ],
}
# closeup対象のコレクション（前腕など）。無ければ全身bboxの一部で代用。
FOREARM_COL = {"female": "筋肉_右前腕", "male": "Rig_右前腕"}

QUAT_FRONT = Quaternion((0.70710678, 0.70710678, 0.0, 0.0))
QUAT_BACK  = Quaternion((0.0, 0.0, 0.70710678, 0.70710678))
def quat_for(cam):
    if cam == "front":   return QUAT_FRONT.copy()
    if cam == "back":    return QUAT_BACK.copy()
    if cam == "front34": return Quaternion((0,0,1), math.radians(-35)) @ QUAT_FRONT
    raise ValueError(cam)


def collection_map(scene):
    m = {}
    for c in bpy.data.collections:
        m[c.name] = c
    return m


def set_visibility(scene, show_cols):
    cmap = collection_map(scene)
    show_objs = set()
    for cn in show_cols:
        c = cmap.get(cn)
        if c:
            for o in c.all_objects:
                # MESH以外は写さない（例: 筋肉コレクション内のデバッグカーブ
                # CURRENT_左広頚筋接触ライン が黄色い線として写り込んだ 2026-07-13）
                if o.type == 'MESH':
                    show_objs.add(o.name)
    if AGESAFE:
        hidden = set()
        for cn in AGESAFE_HIDE:
            c = cmap.get(cn)
            if c:
                hidden |= {o.name for o in c.all_objects if o.type == 'MESH'}
        if hidden:
            show_objs -= hidden
        print(f"  AGESAFE: hid {len(hidden)} objects from {sorted(AGESAFE_HIDE)}")
    for o in scene.objects:
        o.hide_render = o.name not in show_objs
    return show_objs


def visible_bbox(scene, names):
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for n in names:
        o = scene.objects.get(n)
        if not o or o.type != 'MESH':
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    return mn, mx


def col_bbox(scene, colname):
    cmap = collection_map(scene)
    c = cmap.get(colname)
    if not c:
        return None
    names = [o.name for o in c.all_objects if o.type == 'MESH']
    if not names:
        return None
    return visible_bbox(scene, names)


def place_camera(scene, cam_obj, center, ortho_scale, quat):
    cam_obj.data.type = 'ORTHO'
    cam_obj.data.sensor_fit = 'VERTICAL'
    cam_obj.data.ortho_scale = ortho_scale
    cam_obj.rotation_mode = 'QUATERNION'
    cam_obj.rotation_quaternion = quat
    forward = quat @ Vector((0, 0, -1))
    dist = ortho_scale * 4 + 5
    cam_obj.location = center - forward * dist
    cam_obj.data.clip_start = 0.01
    cam_obj.data.clip_end = dist * 2 + 50


def main():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True  # 背景は出さず透過。後段で184に合成（色管理差を回避）
    scene.view_settings.view_transform = 'Standard'  # 頂点カラーを素直に＆男女でトーン統一
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'SINGLE' if MANNEQUIN else 'VERTEX'
    sh.show_xray = False
    sh.show_object_outline = False
    sh.show_shadows = False
    sh.background_type = 'VIEWPORT'
    sh.background_color = (0.72, 0.72, 0.72)
    if MANNEQUIN:
        # 単色にすると筋の走行が陰影だけになるので cavity で凹凸を立てる（無いと構造が読めない）
        sh.single_color = (0.16, 0.16, 0.17)
        sh.show_shadows = True
        sh.shadow_intensity = 0.4
        sh.show_cavity = True
        sh.cavity_type = 'BOTH'
        sh.curvature_ridge_factor = 1.2
        sh.curvature_valley_factor = 1.2

    cam_data = bpy.data.cameras.new("HeadlessCam")
    cam_obj = bpy.data.objects.new("HeadlessCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    out_dir = os.environ.get("PREVIEW_OUT") or os.path.join(ROOT, CFG[MODEL]["previews_dir"])
    os.makedirs(out_dir, exist_ok=True)

    for fname, preset, cam, closeup in SHOTS[MODEL]:
        if SHOT_FILTER and SHOT_FILTER not in fname:
            continue
        if AGESAFE and preset in AGESAFE_DROP_PRESETS:
            print(f"SKIPPED {fname} (AGESAFE: preset={preset})")
            continue
        show_cols = PRESETS[MODEL][preset]
        names = set_visibility(scene, show_cols)
        mn, mx = visible_bbox(scene, names)
        dims = mx - mn
        center = (mn + mx) / 2.0
        quat = quat_for(cam)

        if closeup == "torso":
            # 上半身に寄る: 中心を胸あたりへ、高さを縮める
            top = mx.z
            center = Vector((center.x, center.y, top - dims.z * 0.30))
            ortho = dims.z * 0.42
            scene.render.resolution_x = 1100; scene.render.resolution_y = 1300
        elif closeup == "forearm":
            bb = col_bbox(scene, FOREARM_COL[MODEL])
            if bb:
                fmn, fmx = bb
                center = (fmn + fmx) / 2.0       # 前腕＋手のbbox中心に寄せる
                fd = fmx - fmn
                ortho = max(fd.z, fd.x) * 1.15   # 前腕が縦いっぱい＝中央に大きく（胴体は枠外へ）
                # 前腕は胴体寄りなので、カメラを腕側(外側)へ少し振って前腕を画面中央に＝胴体を枠外へ
                horiz_half = ortho * (1100/1300) / 2.0
                center = Vector((center.x + (-0.30 if center.x < 0 else 0.30) * horiz_half, center.y, center.z))
            else:
                ortho = dims.z * 0.35
            scene.render.resolution_x = 1100; scene.render.resolution_y = 1300
        else:
            ortho = dims.z * 1.10  # 全身が縦約91%。旧1.30(縦77%)は「モデルが小さい」指摘で変更(2026-07-13)
            scene.render.resolution_x = 1000; scene.render.resolution_y = 1400

        place_camera(scene, cam_obj, center, ortho, quat)
        scene.render.filepath = os.path.join(out_dir, fname)
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED {fname}  preset={preset} cam={cam} closeup={closeup} ortho={ortho:.3f} center=({center.x:.2f},{center.y:.2f},{center.z:.2f})")

    print("ALL DONE", MODEL)


if __name__ == "__main__":
    main()
