# v1.68.0: 女性マスターに、男性版にあって女性版に無かった筋39個＋骨間膜4枚（計43個）を足す
#   腕以外の37個 … Tポーズ版（3DAnatomyFemale_Tpose_final_20261014.blend、男性パーツを女性の形へ移して押し込み済み）から取る
#                   ※腕以外の共有パーツは マスター＝Tポーズ版 で頂点・matrix_world とも一致（大胸筋2部位だけ 1〜2mm 差）を確認済み
#   腕の6個     … Man_All から取り、matrix_world を同じ側の肩甲骨にそろえる（マスターの腕・手は Man_All の頂点そのまま＋肩甲骨フレーム）
# blender -b 3DAnatomyFemale.blend -P scripts/add_missing_43_v1_68.py -- <added.json> [--save]
import bpy, sys, os, json, numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
names = json.load(open(a[0], encoding="utf-8"))
SAVE = "--save" in a
P = os.path.dirname(bpy.data.filepath)
TPOSE = os.path.join(P, "3DAnatomyFemale_Tpose_final_20261014.blend")
MAN = os.path.join(P, "3DAnatomyman_Japanese_fbx", "Man_All.blend")
ARM = ("右前腕骨間膜", "左前腕骨間膜", "右手の虫様筋", "左手の虫様筋", "右掌側骨間筋", "左掌側骨間筋")
assert len(names) == 43 and not any(n in bpy.data.objects for n in names)
arm = [n for n in names if n.split("(")[0] in ARM]
rest = [n for n in names if n not in arm]
assert len(arm) == 6 and len(rest) == 37

# 入れ先コレクションは Tポーズ版と同じ（男性版の Rig_/深層筋_<部位> → 筋肉_<部位>、骨間膜は 骨格）
with bpy.data.libraries.load(TPOSE, link=False) as (src, dst):
    dst.objects = list(rest)   # 読み込み後、渡したリストの中身がオブジェクトに置き換わるのでコピーを渡す
with bpy.data.libraries.load(MAN, link=False) as (src2, dst2):
    dst2.objects = list(arm)
loaded = list(dst.objects) + list(dst2.objects)
assert all(o is not None for o in loaded), [o and o.name for o in loaded]
_d = set(rest + arm) ^ {o.name for o in loaded}
assert not _d, [ascii(x) for x in _d]

COLS = {  # Tポーズ版で入れたコレクション
    n: c for n, c in json.load(open(os.path.join(os.path.dirname(a[0]), "added_cols.json"), encoding="utf-8")).items()}

mat = bpy.data.materials["Anatomy_VertexColor"]
assert not mat.library
for o in loaded:
    for c in COLS[o.name]:
        bpy.data.collections[c].objects.link(o)
    me = o.data
    for i in range(len(me.materials)):
        me.materials[i] = mat
    if "restored_from_male" in o:
        del o["restored_from_male"]
    assert o.parent is None and len(o.modifiers) == 0, (o.name, o.parent, [m.type for m in o.modifiers])
    assert "Col" in me.attributes and all(k in o for k in ("name_ja", "name_kana", "name_en", "name_la")), o.name

for o in dst2.objects:
    side = o.name[0]
    scap = bpy.data.objects["右肩甲骨(みぎけんこうこつ)" if side == "右" else "左肩甲骨(ひだりけんこうこつ)"]
    o.matrix_world = scap.matrix_world.copy()

# 読み込みに付いてきた材質・余計なオブジェクトを掃除（付随の Armature 等が無いことも確かめる）
extra = [o for o in bpy.data.objects if not o.users_collection]
print("orphan objects:", [o.name for o in extra])
for o in extra:
    bpy.data.objects.remove(o, do_unlink=True)
for m in [m for m in bpy.data.materials if m.users == 0]:
    bpy.data.materials.remove(m)

bpy.context.view_layer.update()
for o in loaded:
    o.hide_set(False)
res = {}
for o in loaded:
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world); w = co @ M[:3, :3].T + M[:3, 3]
    res[o.name] = dict(nv=len(co), cen=w.mean(0).round(5).tolist(), cols=[c.name for c in o.users_collection],
                       mats=[m.name for m in o.data.materials], scale=round(o.matrix_world.to_scale()[0], 5))
json.dump(res, open(os.path.join(os.path.dirname(a[0]), "built.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("MESH", sum(o.type == 'MESH' for o in bpy.data.objects), "materials", sorted(m.name for m in bpy.data.materials))
if SAVE:
    bpy.ops.wm.save_mainfile()
    print("SAVED", bpy.data.filepath)
