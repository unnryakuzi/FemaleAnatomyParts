# -*- coding: utf-8 -*-
"""配布物に入れない検討用コレクションを、書き出し前にメモリ上で消す（.blend は保存しない）。

  blender -b 3DAnatomyFemale.blend -P scripts/listing/drop_review_only.py -P scripts/listing/export_dist.py -- female v1.68.0

女性マスターの `_下着(検討用)`（Swimwear_Top/Bottom）は BOOTH 掲載画像の検討用で、配布物 v1.67.x には入っていない。
export_dist.py は全部の非表示を解除して書き出すので、残したままだと配布物に入る（2026-10-14）。
"""
import bpy

DROP = ["_下着(検討用)", "_ガイドライン"]
for name in DROP:
    c = bpy.data.collections.get(name)
    if c is None:
        continue
    objs = list(c.all_objects)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(c)
    print("[drop_review_only] %s: %d オブジェクトを外した" % (name, len(objs)))

# 編集用のガイド線（CURRENT_*ライン / DIAG_*）。v1.67.x の .blend には非表示で残っていたが、
# export_dist.py が非表示を解除すると glb/obj にメッシュとして出る（2026-10-14 の初回書き出しで glb 718 / obj 720 になった）
guides = [o for o in bpy.data.objects if o.type == "CURVE" and o.name.startswith(("CURRENT_", "DIAG_"))]
for o in guides:
    bpy.data.objects.remove(o, do_unlink=True)
print("[drop_review_only] ガイド線 %d 本を外した" % len(guides))
