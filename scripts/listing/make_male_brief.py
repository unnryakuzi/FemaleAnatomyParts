# -*- coding: utf-8 -*-
"""男性ブリーフを生成して .blend に書き出す（ヘッドレス実行口）。

  blender -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/listing/make_male_brief.py -- listing [waist]
  blender -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/listing/make_male_brief.py -- dist    [waist]

listing … 掲載画像用。体表＝筋肉面（掲載ショットで実際に写る面）。生殖器は隠して撮るので
          ウエストは自由に下げられる。出力 swimwear_fit_male.blend
dist    … 配布データ用。体表＝皮膚。**外性器 z<=0.861 を覆う必要があるのでウエストを
          0.870 より下げられない**（下げると根元が出る）。出力 swimwear_fit_male_dist.blend

マスター .blend は読むだけで保存しない。輪郭は brief_outline.json に記録する。
"""
import bpy, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import swimwear_fit_lib as L

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "listing"
WAIST = float(argv[1]) if len(argv) > 1 else (0.810 if MODE == "listing" else 0.878)

HEM = {"front": 0.660, "side": 0.790, "back": 0.700}
outline = {"waist": {"front": WAIST, "side": WAIST, "back": WAIST},
           "hem": dict(HEM), "power": 1.6}

if MODE == "dist":
    L.SURFACE_COLS["male"] = L.SURFACE_COLS_DIST["male"]
    out = os.path.join(HERE, "swimwear_fit_male_dist.blend")
else:
    L.SURFACE_COLS["male"] = ["表層筋", "深層筋", "骨格"]
    out = os.path.join(HERE, "swimwear_fit_male.blend")

print(f"@@@ MODE {MODE} waist={WAIST:.3f} hem={HEM}")
ob = L.generate_brief("male", name="Swimwear_Brief", outline=outline, gusset=True)

# 覆えているかを数値で確認（掲載用は生殖器を隠して撮るので参考値）
gen = L.col_objs("生殖器")
if gen:
    L.coverage("male", ["Swimwear_Brief"], [o.name for o in gen], "生殖器")

bpy.data.libraries.write(out, {ob}, fake_user=True, compress=True)
print(f"@@@ WROTE {out} ({os.path.getsize(out)} bytes) verts={len(ob.data.vertices)}")
print("@@@ DONE")
