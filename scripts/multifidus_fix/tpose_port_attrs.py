# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: plan のパーツについて、メッシュ属性ごとのハッシュと評価後の角の法線のハッシュを出す。.blend は保存しない
#  頂点だけ写したとき、カスタム法線（custom_normal は面の形に対する相対値）を含めて見た目がマスターと同じになるかを確かめる用
# blender -b <blend> -P tpose_port_attrs.py -- <plan.json> <出力 json>
import bpy, sys, json, hashlib, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; PLAN = json.load(open(a[0], encoding="utf-8")); OUT = a[1]
def h(x): return hashlib.md5(np.ascontiguousarray(x).tobytes()).hexdigest()[:16]
DT = {"FLOAT_VECTOR": (np.float32, 3, "vector"), "FLOAT_COLOR": (np.float32, 4, "color"), "INT16_2D": (np.int16, 2, "value"),
      "BOOLEAN": (bool, 1, "value"), "INT": (np.int32, 1, "value"), "INT32_2D": (np.int32, 2, "value"), "FLOAT": (np.float32, 1, "value")}
d = {}
for n in [r["n"] for r in PLAN["move"]] + [r["n"] for r in PLAN["keep_arm"]]:
    me = bpy.data.objects[n].data; r = {}
    for at in me.attributes:
        if at.name.startswith(".select"): continue                     # 選択状態は形・見た目に関係しない
        if at.data_type not in DT: r[at.name] = "?" + at.data_type; continue
        t, k, f = DT[at.data_type]; buf = np.empty(len(at.data) * k, t); at.data.foreach_get(f, buf); r[at.name] = h(buf)
    cn = np.empty(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get("vector", cn); r["_corner_normals"] = h(cn)
    r["_mats"] = [m.name if m else None for m in me.materials]
    d[n] = r
json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("ATTRS", len(d))
