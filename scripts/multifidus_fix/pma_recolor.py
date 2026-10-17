# 大胸筋の腹部の下の端（腱の色＝白クリーム）を、筋の真ん中と同じ色にする（形は変えない）。別名で保存
#  主軸（PCA）で上腕骨側を 1、下の端を 0 とし、0〜0.25 は筋の色、0.25〜0.40 で元の色へなめらかに戻す
# blender -b <blend> -P pma_recolor.py -- <保存先（開いたファイルと同じパスなら上書き保存）>
import bpy, sys, numpy as np
OUT = sys.argv[sys.argv.index("--") + 1]
base = lambda n: n.split("(")[0].split(".")[0]
hum = np.concatenate([np.array([o.matrix_world @ v.co for v in o.data.vertices]) for o in bpy.data.objects if o.type == 'MESH' and "上腕骨" in o.name])
for o in bpy.data.objects:
    if o.type != 'MESH' or base(o.name) not in ("右大胸筋腹部", "左大胸筋腹部"): continue
    me = o.data; n = len(me.vertices); co = np.empty(n * 3); me.vertices.foreach_get("co", co); M = np.array(o.matrix_world); W = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    c = W.mean(0); ax = np.linalg.svd(W - c, full_matrices=False)[2][0]; t = (W - c) @ ax
    near_h = np.argmin(((W[:, None, :] - hum[None, ::50, :]) ** 2).sum(2).min(1))
    if t[near_h] < 0: t = -t
    t = (t - t.min()) / (t.max() - t.min())
    at = me.color_attributes["Col"]; col = np.empty(n * 4, np.float32); at.data.foreach_get("color", col); col = col.reshape(-1, 4)
    mus = np.median(col[(t > 0.4) & (t < 0.6)], 0)
    w = np.clip((0.40 - t) / 0.15, 0, 1)[:, None]                         # 0.25 以下で 1、0.40 以上で 0
    col = col * (1 - w) + mus * w
    at.data.foreach_set("color", col.astype(np.float32).ravel()); print("色を変えた", o.name, int((w[:, 0] > 0).sum()), "/", n, "筋の色", np.round(mus, 3))
if bpy.path.abspath(OUT).replace("/", "\\").lower() == bpy.data.filepath.replace("/", "\\").lower():
    bpy.ops.wm.save_mainfile()                                                # マスターと同じパスなら上書き保存
else:
    bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print("SAVED", OUT)
