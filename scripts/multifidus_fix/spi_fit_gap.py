# 下後鋸筋を、広背筋の内面と脊柱起立筋（胸最長筋・腰腸肋筋・胸腸肋筋）の外面のすき間に収める（案 C）。.blend は保存しない（結果は npz）
#  背中を (x, z) の格子（2.5mm）に区切り、後ろ（+Y）から光線で各面の y を測る。下後鋸筋がはみ出す列だけ、前後方向に
#  ずらす（入るとき）か、すき間に合わせて薄くする（入らないとき）。列ごとに y を一次式で写す（傾き>0 なので裏返らない）。
#  ずらし量・倍率はガウスでならしてから頂点ごとに補間する（段差を出さない）
# blender -b 3DAnatomyFemale.blend -P spi_fit_gap.py -- <下後鋸筋の入力 npz（ワールド座標）> <出力 npz> [余白 mm=0.3] [最小厚み mm=0.8]
import bpy, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]
INP, OUT = a[0], a[1]; MARGIN = float(a[2]) / 1000 if len(a) > 2 else 0.0003; TMIN = float(a[3]) / 1000 if len(a) > 3 else 0.0008
STEP, SIG = 0.0025, 0.004
base = lambda n: n.split("(")[0].split(".")[0]
for o in bpy.context.scene.objects:
    for md in o.modifiers: md.show_viewport = False
    o.hide_viewport = False
bpy.context.view_layer.update()
def obj(b): return next(o for o in bpy.data.objects if o.type == 'MESH' and base(o.name) == b)
def setco(o, w):
    Mi = np.array(o.matrix_world.inverted()); o.data.vertices.foreach_set("co", (w @ Mi[:3, :3].T + Mi[:3, 3]).astype(np.float32).ravel()); o.data.update()
X = np.load(INP)
for k in X.files: setco(obj(k), X[k].astype(np.float64))
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
def tree(o):
    return BVHTree.FromObject(o, dg), o.matrix_world.copy(), o.matrix_world.inverted()
def hits(tr, x, z):
    t, M, Mi = tr; ys = []; org = Vector((x, 1.0, z)); d = Vector((0, -1, 0))
    for _ in range(8):
        h = t.ray_cast(Mi @ org, (Mi.to_3x3() @ d).normalized(), 1.0e6)
        if h[0] is None: break
        wp = M @ h[0]; ys.append(wp.y); org = wp + d * 1e-5
    return ys
def gsmooth(F, W, sig_cells):
    # 重み付きガウス（W=0 のセルは周りから埋まる）
    from math import ceil
    r = int(ceil(3 * sig_cells)); k = np.exp(-(np.arange(-r, r + 1) / sig_cells) ** 2 / 2)
    def conv(A):
        A = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, A)
        return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, A)
    num, den = conv(F * W), conv(W)
    return np.where(den > 1e-9, num / np.maximum(den, 1e-9), 0.0), den
out, rep = {}, {}
for side, sg in (("右", -1), ("左", 1)):
    S = obj(side + "下後鋸筋"); trS, trL = tree(S), tree(obj(side + "広背筋"))
    trE = [tree(obj(side + n)) for n in ("胸最長筋", "腰腸肋筋", "胸腸肋筋")]
    W = X[side + "下後鋸筋"].astype(np.float64)
    xs = np.arange(W[:, 0].min() - STEP, W[:, 0].max() + STEP, STEP); zs = np.arange(W[:, 2].min() - STEP, W[:, 2].max() + STEP, STEP)
    A_ = np.ones((len(xs), len(zs))); D_ = np.zeros_like(A_); SIN = np.zeros_like(A_); VAL = np.zeros_like(A_); CHG = np.zeros_like(A_)
    stats = dict(cols=0, fit=0, shift=0, squash=0, center=0)
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            hs = hits(trS, x, z)
            if len(hs) < 2: continue
            s_out, s_in = hs[0], hs[1]; t = s_out - s_in
            if t <= 1e-5: continue
            hl = hits(trL, x, z); he = [h[0] for h in (hits(tr, x, z) for tr in trE) if h]
            U = hl[1] - MARGIN if len(hl) >= 2 else np.inf
            Lo = max(he) + MARGIN if he else -np.inf
            stats["cols"] += 1; SIN[i, j] = s_in; VAL[i, j] = 1
            if s_out <= U and s_in >= Lo:
                stats["fit"] += 1; continue
            gap = U - Lo
            if gap >= t:
                n_in = U - t if s_out > U else s_in
                n_in = max(n_in, Lo); a_, d_ = 1.0, n_in - s_in; stats["shift"] += 1
            elif gap >= TMIN:
                a_, d_ = gap / t, Lo - s_in; stats["squash"] += 1
            else:
                c = (U + Lo) / 2 if np.isfinite(gap) else s_in; a_, d_ = TMIN / t, c - TMIN / 2 - s_in; stats["center"] += 1
            A_[i, j], D_[i, j], CHG[i, j] = a_, d_, 1
    # ならす: 変えない列（fit）は a=1, d=0 として重み1で入れる（周りへ滑らかにつなぐ）
    sc = SIG / STEP
    As, _ = gsmooth(A_, VAL, sc); Ds, _ = gsmooth(D_, VAL, sc); Ss, den = gsmooth(SIN, VAL, 1.0)
    As = np.where(den > 1e-6, As, 1.0)
    # 頂点ごとに双一次補間
    fi = (W[:, 0] - xs[0]) / STEP; fj = (W[:, 2] - zs[0]) / STEP
    i0 = np.clip(np.floor(fi).astype(int), 0, len(xs) - 2); j0 = np.clip(np.floor(fj).astype(int), 0, len(zs) - 2)
    u = np.clip(fi - i0, 0, 1); v = np.clip(fj - j0, 0, 1)
    def bil(G): return G[i0, j0] * (1 - u) * (1 - v) + G[i0 + 1, j0] * u * (1 - v) + G[i0, j0 + 1] * (1 - u) * v + G[i0 + 1, j0 + 1] * u * v
    a_v, d_v, s_v = bil(As), bil(Ds), bil(Ss)
    Wn = W.copy(); Wn[:, 1] = s_v + d_v + a_v * (W[:, 1] - s_v)
    out[side + "下後鋸筋"] = Wn.astype(np.float32)
    mv = np.abs(Wn[:, 1] - W[:, 1]) * 1000
    rep[side] = dict(stats, moved_verts=int((mv > 0.05).sum()), n=len(W), move_max_mm=round(float(mv.max()), 1), a_min=round(float(a_v.min()), 2))
    print(side, rep[side], flush=True)
np.savez_compressed(OUT, **out)
print("DONE")
