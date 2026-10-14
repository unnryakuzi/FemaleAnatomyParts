# 多裂筋の作り直し用: 筋肉・骨・腱の頂点（ワールド座標、間引き）と、指定パーツの全頂点・辺を書き出す。.blend は保存しない
# blender -b <blend> -P dump_parts.py -- <出力 npz> [全頂点を出すパーツ名の接頭辞 ...]
#  （FemaleAnatomyTexture\...\handoff_muscle_idmap_20261013\scripts\10_dump_parts.py と 11_dump_missing.py を1本にしたもの。
#    男性 Man_All のコレクション（表層筋・深層筋）も読む）
import bpy, sys, re, json, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; OUT = a[0]; FULL = a[1:]; CAP = 3000
base = lambda n: re.sub(r"\(.*?\)|\.\d+$", "", n)
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("表層筋", "深層筋", "靱帯・腱", "骨格")]
objs = sorted({o for c in USE for o in c.all_objects if o.type == "MESH"}, key=lambda o: o.name)
out, meta, full = {}, {}, {}
for o in objs:
    me = o.data; n = len(me.vertices); co = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world, np.float64); w = co @ M[:3, :3].T + M[:3, 3]
    ed = np.empty(len(me.edges) * 2, np.int64); me.edges.foreach_get("vertices", ed)
    sig = int((ed[0::2] * 1000003 + ed[1::2]).sum() % 2147483647)       # 辺のつながりの指紋（同じ番号付けか）
    st = max(1, n // CAP); idx = np.arange(0, n, st)
    k = base(o.name)
    if k in meta: k = k + "#" + o.name
    s = len(meta)
    out["i_%d" % s] = idx.astype(np.int32); out["p_%d" % s] = w[idx].astype(np.float32)
    meta[k] = dict(slot=s, name=o.name, n=n, sig=sig, cols=[c.name for c in o.users_collection])
    if any(o.name.startswith(f) for f in FULL):
        out["w_%d" % s] = w; out["e_%d" % s] = ed.reshape(-1, 2).astype(np.int32); full[k] = s
np.savez_compressed(OUT, **out); json.dump(dict(meta=meta, full=full), open(OUT.replace(".npz", ".json"), "w", encoding="utf-8"), ensure_ascii=False)
print("DUMPED", len(meta), "full", list(full))
