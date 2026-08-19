# -*- coding: utf-8 -*-
"""下着を出品モデルへフィットさせ、結果を小さな .blend に書き出す（ヘッドレス実行口）。

中身は swimwear_fit_lib.py。パラメータの詰めは MCP でビューポートを見ながら行い、
確定後の再生成をこのスクリプトで再現する。マスター .blend は読むだけで保存しない。

usage:
  blender -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/listing/fit_swimwear.py -- male
  blender -b 3DAnatomyFemale.blend                   -P scripts/listing/fit_swimwear.py -- female
  （末尾に probe を足すと採寸だけ）
出力: scripts/listing/swimwear_fit_<model>.blend  / 出力行は "@@@" 始まり
"""
import bpy, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import swimwear_fit_lib as L

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODEL = argv[0] if argv else "male"

if "probe" in argv[1:]:
    L.probe(MODEL)
else:
    L.fit(MODEL)
    for garment, targets, label in (
        (["Swimwear_Bottom"], [o.name for o in L.col_objs("生殖器")], "生殖器"),
        (["Swimwear_Top"], ["Breast_Base"], "乳房"),
    ):
        if all(n in bpy.data.objects for n in garment) and targets and \
           all(n in bpy.data.objects for n in targets):
            L.coverage(MODEL, garment, targets, label)
    L.cleanup()
    L.write_out(MODEL)
print("@@@ DONE", MODEL)
