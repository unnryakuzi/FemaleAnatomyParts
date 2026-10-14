# v1.68.0 の仕上げ: 多裂筋の作り直しを書き込み、踵骨腱を 靱帯・腱 へ移し、bump_version する
# blender -b 3DAnatomyFemale.blend -P finalize_v1_68.py -- <multifidus_new_all.npz>
import bpy, sys, numpy as np
sys.path.insert(0, r"C:\Users\abesh\.claude\skills\blender-anatomy-mesh\scripts")
from snapshot import bump_version
NPZ = sys.argv[sys.argv.index("--") + 1]
X = np.load(NPZ)
for k in ("右多裂筋", "左多裂筋"):
    o = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.split("(")[0] == k)
    w = X[k].astype(np.float64); assert len(w) == len(o.data.vertices)
    Mi = np.array(o.matrix_world.inverted(), np.float64)
    o.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
    print("SET", o.name)
bone, lig = bpy.data.collections["骨格"], bpy.data.collections["靱帯・腱"]
for o in [o for o in bone.objects if "踵骨腱" in o.name]:
    lig.objects.link(o); bone.objects.unlink(o); print("MOVED", o.name)
assert sum(o.type == 'MESH' for o in bpy.data.objects) == 718
bump_version('minor', '欠けていた筋39個と骨間膜4枚を男性版から追加（腹直筋・内腹斜筋・腹横筋・錐体筋・大小菱形筋・肩甲挙筋・鎖骨下筋・下後鋸筋・胸腸肋筋・頭頚の半棘筋/回旋筋/最長筋/後頭直筋/横突間筋/棘間筋・手の虫様筋/掌側骨間筋・前腕/下腿の骨間膜）。'
             '腕以外の37個は 3DAnatomyFemale_Tpose_final_20261014.blend（男性パーツを周りの変形で女性へ移し、覆う筋の内側へ押し込み済み）から、'
             '腕の6個は Man_All から取り同側肩甲骨フレームへ（scripts/add_missing_43_v1_68.py）。'
             '多裂筋（左右）の上端が頭蓋の下まで約8cm伸びていたのを、男性の多裂筋を周り666パーツの変形で移し直して修正（上端 1672→1593mm＝第2頚椎の高さ、scripts/multifidus_fix/）。'
             '踵骨腱を 骨格 から 靱帯・腱 へ移動。718メッシュ（配布物は _下着(検討用) 2個を除く716）')
