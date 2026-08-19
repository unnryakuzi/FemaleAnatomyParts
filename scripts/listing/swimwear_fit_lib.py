# -*- coding: utf-8 -*-
"""下着(Swimwear_Top/Bottom)を出品モデルへ着せるためのライブラリ。MCP から呼ぶ。

  import sys, importlib
  sys.path.insert(0, r"C:\\Users\\abesh\\Documents\\Blender\\MaleAnatomy\\scripts\\listing")
  import swimwear_fit_lib as L; importlib.reload(L)
  L.probe("male")          # 採寸だけ（何も変更しない）
  L.fit("male")            # append → 位置合わせ → 押し出し
  L.write_out("male")      # swimwear_fit_male.blend へ書き出し（マスターは保存しない）

方式:
  1) ランドマーク合わせ
     股下高さ(胴体断面が成立する最下端)を基準に骨盤帯で採寸し、軸ごとの scale と
     アンカーを決める。Bottom=股下高さ / Top=胸の最前点(乳頭高) にそれぞれ合わせる。
  2) 円柱ハイトマップによる押し出し
     体表の頂点を「体の中心軸まわりの (θ, z) 格子」に入れて各セルの最大半径 R を持つ。
     下着頂点の半径が R+clearance を下回っていたら外へ押す。正射投影カメラは水平に
     見るので、この判定＝「その高さで体が下着の外に見えていないか」そのもの。
     押し量は膨張→平均で均し、tentacle 状の突起を作らない
     （CLAUDE.md: Shrinkwrap modifier / 素の per-vertex push は形状破綻するため使わない）。
"""
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_BLEND = os.path.join(HERE, "swimwear_src.blend")

# 体表として扱うコレクション（下着を乗せる面）＝掲載ショットで実際に写る面に合わせる。
#  male : 筋肉面。皮膚(外皮)には外性器が完全に造形されており、皮膚に合わせると下着が
#         その形に沿って股間が膨らむ（実測・目視）。全年齢化が目的なのに逆効果になる。
#         掲載する筋肉ショットでは皮膚は非表示なので筋肉面に合わせるのが正しい。
#         → 皮膚ショット(07_skin)は下着で覆えないため、従来どおり掲載しない。
#  female: 全身の皮膚が無いので 女性外皮(乳房)+筋肉+骨格 を体表とみなす。
SURFACE_COLS = {"male": ["表層筋", "深層筋", "骨格"], "female": ["女性外皮", "筋肉"]}
# 配布データ用の男性は皮膚を含むモデルで見える必要があるので、皮膚を体表にする。
SURFACE_COLS_DIST = {"male": ["外皮"]}
# 押し出しの基準から外す箱（ワールド座標 xmin,xmax,ymin,ymax,zmin,zmax）。
# 男性の皮膚には外性器が完全に造形されており、そのまま覆うと下着が形に沿って股間が
# 膨らむ（実測・目視）。この領域を体表から外すと、下着は上を橋渡しして平らになる。
NO_PUSH_BOX = {"male": (-0.060, 0.060, -0.230, -0.150, 0.660, 0.800)}
# 押し出しの基準から外すもの。
#  male : 生殖器（下着の内側に隠す）
#  female: 腕・手。A ポーズでは上腕の内側面が胴体の外周と同じ |x| に来る高さがあり、
#          幅の上限だけでは分離できない（ブラのバンドが腕へ 30mm 張り出した）。
#          骨格も外す（前腕・上腕の骨が同じ帯に入るため）。骨は筋の内側なので体表判定に不要。
SURFACE_EXCLUDE_COLS = {
    "male": ["生殖器"],
    "female": ["筋肉_右上腕", "筋肉_左上腕", "筋肉_右前腕", "筋肉_左前腕",
               "筋肉_右手", "筋肉_左手"],
}
GARMENTS = {"male": ["Swimwear_Bottom"], "female": ["Swimwear_Top", "Swimwear_Bottom"]}

CLEARANCE = 0.007      # 体表から浮かせる量 7mm
SUBDIV = 1             # 押し出し前に下着を細分する回数。素の 762 頂点だと頂点間隔が
                       # 約15mm あり、間で体表が覗く（背面で実測）
MAX_PUSH = 0.030       # 1頂点あたりの押し出し上限。これを超える不一致は形状の食い違いで、
                       # 追うと下着がスカート状に膨らむ
MAX_GAP = 0.012        # 体表から浮いてよい上限。超えたぶんは引き戻す
DILATE_ITERS = 2
SMOOTH_ITERS = 6
# 体幹コリドー: 押し出しの基準にする体表を胴体だけに絞る (zl, zh, tan_cut, xtorso)。
#   常に |x|<=xtorso … A ポーズの手が腰の高さ(z≈0.90)にある。拾うと腰が羽状に広がる
#   z<=zl では「真横のセクター」を落とす（|Δy| < tan_cut*|x| を除外）
#     骨盤より下は体が左右の脚に分かれていて中心軸まわりの星形にならず、外向きレイが
#     太腿を拾うと下着がスカート状に広がる（実測 push 110mm）。
#     ただし |x| でまとめて切ると臀部まで消えて下着が尻を突き抜ける（実測）。太腿は
#     ほぼ真横(Δy≈0)、臀部は斜め後方(Δy>0)なので、角度で切れば太腿だけ落とせる。
#   zl..zh で tan_cut を 0 へ線形に戻す
LEG_CUT = {"male": (0.800, 0.870, 0.577, 0.200), "female": (0.865, 0.930, 0.577, 0.200)}
NTHETA = 240           # 円柱ハイトマップの角度分割（1.5°）
ZBIN = 0.004           # 同 Z 分割 4mm

_VIS_BACKUP = None     # look() 前の表示状態
USE_NO_BOX = False     # True で NO_PUSH_BOX を押し出しの基準から外す（配布用の男性）


# ------------------------------------------------------------------ 基本
def col_objs(name):
    c = bpy.data.collections.get(name)
    return [o for o in c.all_objects if o.type == 'MESH'] if c else []


def surface_objs(model):
    keep, ex = [], set()
    for cn in SURFACE_EXCLUDE_COLS[model]:
        ex |= {o.name for o in col_objs(cn)}
    seen = set()
    for cn in SURFACE_COLS[model]:
        for o in col_objs(cn):
            if o.name not in ex and o.name not in seen:
                seen.add(o.name); keep.append(o)
    return keep


def eval_world_verts(objs):
    """メッシュのワールド座標頂点を (N,3) で返す。

    モディファイア付き（女性の Breast_Base は MIRROR で左半分が生える）だけ
    depsgraph 評価する。女性の体表は 638 オブジェクト 1100万頂点あり、全部に
    to_mesh() を掛けると MCP がタイムアウトする。
    """
    dg = None
    chunks = []
    for o in objs:
        if o.modifiers:
            if dg is None:
                dg = bpy.context.evaluated_depsgraph_get()
            ev = o.evaluated_get(dg)
            try:
                me = ev.to_mesh()
            except RuntimeError:
                continue
            free = ev.to_mesh_clear
        else:
            me, free = o.data, None
        n = len(me.vertices)
        if n:
            a = np.empty(n * 3, dtype=np.float64)
            me.vertices.foreach_get("co", a)
            a = a.reshape(n, 3)
            m = np.array(o.matrix_world)
            chunks.append(a @ m[:3, :3].T + m[:3, 3])
        if free:
            free()
    return np.concatenate(chunks) if chunks else np.zeros((0, 3))


def obj_verts(o):
    me = o.data
    n = len(me.vertices)
    a = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", a)
    a = a.reshape(n, 3)
    m = np.array(o.matrix_world)
    return a @ m[:3, :3].T + m[:3, 3]


def set_verts(o, arr):
    mi = np.array(o.matrix_world.inverted())
    loc = arr @ mi[:3, :3].T + mi[:3, 3]
    o.data.vertices.foreach_set("co", loc.reshape(-1).copy())
    o.data.update()


# ------------------------------------------------------------------ 採寸
def torso_slice(pts, z, half=0.012, sparse=False):
    """Z=z の水平断面から胴体だけを切り出す。

    dense（出品モデル・百万頂点級・A ポーズ）: 腕は胴体の外側にあるので |x| を昇順に
      並べて最初の「空隙」で打ち切る。x≈0 に材料が無い断面は None（＝胴体ではない）。
    sparse（Ref_Body・14k 頂点・T ポーズ）: 点が疎で空隙判定が誤爆する（実測 z=0.90 で
      真値 0.170 に対し 0.056 と誤検出）。T ポーズの腕は |x|>0.50 に離れているので、
      空隙判定をやめて |x|<=0.30 のキャップだけで胴体を取る。
    """
    s = pts[np.abs(pts[:, 2] - z) < half]
    if len(s) < 8:
        return None
    ax = np.abs(s[:, 0])
    if sparse:
        s = s[ax <= 0.30]
        return s if len(s) >= 8 else None
    if ax.min() > 0.020:
        return None
    srt = np.sort(ax)
    span = max(srt[-1] - srt[0], 1e-6)
    gap = float(np.clip(6.0 * span / len(srt), 0.010, 0.030))
    idx = np.nonzero(np.diff(srt) > gap)[0]
    cut = srt[idx[0]] if len(idx) else srt[-1]
    s = s[ax <= cut + 1e-9]
    return s if len(s) >= 8 else None


def profile(pts, z0, z1, step=0.02, sparse=False):
    out = []
    for z in np.arange(z0, z1 + 1e-9, step):
        s = torso_slice(pts, z, sparse=sparse)
        if s is None:
            continue
        out.append(dict(z=float(z), ymin=float(s[:, 1].min()), ymax=float(s[:, 1].max()),
                        xmax=float(np.abs(s[:, 0]).max()), n=len(s)))
    return out


def smooth_prof(prof, win=5):
    """断面プロファイルの幅と前後中心を移動平均でならす。

    生の値は Z ごとに波打つ（外性器の張り出し・臀部の出入りで断面中心が ±15mm 動く）。
    そのまま Z 依存の変換に使うと下着が波打って体に食い込む。
    """
    zs = np.array([p["z"] for p in prof])
    k = np.ones(win) / win
    def sm(vals):
        v = np.array(vals, dtype=float)
        return np.convolve(np.pad(v, (win // 2, win // 2), mode='edge'), k, mode='valid')
    return zs, sm([p["xmax"] for p in prof]), sm([(p["ymin"] + p["ymax"]) / 2 for p in prof])


def prof_at(prof, z):
    """断面プロファイルを Z で線形補間して返す。"""
    zs = np.array([p["z"] for p in prof])
    return dict(
        z=float(z),
        ymin=float(np.interp(z, zs, [p["ymin"] for p in prof])),
        ymax=float(np.interp(z, zs, [p["ymax"] for p in prof])),
        xmax=float(np.interp(z, zs, [p["xmax"] for p in prof])),
    )


def widest(prof, z0, z1):
    c = [p for p in prof if z0 <= p["z"] <= z1]
    return max(c, key=lambda p: p["xmax"]) if c else None


def frontmost(prof, z0, z1):
    c = [p for p in prof if z0 <= p["z"] <= z1]
    return min(c, key=lambda p: p["ymin"]) if c else None


def axis_y_fn(prof):
    zs = np.array([p["z"] for p in prof])
    ys = np.array([(p["ymin"] + p["ymax"]) / 2 for p in prof])
    return lambda z: np.interp(z, zs, ys)


_FRAME_CACHE = {}


def measure(model, verbose=True, cache=True):
    """出どころ素体と出品モデルの体表を採寸する。

    股下高さは基準に使わない。腿が接触しているモデル（Man_All の皮膚）では
    「x≈0 に材料がある最下端」が太腿の中ほどになってしまい当てにならないため。
    代わりに fit() 側で「覆うべき Z 範囲」を明示指定し、その高さの断面で採寸する。
    """
    if cache and model in _FRAME_CACHE:
        return _FRAME_CACHE[model]
    src = load_source()
    src_pts = obj_verts(src["Ref_Body"])
    tgt_pts = eval_world_verts(surface_objs(model))
    sp = profile(src_pts, 0.60, 1.37, sparse=True)   # 1.37 超は T ポーズの腕が入る
    tp = profile(tgt_pts, 0.50, 1.60)
    f = dict(src_h=src_pts[:, 2].max() - src_pts[:, 2].min(),
             tgt_h=tgt_pts[:, 2].max() - tgt_pts[:, 2].min(),
             src_prof=sp, tgt_prof=tp, tgt_pts=tgt_pts)
    if verbose:
        print(f"@@@ H src={f['src_h']:.4f} tgt={f['tgt_h']:.4f} ratio={f['tgt_h']/f['src_h']:.4f} "
              f"tgt_verts={len(tgt_pts)}")
    if cache:
        _FRAME_CACHE[model] = f
    return f


def probe(model):
    f = measure(model)
    for p in f["tgt_prof"]:
        print(f"@@@ PROF z={p['z']:.3f} Ymin={p['ymin']:+.4f} Ymax={p['ymax']:+.4f} "
              f"Xmax={p['xmax']:.4f} n={p['n']}")
    for cn in ("生殖器",):
        objs = col_objs(cn)
        if objs:
            g = eval_world_verts(objs)
            print(f"@@@ {cn} n={len(objs)} bbox=({g[:,0].min():.4f},{g[:,1].min():.4f},{g[:,2].min():.4f})-"
                  f"({g[:,0].max():.4f},{g[:,1].max():.4f},{g[:,2].max():.4f})")
    br = bpy.data.objects.get("Breast_Base")
    if br:
        b = eval_world_verts([br])
        print(f"@@@ Breast_Base bbox=({b[:,0].min():.4f},{b[:,1].min():.4f},{b[:,2].min():.4f})-"
              f"({b[:,0].max():.4f},{b[:,1].max():.4f},{b[:,2].max():.4f})")
    return f


# ------------------------------------------------------------------ 円柱ハイトマップ
class HeightMap:
    """体表を中心軸まわりの (θ, z) 格子に入れ、各セルの最大半径を持つ。

    正射カメラは水平に見るので「ある高さ・ある方位で体表がどこまで外に出ているか」＝
    最大半径。これが下着の半径を超えていたら、その方向から体が見えてしまう。
    """

    def __init__(self, pts, ayf, z0, z1, pad=0.06, legcut=None, no_box=None):
        m = (pts[:, 2] >= z0 - pad) & (pts[:, 2] <= z1 + pad)
        p = pts[m]
        if no_box:
            x0, x1, y0, y1, bz0, bz1 = no_box
            inb = ((p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)
                   & (p[:, 2] >= bz0) & (p[:, 2] <= bz1))
            print(f"@@@ HMAP 除外box {int(inb.sum())} pts（下着はこの上を橋渡しする）")
            p = p[~inb]
        if legcut:
            zl, zh, tan_cut, xtorso = legcut
            t = np.clip((p[:, 2] - zl) / max(zh - zl, 1e-6), 0.0, 1.0)
            k = tan_cut * (1.0 - t)
            dy_ = np.abs(p[:, 1] - ayf(p[:, 2]))
            keep = (np.abs(p[:, 0]) <= xtorso) & (dy_ >= k * np.abs(p[:, 0]))
            print(f"@@@ HMAP corridor |x|<={xtorso}, 真横セクター除外 tan<={tan_cut}(z<={zl}): "
                  f"{len(p)} -> {int(keep.sum())} pts")
            p = p[keep]
        self.z0 = z0 - pad
        self.nz = max(int((z1 + pad - self.z0) / ZBIN) + 1, 1)
        dx = p[:, 0]
        dy = p[:, 1] - ayf(p[:, 2])
        r = np.hypot(dx, dy)
        th = np.arctan2(dy, dx)
        ti = np.clip(((th + math.pi) / (2 * math.pi) * NTHETA).astype(int), 0, NTHETA - 1)
        zi = np.clip(((p[:, 2] - self.z0) / ZBIN).astype(int), 0, self.nz - 1)
        flat = zi * NTHETA + ti
        g = np.zeros(self.nz * NTHETA)
        np.maximum.at(g, flat, r)
        self.grid = g.reshape(self.nz, NTHETA)
        self.count = np.bincount(flat, minlength=self.nz * NTHETA).reshape(self.nz, NTHETA)
        print(f"@@@ HMAP pts={len(p)} z=[{self.z0:.3f},{self.z0+self.nz*ZBIN:.3f}] "
              f"cells_filled={int((self.count>0).sum())}/{self.grid.size}")

    def max_r(self, x, y_rel, z, wt=2, wz=1):
        """(θ,z) の近傍セルを見て体表の最大半径を返す。近傍が空なら None。"""
        r = math.hypot(x, y_rel)
        th = math.atan2(y_rel, x)
        ti = int((th + math.pi) / (2 * math.pi) * NTHETA) % NTHETA
        zi = int((z - self.z0) / ZBIN)
        if zi < 0 or zi >= self.nz:
            return None
        best = 0.0; found = False
        for dz in range(-wz, wz + 1):
            k = zi + dz
            if k < 0 or k >= self.nz:
                continue
            for dt in range(-wt, wt + 1):
                j = (ti + dt) % NTHETA
                if self.count[k, j]:
                    found = True
                    if self.grid[k, j] > best:
                        best = self.grid[k, j]
        return best if found else None


# ------------------------------------------------------------------ 着せる
SRC_NAMES = ("Swimwear_Top", "Swimwear_Bottom", "Ref_Body")


def load_source(fresh=False):
    """swimwear_src.blend から下着と参照素体を append（既にあれば再利用）。

    fresh=True で必ず入れ直す。fit() は細分でメッシュを作り替えるので、やり直すたびに
    素の形状から始めないと細分が積み上がる。
    """
    if fresh:
        for n in SRC_NAMES:
            o = bpy.data.objects.get(n)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
    have = {n: bpy.data.objects.get(n) for n in SRC_NAMES}
    if all(have.values()):
        return have
    with bpy.data.libraries.load(SRC_BLEND) as (df, dt):
        dt.objects = [n for n in df.objects if n not in bpy.data.objects]
    for o in dt.objects:
        if o is not None:
            bpy.context.scene.collection.objects.link(o)
    return {n: bpy.data.objects.get(n) for n in SRC_NAMES}


def edge_neighbors(me):
    nb = [[] for _ in range(len(me.vertices))]
    for e in me.edges:
        a, b = e.vertices
        nb[a].append(b); nb[b].append(a)
    return nb


def push_pass(name, gob, gv, hmap, ayf, tag):
    n = len(gv)
    need = np.zeros(n)
    dirs = np.zeros((n, 2))
    ay = ayf(gv[:, 2])
    for i in range(n):
        dx = gv[i, 0]; dy = gv[i, 1] - ay[i]
        r = math.hypot(dx, dy)
        if r < 0.025:                     # 軸に近すぎる（股布）→ 押さない
            continue
        dirs[i] = (dx / r, dy / r)
        R = hmap.max_r(dx, dy, gv[i, 2])
        if R is not None:
            need[i] = min(max(0.0, (R + CLEARANCE) - r), MAX_PUSH)
    raw_max = need.max()
    need0 = need.copy()
    nb = edge_neighbors(gob.data)
    for _ in range(DILATE_ITERS):
        nn = need.copy()
        for i, ns in enumerate(nb):
            if ns:
                nn[i] = max(need[i], float(np.mean(need[ns])))
        need = nn
    for _ in range(SMOOTH_ITERS):
        nn = need.copy()
        for i, ns in enumerate(nb):
            if ns:
                nn[i] = 0.4 * need[i] + 0.6 * float(np.mean(need[ns]))
        need = nn
    # 平均化でピークが削れるので、最後に必要量を下回らないよう戻す（被覆の保証）。
    # 周囲は膨張で既に持ち上がっているため、ここで戻しても尖らない。
    need = np.maximum(need, need0)
    gv[:, 0] += dirs[:, 0] * need
    gv[:, 1] += dirs[:, 1] * need
    print(f"@@@ PUSH {name} {tag} n>0={int((need>1e-6).sum())}/{n} "
          f"raw_max={raw_max*1000:.1f} applied_max={need.max()*1000:.1f} mm")
    return gv


def pull_pass(name, gob, gv, hmap, ayf):
    """体表から離れすぎた箇所を引き戻す。

    元は別体型用の下着なので、体が細い高さで裾や脇が輪郭の外へ浮く（実測で数mm〜）。
    体表半径が分かるセルに限り r <= R + MAX_GAP に収める。R + MAX_GAP は
    CLEARANCE より大きいので、引き戻しても体に接触・貫通はしない。
    """
    n = len(gv)
    d = np.zeros(n)
    dirs = np.zeros((n, 2))
    ay = ayf(gv[:, 2])
    for i in range(n):
        dx = gv[i, 0]; dy = gv[i, 1] - ay[i]
        r = math.hypot(dx, dy)
        if r < 0.025:
            continue
        dirs[i] = (dx / r, dy / r)
        R = hmap.max_r(dx, dy, gv[i, 2])
        if R is not None and r > R + MAX_GAP:
            d[i] = -(r - (R + MAX_GAP))
    nb = edge_neighbors(gob.data)
    for _ in range(SMOOTH_ITERS):
        nn = d.copy()
        for i, ns in enumerate(nb):
            if ns:
                nn[i] = 0.4 * d[i] + 0.6 * float(np.mean(d[ns]))
        d = nn
    gv[:, 0] += dirs[:, 0] * d
    gv[:, 1] += dirs[:, 1] * d
    print(f"@@@ PULL {name} n<0={int((d<-1e-6).sum())}/{n} max={-d.min()*1000:.1f} mm")
    return gv


def wrap_pass(model, name, offset=0.005, max_snap=0.060, smooth=4, skip_breast=True):
    """最近傍の体表点へ投影して貼り付ける（肩紐・背中バンド用）。

    押し出し/引き戻しは中心軸からの水平方向にしか効かない。肩の上は面が水平を向いて
    いるので水平方向の判定が成立せず、紐が蛇行し背中から浮く（ユーザー指摘 2026-08-15）。
    ここは方向を仮定せず「いちばん近い体表点から offset だけ離れた位置」へ置く。

    カップは対象外（skip_breast）。ただし「最近傍が乳房の点なら触らない」だけでは
    足りない。乳房の奥には大胸筋があり、カップ頂点の最近傍がそちらになると乳房を
    突き抜けて内側へ吸い込まれ、カップが割れる（実測・目視で確認 2026-08-15）。
    → **乳房の bbox 内にある「乳房以外」の点を KDTree から除く**。こうすると胸の前面で
      最近傍になり得るのは乳房だけになり、カップ頂点は確実に skip される。
    """
    from mathutils.kdtree import KDTree
    gob = bpy.data.objects[name]
    gv = obj_verts(gob)
    z0, z1 = gv[:, 2].min() - 0.08, gv[:, 2].max() + 0.08

    objs, is_br = [], []
    for cn in SURFACE_COLS[model]:          # ここでは腕も除外しない（肩紐は三角筋に乗る）
        for o in col_objs(cn):
            if o not in objs:
                objs.append(o)
    pts_list, br_list = [], []
    for o in objs:
        p = eval_world_verts([o])
        if not len(p):
            continue
        m = (p[:, 2] >= z0) & (p[:, 2] <= z1)
        if not m.any():
            continue
        p = p[m]
        pts_list.append(p)
        br_list.append(np.full(len(p), o.name == "Breast_Base"))
    pts = np.concatenate(pts_list); brf = np.concatenate(br_list)
    if skip_breast and brf.any():
        b = pts[brf]
        lo = b.min(axis=0) - 0.005; hi = b.max(axis=0) + 0.005
        inside = np.all((pts >= lo) & (pts <= hi), axis=1)
        drop = inside & ~brf                # 乳房 bbox 内の「乳房以外」＝奥の大胸筋など
        print(f"@@@ WRAP {name} 乳房bbox内の非乳房点を除外: {int(drop.sum())} pts")
        pts = pts[~drop]; brf = brf[~drop]
    stride = max(1, len(pts) // 400000)     # KDTree の構築が Python ループなので上限を切る
    pts = pts[::stride]; brf = brf[::stride]
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(Vector(p), i)
    kd.balance()
    print(f"@@@ WRAP {name} kdtree={len(pts)} pts (stride={stride}) z=[{z0:.3f},{z1:.3f}]")

    def project(arr):
        moved = np.zeros(len(arr), dtype=bool)
        for i, v in enumerate(arr):
            co, idx, d = kd.find(Vector(v))
            if d > max_snap:
                continue
            if skip_breast and brf[idx]:
                continue
            n = Vector(v) - co
            if n.length < 1e-6:
                continue
            arr[i] = np.array(co + n.normalized() * offset)
            moved[i] = True
        return moved

    moved = project(gv)
    # 貼り付けただけだと点ごとに凹凸が残る（紐の蛇行）。長手方向にならしてから再投影する
    nb = edge_neighbors(gob.data)
    for _ in range(smooth):
        nv = gv.copy()
        for i, ns in enumerate(nb):
            if moved[i] and ns:
                nv[i] = 0.35 * gv[i] + 0.65 * gv[ns].mean(axis=0)
        gv = nv
        project(gv)
    set_verts(gob, gv)
    print(f"@@@ WRAP {name} projected {int(moved.sum())}/{len(gv)} verts (offset={offset*1000:.0f}mm)")
    return gv


STRAP_JSON = os.path.join(HERE, "swimwear_strap_prev.json")


def _centerline_points(gv, sgn, n_strap=12, n_band=7, z_split=1.405, x_min=0.030, y_back=0.080):
    """肩紐＋背面バンドの中心線を現在のメッシュから求める（19点）。sgn=+1 が左(+X)。"""
    x = gv[:, 0] * sgn
    pts = []
    s = gv[(x > x_min) & (gv[:, 2] > z_split)]          # 肩紐部: Y で等分
    e = np.linspace(s[:, 1].min(), s[:, 1].max(), n_strap + 1)
    for i in range(n_strap):
        m = (s[:, 1] >= e[i]) & (s[:, 1] <= e[i + 1])
        if m.sum() >= 2:
            pts.append(s[m].mean(axis=0))
    # バンド部: 合流部から正中へ向かう内側だけ。体側へ回り込む部分(x が肩紐より外)を
    # 混ぜると、下降部(x≈0.07)と回り込み(x≈0.12)の2つの塊の中間を平均で拾ってしまい、
    # ライン点が実際には頂点が無い位置に出る（実測 x=0.098 に対し頂点は 0.065〜0.08）。
    x_cap = (pts[-1][0] * sgn + 0.015) if len(pts) else 0.095
    s = gv[(x > -0.005) & (x <= x_cap) & (gv[:, 2] <= z_split) & (gv[:, 1] > y_back)]
    key = s[:, 2] + s[:, 0] * sgn      # 下降で Z が減り、正中へ向かって X も減る＝単調
    e = np.linspace(key.max(), key.min(), n_band + 1)
    for i in range(n_band):
        m = (key <= e[i]) & (key >= e[i + 1])
        if m.sum() >= 2:
            pts.append(s[m].mean(axis=0))
    return np.array(pts)


def restore_strap_lines():
    """swimwear_strap_prev.json の座標から CURRENT_<側>肩紐ライン を作り直す。

    ユーザーが編集した肩紐の経路は JSON に残っているので、シーンにカーブが無くても
    三角ビキニの工程（fit → snap_to_line → rebuild_strap）をそのまま再現できる。
    """
    import json
    D = json.load(open(STRAP_JSON, encoding="utf-8"))
    for side, d in D["straps"].items():
        pts = np.array(d["prev"], dtype=float)
        name = f"CURRENT_{side}肩紐ライン"
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        cu = bpy.data.curves.new(name, 'CURVE')
        cu.dimensions = '3D'; cu.bevel_depth = 0.0035; cu.resolution_u = 2
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, q in enumerate(pts):
            sp.points[i].co = (float(q[0]), float(q[1]), float(q[2]), 1.0)
        ob = bpy.data.objects.new(name, cu)
        ob.show_in_front = True
        bpy.context.scene.collection.objects.link(ob)
        print(f"@@@ RESTORE {name} {len(pts)}点")


def _line_points(side):
    ob = bpy.data.objects[f"CURRENT_{side}肩紐ライン"]
    return np.array([list(ob.matrix_world @ Vector(p.co[:3])) for p in ob.data.splines[0].points])


def _set_line_points(side, pts):
    ob = bpy.data.objects[f"CURRENT_{side}肩紐ライン"]
    sp = ob.data.splines[0]
    for i, q in enumerate(pts):
        sp.points[i].co = (float(q[0]), float(q[1]), float(q[2]), 1.0)
    ob.data.update_tag()


def snap_to_line(master="左", r0=0.030, r1=0.075, mirror=True):
    """**デバッグラインを正**として、下着メッシュをラインへ寄せる。

    apply_strap_edit が「ラインの移動量をメッシュへ渡す」のに対し、こちらは
    「現在のメッシュ中心線とラインの差」を埋める。編集を重ねてもズレが溜まらない。
    master 側のラインを反対側へミラーしてから両側を合わせるので、
    「片側だけ編集 → 左右対称に反映」がそのまま成立する。
    """
    gob = bpy.data.objects["Swimwear_Top"]
    gv = obj_verts(gob)
    tgt = {master: _line_points(master)}
    other = "右" if master == "左" else "左"
    if mirror:
        m = tgt[master].copy(); m[:, 0] *= -1
        tgt[other] = m
        _set_line_points(other, m)                 # 反対側のラインも正しい位置へ
        print(f"@@@ SNAP {master}のラインを{other}へミラー")
    else:
        tgt[other] = _line_points(other)           # 左右それぞれ自分のラインへ合わせる

    total = np.zeros_like(gv)
    for side, sgn in ((master, 1.0 if master == "左" else -1.0),
                      (other, -1.0 if master == "左" else 1.0)):
        prev = _centerline_points(gv, sgn)
        cur = tgt[side]
        if len(prev) != len(cur):
            raise SystemExit(f"{side}: 点数不一致 中心線={len(prev)} ライン={len(cur)}")
        delta = cur - prev
        ts = np.linspace(0.0, 1.0, len(prev))
        same = (gv[:, 0] * sgn) > -0.005
        n = 0
        for i in np.nonzero(same)[0]:
            t, d = _polyline_project(prev, gv[i])
            if d >= r1:
                continue
            w = 1.0 if d <= r0 else 0.5 * (1 + math.cos(math.pi * (d - r0) / (r1 - r0)))
            total[i] += np.array([np.interp(t, ts, delta[:, k]) for k in range(3)]) * w
            n += 1
        print(f"@@@ SNAP {side} 中心線→ライン ずれ max={np.linalg.norm(delta,axis=1).max()*1000:.1f}mm "
              f"適用 {n} 頂点")
    set_verts(gob, gv + total)
    return gv + total


def smooth_region(obj_name, center, radius=0.030, iters=10, lam=0.5):
    """指定球内の頂点をラプラシアン平滑化して局所的な折れを均す。

    紐がバンドへ合流する所は元のトポロジが急に曲がっていて三角のフラップが飛び出す。
    ライン移動では直らないので、その周辺だけ均す。縮みを抑えるため往復（Taubin）で回す。
    """
    ob = bpy.data.objects[obj_name]
    gv = obj_verts(ob)
    c = np.array(center, dtype=float)
    d = np.linalg.norm(gv - c, axis=1)
    w = np.clip(1.0 - d / radius, 0.0, 1.0)          # 中心1 → 縁0
    if not (w > 0).any():
        print("@@@ SMOOTH 対象なし"); return gv
    nb = edge_neighbors(ob.data)
    before = gv.copy()
    for k in range(iters):
        f = lam if k % 2 == 0 else -0.53 * lam        # Taubin λ/μ
        nv = gv.copy()
        for i in np.nonzero(w > 0)[0]:
            ns = nb[i]
            if ns:
                nv[i] = gv[i] + f * w[i] * (gv[ns].mean(axis=0) - gv[i])
        gv = nv
    set_verts(ob, gv)
    moved = np.linalg.norm(gv - before, axis=1)
    print(f"@@@ SMOOTH {obj_name} 対象 {int((w>0).sum())} 頂点 移動 max={moved.max()*1000:.1f}mm "
          f"median={np.median(moved[w>0])*1000:.2f}mm")
    return gv


SWIM_RGBA = (0.045, 0.045, 0.05, 1.0)   # extract_swimwear.py と同じ（リニア）


def _resample(path, n):
    """折れ線を弧長等間隔で n 点に再サンプルする。"""
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    s = np.linspace(0.0, cum[-1], n)
    return np.stack([np.interp(s, cum, path[:, k]) for k in range(3)], axis=1)


def _frames(path):
    """平行移動フレーム（parallel transport）。断面の向きが回らない＝ねじれない。"""
    tg = np.gradient(path, axis=0)
    tg /= np.linalg.norm(tg, axis=1)[:, None]
    up = np.array([0.0, 0.0, 1.0])
    n0 = np.cross(tg[0], up)
    if np.linalg.norm(n0) < 1e-6:
        n0 = np.cross(tg[0], np.array([1.0, 0.0, 0.0]))
    n0 /= np.linalg.norm(n0)
    ns = [n0]
    for i in range(1, len(path)):
        v = ns[-1] - tg[i] * (ns[-1] @ tg[i])      # 前の法線を接線に直交化
        nv = np.linalg.norm(v)
        ns.append(v / nv if nv > 1e-9 else ns[-1])
    ns = np.array(ns)
    bs = np.cross(tg, ns)
    return tg, ns, bs


def _outward_dirs(path, model="female", pad=0.06):
    """経路の各点で体表から外向きの方向を求める（最近傍の体表点から見た向き）。
    平たい紐の「厚み方向」をこれに合わせると、体に貼り付いたリボンになる。"""
    from mathutils.kdtree import KDTree
    z0, z1 = path[:, 2].min() - pad, path[:, 2].max() + pad
    pts = []
    for cn in SURFACE_COLS[model]:
        for o in col_objs(cn):
            a = eval_world_verts([o])
            if len(a):
                a = a[(a[:, 2] >= z0) & (a[:, 2] <= z1)]
                if len(a):
                    pts.append(a)
    pts = np.concatenate(pts)
    stride = max(1, len(pts) // 250000)
    pts = pts[::stride]
    kd = KDTree(len(pts))
    for i, q in enumerate(pts):
        kd.insert(Vector(q), i)
    kd.balance()
    out = np.zeros_like(path)
    for i, q in enumerate(path):
        co, idx, d = kd.find(Vector(q))
        v = np.array(q) - np.array(co)
        n = np.linalg.norm(v)
        out[i] = v / n if n > 1e-6 else np.array([0.0, 0.0, 1.0])
    # 方向が点ごとに暴れないようならす
    for _ in range(6):
        sm = out.copy()
        sm[1:-1] = (out[:-2] + 2 * out[1:-1] + out[2:]) / 4.0
        out = sm / np.linalg.norm(sm, axis=1)[:, None]
    return out


def rebuild_strap(side, i_tube=(0, 15), i_del=(1, 14), ring=12, samples=48,
                  radius=None, del_r=0.030, section=None, model="female"):
    """肩紐を「編集済みラインに沿った一定断面の筒」に作り直す。

    元のビキニトップの紐は途中で筒から平たいリボンへ変化する造形で、断面の向きが
    回転している（＝ねじれ）。頂点移動や平滑化では直らないため、区間ごと差し替える。
      1) ライン上の弧長 i_del 区間にある紐頂点を削除
      2) それで空いた開口だけを塞ぐ（襟ぐり・アームホール等の元からの開口は残す）
      3) ライン i_tube 区間に沿って筒を生成。断面の向きは parallel transport で
         運ぶのでねじれない。両端はカップ／バンドへ数mm差し込んで重ねる
    """
    import bmesh
    gob = bpy.data.objects["Swimwear_Top"]
    pts = _line_points(side)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    T = np.concatenate([[0.0], np.cumsum(seg)]); T /= T[-1]

    gv = obj_verts(gob)
    same = (gv[:, 0] > 0) if side == "左" else (gv[:, 0] < 0)
    t_arr = np.full(len(gv), -1.0); d_arr = np.full(len(gv), 9.9)
    for i in np.nonzero(same)[0]:
        t_arr[i], d_arr[i] = _polyline_project(pts, gv[i])
    doomed = same & (d_arr < del_r) & (t_arr > T[i_del[0]]) & (t_arr < T[i_del[1]])
    if radius is None:
        radius = float(np.median(d_arr[doomed]))
    print(f"@@@ REBUILD {side} 削除 {int(doomed.sum())} 頂点 / 断面半径 {radius*1000:.1f}mm")

    bm = bmesh.new(); bm.from_mesh(gob.data); bm.verts.ensure_lookup_table()
    was_boundary = {(e.verts[0].co.copy().freeze(), e.verts[1].co.copy().freeze())
                    for e in bm.edges if len(e.link_faces) == 1}
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.nonzero(doomed)[0]], context='VERTS')
    bm.edges.ensure_lookup_table()
    new_bnd = [e for e in bm.edges if len(e.link_faces) == 1
               and (e.verts[0].co.copy().freeze(), e.verts[1].co.copy().freeze()) not in was_boundary
               and (e.verts[1].co.copy().freeze(), e.verts[0].co.copy().freeze()) not in was_boundary]
    # 連結成分ごとに分ける（カップ側の縁とバンド側の縁）
    loops, seen = [], set()
    for e in new_bnd:
        if e in seen:
            continue
        comp, stack = [], [e]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x); comp.append(x)
            for v in x.verts:
                for y in v.link_edges:
                    if y in new_bnd and y not in seen:
                        stack.append(y)
        loops.append(comp)
    print(f"@@@ REBUILD {side} 開口 {len(loops)} 個 (辺数 {[len(c) for c in loops]})")

    path = _resample(pts[i_tube[0]:i_tube[1] + 1], samples)
    tg, ns, bs = _frames(path)
    ang = np.linspace(0, 2 * math.pi, ring, endpoint=False)
    if section is None:
        axes = [(radius * ns[k], radius * bs[k]) for k in range(samples)]   # 円
    else:
        # 楕円: 短軸=体表の法線方向（厚み）、長軸=体表に沿う方向（幅）。
        # 元の紐は厚み1.2〜2.0mm・幅11〜18mm のほぼ平らなリボン（実測）。
        a_half, b_half = section
        outw = _outward_dirs(path, model)
        axes = []
        for k in range(samples):
            minor = outw[k] - tg[k] * (outw[k] @ tg[k])
            n = np.linalg.norm(minor)
            minor = minor / n if n > 1e-9 else bs[k]
            major = np.cross(minor, tg[k])
            major /= np.linalg.norm(major)
            axes.append((a_half * major, b_half * minor))
        print(f"@@@ REBUILD {side} 断面 楕円 幅{a_half*2000:.1f}mm x 厚み{b_half*2000:.1f}mm")
    rings = []
    for k in range(samples):
        u, v = axes[k]
        rings.append([bm.verts.new(path[k] + math.cos(a) * u + math.sin(a) * v) for a in ang])
    for k in range(samples - 1):
        for j in range(ring):
            j2 = (j + 1) % ring
            bm.faces.new((rings[k][j], rings[k][j2], rings[k + 1][j2], rings[k + 1][j]))
    # 端は蓋をせず、開口の縁へ橋渡しして連続させる。
    # 蓋＋差し込みだと接合部に n-gon の平面と筒の端が重なって汚くなる（ユーザー指摘）。
    def ring_edges(r):
        es = []
        for j in range(ring):
            e = bm.edges.get((r[j], r[(j + 1) % ring]))
            if e: es.append(e)
        return es
    bridged = 0
    for r in (rings[0], rings[-1]):
        c = np.mean([list(v.co) for v in r], axis=0)
        if not loops:
            break
        li = min(range(len(loops)), key=lambda i: np.linalg.norm(
            np.mean([list(v.co) for e in loops[i] for v in e.verts], axis=0) - c))
        try:
            bmesh.ops.bridge_loops(bm, edges=ring_edges(r) + loops[li])
            bridged += 1
        except Exception as ex:
            print(f"@@@ REBUILD {side} bridge 失敗 -> 蓋で代用: {ex}")
            bm.faces.new(r)
        loops.pop(li)
    print(f"@@@ REBUILD {side} 接合部を {bridged} 箇所ブリッジ")
    bm.normal_update()
    bm.to_mesh(gob.data); bm.free()
    me = gob.data
    me.update()
    attr = me.color_attributes.get("Col") or me.color_attributes.new(
        name="Col", type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set("color", list(SWIM_RGBA) * len(me.vertices))
    me.update()
    print(f"@@@ REBUILD {side} 完了 verts={len(me.vertices)} faces={len(me.polygons)}")


def make_strap_line(n_strap=12, n_band=7, z_split=1.405, x_min=0.030, y_back=0.080):
    """肩紐＋背面バンドの中心線を CURRENT_<側>肩紐ライン として引き、現在座標を保存する。

    経路は 胸(カップ上縁) → 肩の上 → 背面を下る → 背中の水平バンド → 正中 の1本。
    パラメータの取り方を2段に分けている：
      肩紐部  … Y が単調増加（前→肩→後）なので Y で等分
      バンド部… 背面の下降で Z が減り、正中へ向かって X も減るので Z+X で等分
    ※ このモデルは **+X がモデルの左**（右精巣 X<0 / 左精巣 X>0 で確認済み）。
    """
    import json
    gob = bpy.data.objects["Swimwear_Top"]
    gv = obj_verts(gob)
    out = {"object": "Swimwear_Top", "z_split": z_split, "x_min": x_min,
           "note": "+X=モデルの左。点順は 胸→肩→背面→正中", "straps": {}}

    for side, sgn in (("左", 1.0), ("右", -1.0)):
        pts = _centerline_points(gv, sgn, n_strap, n_band, z_split, x_min, y_back)
        name = f"CURRENT_{side}肩紐ライン"
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        cu = bpy.data.curves.new(name, 'CURVE')
        cu.dimensions = '3D'; cu.bevel_depth = 0.0035; cu.resolution_u = 2
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, q in enumerate(pts):
            sp.points[i].co = (q[0], q[1], q[2], 1.0)
        ob = bpy.data.objects.new(name, cu)
        ob.show_in_front = True
        bpy.context.scene.collection.objects.link(ob)
        out["straps"][side] = {"prev": [[float(v) for v in q] for q in pts]}
        print(f"@@@ {name} {len(pts)}点（肩紐{n_strap}+バンド{n_band}）")
        for i, q in enumerate(pts):
            print(f"    {i:2d} ({q[0]:+.4f}, {q[1]:+.4f}, {q[2]:+.4f})")
    json.dump(out, open(STRAP_JSON, "w", encoding="utf-8"), ensure_ascii=False)
    print("@@@ SAVED", STRAP_JSON)


def _polyline_project(pts_line, v):
    """折れ線上の最近点を返す (弧長パラメータ t[0..1], 距離 d)。"""
    best = (1e9, 0.0)
    total = np.linalg.norm(np.diff(pts_line, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(total)])
    for i in range(len(pts_line) - 1):
        a, b = pts_line[i], pts_line[i + 1]
        ab = b - a
        L2 = float(ab @ ab)
        s = 0.0 if L2 < 1e-12 else float(np.clip((v - a) @ ab / L2, 0.0, 1.0))
        q = a + ab * s
        d = float(np.linalg.norm(v - q))
        if d < best[0]:
            best = (d, (cum[i] + s * total[i]) / max(cum[-1], 1e-9))
    return best[1], best[0]


def apply_strap_edit(sides=("左",), mirror_to_other=True, r0=0.030, r1=0.075):
    """デバッグライン(CURRENT_<側>肩紐ライン)の編集差分を下着メッシュへ適用する。

    ライン13点の変位を弧長で補間し、ラインからの距離で 1→0 にフェードさせて当てる。
    紐の頂点だけを動かすとカップ/バンドとの境目に段差が出るので、フェードで逃がす。
    """
    import json
    D = json.load(open(STRAP_JSON, encoding="utf-8"))
    gob = bpy.data.objects[D["object"]]
    gv = obj_verts(gob)
    total = np.zeros_like(gv)

    for side in sides:
        ob = bpy.data.objects[f"CURRENT_{side}肩紐ライン"]
        cur = np.array([list(ob.matrix_world @ Vector(p.co[:3]))
                        for p in ob.data.splines[0].points])
        prev = np.array(D["straps"][side]["prev"])
        if len(cur) != len(prev):
            raise SystemExit(f"{side}: 点数が変わっている prev={len(prev)} cur={len(cur)}")
        delta = cur - prev
        ts = np.linspace(0.0, 1.0, len(prev))
        for sgn, dl in ((1.0, delta), (-1.0, delta * np.array([-1, 1, 1]))):
            if sgn < 0 and not mirror_to_other:
                continue
            line = prev.copy()
            if sgn < 0:
                line[:, 0] *= -1                      # 反対側へミラーした基準線
            same = (gv[:, 0] > 0) == (line[0, 0] > 0)  # 同じ側の頂点だけ動かす
            for i in np.nonzero(same)[0]:
                t, d = _polyline_project(line, gv[i])
                if d >= r1:
                    continue
                w = 1.0 if d <= r0 else 0.5 * (1 + math.cos(math.pi * (d - r0) / (r1 - r0)))
                total[i] += np.array([np.interp(t, ts, dl[:, k]) for k in range(3)]) * w
        n = int((np.linalg.norm(total, axis=1) > 1e-6).sum())
        print(f"@@@ STRAP {side} 適用 {n}/{len(gv)} 頂点 "
              f"max={np.linalg.norm(total,axis=1).max()*1000:.1f}mm"
              f"{' (反対側へミラー込み)' if mirror_to_other else ''}")
    set_verts(gob, gv + total)
    return gv + total


def verify(name, gob, hmap, ayf):
    gv = obj_verts(gob)
    ay = ayf(gv[:, 2])
    bad = []
    for i in range(len(gv)):
        dx = gv[i, 0]; dy = gv[i, 1] - ay[i]
        r = math.hypot(dx, dy)
        if r < 0.025:
            continue
        R = hmap.max_r(dx, dy, gv[i, 2])
        if R is not None and R > r:
            bad.append((R - r) * 1000)
    if bad:
        b = np.array(bad)
        print(f"@@@ VERIFY {name} 体がはみ出す点 {len(b)}/{len(gv)} "
              f"p90={np.percentile(b,90):.2f} max={b.max():.2f} mm")
    else:
        print(f"@@@ VERIFY {name} はみ出しゼロ（体表は全周で下着の内側）")
    print(f"@@@ VERIFY {name} bbox=({gv[:,0].min():.4f},{gv[:,1].min():.4f},{gv[:,2].min():.4f})-"
          f"({gv[:,0].max():.4f},{gv[:,1].max():.4f},{gv[:,2].max():.4f})")


# 覆うべき Z 範囲（ワールド絶対値）。実測で決める。
#  male Bottom : 外性器 Z 0.6896〜0.8610（生殖器コレクション実測）＋ 皮膚側の膨らみ Z 0.70〜0.76。
#                下端は陰嚢の下、上端は恥骨上のブリーフらしい高さ（腰のくびれ z≈1.04 の手前）。
# z = 覆うべきワールド Z 範囲、xscale = 水平スケールを定数で与える（省略時は Z 依存）。
#  female は A ポーズの腕が胴体に接しており、z>=1.02（前腕・手）と z>=1.28（上腕）で
#  断面幅が腕に汚染される（実測 0.131 -> 0.212）。Z 依存幅を使うと下着が腕まで膨らむので、
#  汚染の無い高さで測った定数を使う。male の骨盤帯は汚染が無いので Z 依存のまま。
#  xtorso = その帯での胴体半幅の上限。これより外の体表（腕・手・三角筋）は押し出しの
#  基準から外す。胸の高さでは胴体が細い（女性で半幅0.15）ので帯ごとに変える。
SPEC = {
    "male":   {"Swimwear_Bottom": {"z": (0.645, 0.878), "xtorso": 0.200}},
    "female": {"Swimwear_Bottom": {"z": (0.855, 1.035), "xscale": 1.045, "xtorso": 0.190},
               "Swimwear_Top":    {"z": (1.282, 1.529), "xscale": 1.00,  "xtorso": 0.155}},
}


def fit(model, frame=None, spec=None, push=True):
    """append → 位置合わせ → 押し出し。spec={'Swimwear_Bottom': (z0, z1)} で覆う高さを指定。"""
    src = load_source(fresh=True)
    f = frame or measure(model)
    sp, tp = f["src_prof"], f["tgt_prof"]
    tgt_pts = f.get("tgt_pts")
    if tgt_pts is None:
        tgt_pts = eval_world_verts(surface_objs(model))
    ayf = axis_y_fn(tp)
    spec = dict(SPEC[model], **(spec or {}))

    for name in GARMENTS[model]:
        gob = src[name]
        gv = obj_verts(gob)
        sz0, sz1 = gv[:, 2].min(), gv[:, 2].max()
        opt = spec[name]
        tz0, tz1 = opt["z"]
        sz = (tz1 - tz0) / (sz1 - sz0)
        zt = (gv[:, 2] - sz0) * sz + tz0            # 各頂点の移動後 Z
        szs, sxw, sycen = smooth_prof(sp)
        tzs, txw, tycen = smooth_prof(tp)
        # 幅は既定で Z 依存（単一スケールだと体が細くなる腰の上端で下着の角が 14mm 飛び出す）。
        # 前後中心は 1 点だけ使う（Z 依存にすると断面中心の波打ちが下着を歪める）。
        if "xscale" in opt:
            sxz = np.full(len(gv), float(opt["xscale"]))
        else:
            sxz = np.interp(zt, tzs, txw) / np.interp(gv[:, 2], szs, sxw)
        scy = float(np.interp((sz0 + sz1) / 2, szs, sycen))
        tcy = float(np.interp((tz0 + tz1) / 2, tzs, tycen))
        print(f"@@@ FIT {name} z {sz0:.4f}..{sz1:.4f} -> {tz0:.4f}..{tz1:.4f} sz={sz:.4f}")
        print(f"@@@   xscale(z) min={sxz.min():.4f} max={sxz.max():.4f} med={np.median(sxz):.4f} "
              f"ycen {scy:+.4f}->{tcy:+.4f}")

        gv[:, 0] *= sxz
        gv[:, 1] = (gv[:, 1] - scy) * sxz + tcy
        gv[:, 2] = zt
        print(f"@@@ PLACED {name} bbox=({gv[:,0].min():.4f},{gv[:,1].min():.4f},{gv[:,2].min():.4f})-"
              f"({gv[:,0].max():.4f},{gv[:,1].max():.4f},{gv[:,2].max():.4f})")
        set_verts(gob, gv)

        for _ in range(SUBDIV):
            bm = bmesh.new(); bm.from_mesh(gob.data)
            bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
            bm.to_mesh(gob.data); bm.free(); gob.data.update()
        if SUBDIV:
            print(f"@@@ SUBDIV {name} -> {len(gob.data.vertices)} verts")
            gv = obj_verts(gob)

        if push:
            lc = list(LEG_CUT[model])
            lc[3] = opt.get("xtorso", lc[3])
            hmap = HeightMap(tgt_pts, ayf, gv[:, 2].min(), gv[:, 2].max(), legcut=tuple(lc),
                             no_box=NO_PUSH_BOX.get(model) if USE_NO_BOX else None)
            gv = push_pass(name, gob, gv, hmap, ayf, "pass1"); set_verts(gob, gv)
            gv = push_pass(name, gob, obj_verts(gob), hmap, ayf, "pass2"); set_verts(gob, gv)
            gv = pull_pass(name, gob, obj_verts(gob), hmap, ayf); set_verts(gob, gv)
            verify(name, gob, hmap, ayf)
    return f


def dense_points(objs, per_tri=10):
    """メッシュ面上に点をばらまく。頂点だけだと (θ,z) 格子に穴が開き、
    被覆率が実際より低く出る（下着 2889 頂点で 14% と誤判定した）。"""
    # 三角形の重心座標サンプル（決定論・面積によらず一定数）
    bc = []
    k = 0
    while len(bc) < per_tri:
        k += 1
        for i in range(k + 1):
            for j in range(k + 1 - i):
                bc.append(((i + 1) / (k + 3), (j + 1) / (k + 3),
                           1 - (i + 1) / (k + 3) - (j + 1) / (k + 3)))
        bc = [b for b in bc if b[2] > 0]
    bc = np.array(bc[:per_tri])
    out = []
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        n = len(me.vertices)
        a = np.empty(n * 3); me.vertices.foreach_get("co", a); a = a.reshape(n, 3)
        m = np.array(o.matrix_world)
        a = a @ m[:3, :3].T + m[:3, 3]
        t = np.empty(len(me.loop_triangles) * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("vertices", t)
        tri = a[t.reshape(-1, 3)]                       # (T,3,3)
        out.append(a)
        for w in bc:
            out.append(tri[:, 0] * w[0] + tri[:, 1] * w[1] + tri[:, 2] * w[2])
    return np.concatenate(out)


def coverage(model, garment_names, target_names, label=""):
    """「隠したい部位が下着の内側にあるか」を数値で測る。

    下着から (θ,z) ハイトマップを作り、対象（乳房 / 生殖器）の各頂点について
    その方位・高さの下着半径が頂点半径以上かを見る。正射カメラは水平に見るので
    これがそのまま「その方向から見えていないか」になる。
    """
    f = measure(model, verbose=False)
    ayf = axis_y_fn(f["tgt_prof"])
    gp = dense_points([bpy.data.objects[n] for n in garment_names])
    tp_ = eval_world_verts([bpy.data.objects[n] for n in target_names])
    hm = HeightMap(gp, ayf, gp[:, 2].min(), gp[:, 2].max(), pad=0.0)
    ay = ayf(tp_[:, 2])
    cov = 0; out = []
    for i in range(len(tp_)):
        dx = tp_[i, 0]; dy = tp_[i, 1] - ay[i]
        r = math.hypot(dx, dy)
        R = hm.max_r(dx, dy, tp_[i, 2], wt=1, wz=1)
        if R is not None and R >= r:
            cov += 1
        else:
            out.append(tp_[i])
    pct = 100.0 * cov / max(len(tp_), 1)
    print(f"@@@ COVERAGE {label or target_names} {cov}/{len(tp_)} = {pct:.1f}%")
    if out:
        o = np.array(out)
        print(f"@@@   露出部 bbox=({o[:,0].min():.4f},{o[:,1].min():.4f},{o[:,2].min():.4f})-"
              f"({o[:,0].max():.4f},{o[:,1].max():.4f},{o[:,2].max():.4f})")
    return pct


def raise_waist(name, target_z, model="male", front_deg=110.0, blend=0.09, nbin=48):
    """上端（ウエスト）の縁を持ち上げて前面の被覆を広げる。

    元がビキニボトムなので前中央が V 字に切れ上がっており（実測 z=0.782、腰の側面は
    0.877）、外性器の上端 z=0.861 より低い＝根元が出る。前面側の縁だけを target_z まで
    上げ、下へ blend の範囲でなだらかに戻す（縁だけ動かすと段差になるため）。
    """
    f = measure(model, verbose=False)
    ayf = axis_y_fn(f["tgt_prof"])
    gob = bpy.data.objects[name]
    gv = obj_verts(gob)
    ay = ayf(gv[:, 2])
    th = np.arctan2(gv[:, 1] - ay, gv[:, 0])          # -Y が前 → th≈-90° が前
    front = np.cos(th + math.pi / 2)                  # 前=+1, 後=-1
    # 現在の上端 z を方位ごとに把握
    bi = np.clip(((th + math.pi) / (2 * math.pi) * nbin).astype(int), 0, nbin - 1)
    edge = np.full(nbin, np.nan)
    for b in range(nbin):
        m = bi == b
        if m.any():
            edge[b] = gv[m, 2].max()
    ok = ~np.isnan(edge)
    edge[~ok] = np.interp(np.nonzero(~ok)[0], np.nonzero(ok)[0], edge[ok])
    for _ in range(4):        # 方位方向に円環で平滑化（生の最大値はギザギザになる）
        edge = (np.roll(edge, 1) + 2 * edge + np.roll(edge, -1)) / 4.0
    lim = math.cos(math.radians(front_deg / 2))       # 前面セクターの範囲
    lift = np.zeros(len(gv))
    for i in range(len(gv)):
        if front[i] < lim:
            continue
        e = edge[bi[i]]
        need = target_z - e
        if need <= 0:
            continue
        w = np.clip((gv[i, 2] - (e - blend)) / blend, 0.0, 1.0)          # 縁ほど大きく
        s = (front[i] - lim) / (1.0 - lim)                               # 側面へ向けて0
        lift[i] = need * w * (0.5 * (1 - math.cos(math.pi * s)))
    nb = edge_neighbors(gob.data)                     # メッシュ上でもならす
    for _ in range(5):
        nl = lift.copy()
        for i, ns in enumerate(nb):
            if ns:
                nl[i] = 0.4 * lift[i] + 0.6 * float(np.mean(lift[ns]))
        lift = nl
    gv[:, 2] += lift
    set_verts(gob, gv)
    print(f"@@@ RAISE {name} 前縁 -> z={target_z:.3f} 適用 {int((lift>1e-6).sum())} 頂点 "
          f"max={lift.max()*1000:.1f}mm")
    return gv


BRIEF_JSON = os.path.join(HERE, "brief_outline.json")
# ブリーフ輪郭の既定値（男性・ワールドZ）。front=前中央, side=真横, back=後中央。
BRIEF_OUTLINE = {
    "male": {"waist": {"front": 0.885, "side": 0.885, "back": 0.880},
             "hem":   {"front": 0.660, "side": 0.800, "back": 0.735},
             "power": 1.6},
}
# 女性ブラ（バンド型）。generate_brief は「上端線と下端線の間に面を張る」だけなので
# 上下どちらの下着にも使える。乳房 Breast_Base は z 1.2881〜1.4366 なので、
# 上端はその上・下端はその下に置けば肌色が一切出ない。
BRA_OUTLINE = {
    "female": {"waist": {"front": 1.452, "side": 1.448, "back": 1.430},   # 上端
               "hem":   {"front": 1.268, "side": 1.276, "back": 1.286},   # 下端
               "power": 1.4},
}


def add_tube(obj_name, path_pts, section=(0.0065, 0.0013), ring=12, samples=48,
             model="female"):
    """既存オブジェクトへ、指定経路に沿った楕円断面の筒を足す（肩紐用）。

    断面の厚み方向は体表の法線、向きは parallel transport なのでねじれない。
    両端は本体へ差し込んで重ねる（単色なので継ぎ目は見えない）。
    """
    import bmesh
    gob = bpy.data.objects[obj_name]
    path = _resample(np.array(path_pts, dtype=float), samples)
    tg, ns, bs = _frames(path)
    a_half, b_half = section
    outw = _outward_dirs(path, model)
    bm = bmesh.new(); bm.from_mesh(gob.data)
    ang = np.linspace(0, 2 * math.pi, ring, endpoint=False)
    rings = []
    for k in range(samples):
        minor = outw[k] - tg[k] * (outw[k] @ tg[k])
        n = np.linalg.norm(minor)
        minor = minor / n if n > 1e-9 else bs[k]
        major = np.cross(minor, tg[k]); major /= np.linalg.norm(major)
        u, v = a_half * major, b_half * minor
        rings.append([bm.verts.new(path[k] + math.cos(t) * u + math.sin(t) * v) for t in ang])
    for k in range(samples - 1):
        for j in range(ring):
            j2 = (j + 1) % ring
            bm.faces.new((rings[k][j], rings[k][j2], rings[k + 1][j2], rings[k + 1][j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bm.normal_update()
    bm.to_mesh(gob.data); bm.free()
    me = gob.data
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    attr = me.color_attributes.get("Col") or me.color_attributes.new(
        name="Col", type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set("color", list(SWIM_RGBA) * len(me.vertices))
    me.update()
    print(f"@@@ TUBE {obj_name} 追加 -> verts={len(me.vertices)} faces={len(me.polygons)}")


def outline_from_target(model, target_names, top_margin=0.012, bot_margin=0.012,
                        fallback_top=1.400, fallback_bot=1.300, nbin=48, smooth=3):
    """隠したい部位（乳房など）の実形状から輪郭テーブルを作る。

    前/横/後の3値だけで決めると、乳房の輪郭に合わず「黒い箱」になる（実測・目視）。
    方位ごとに対象の最上端・最下端を測り、そこへ余裕を足した線を輪郭にすると、
    被覆を保ったまま体の形に沿った下着になる。対象が無い方位は fallback（背中のバンド）。
    """
    f = measure(model, verbose=False)
    ayf = axis_y_fn(f["tgt_prof"])
    pts = eval_world_verts([bpy.data.objects[n] for n in target_names])
    th = np.degrees(np.arctan2(pts[:, 1] - ayf(pts[:, 2]), pts[:, 0]))
    bi = np.clip(((th + 180.0) / 360.0 * nbin).astype(int), 0, nbin - 1)
    top = np.full(nbin, np.nan); bot = np.full(nbin, np.nan)
    for b in range(nbin):
        m = bi == b
        if m.any():
            top[b] = pts[m, 2].max(); bot[b] = pts[m, 2].min()
    # 対象が無い方位（背中側など）は fallback をそのまま使う＝覆う必要が無いので細くできる。
    # 対象がある方位だけ「実形状＋余裕」まで広げる。
    has = ~np.isnan(top)
    top = np.where(has, np.maximum(top + top_margin, fallback_top), fallback_top)
    bot = np.where(has, np.minimum(bot - bot_margin, fallback_bot), fallback_bot)
    for _ in range(smooth):
        top = (np.roll(top, 1) + 2 * top + np.roll(top, -1)) / 4.0
        bot = (np.roll(bot, 1) + 2 * bot + np.roll(bot, -1)) / 4.0
    deg = -180.0 + (np.arange(nbin) + 0.5) * (360.0 / nbin)
    print(f"@@@ OUTLINE 対象から算出 上端 z[{top.min():.3f},{top.max():.3f}] "
          f"下端 z[{bot.min():.3f},{bot.max():.3f}]")
    return {"waist": {"table": [[float(a), float(b)] for a, b in zip(deg, top)]},
            "hem":   {"table": [[float(a), float(b)] for a, b in zip(deg, bot)]},
            "power": 1.0}


def _outline_fn(d, power):
    """輪郭 z(θ) を返す。θ は atan2(y-ay, x)、前が -90°。
    table があれば方位→z の折れ線（周期360°）、無ければ前/横/後の3値から作る。"""
    if "table" in d:
        t = np.array(d["table"], dtype=float)
        o = np.argsort(t[:, 0]); dg, zz = t[o, 0], t[o, 1]
        return lambda th: np.interp(np.degrees(th), dg, zz, period=360.0)

    def f(th):
        a = -np.sin(th)                     # 前=+1, 後=-1, 真横=0
        fw = np.clip(a, 0, None) ** power
        bw = np.clip(-a, 0, None) ** power
        return d["side"] + (d["front"] - d["side"]) * fw + (d["back"] - d["side"]) * bw
    return f


def generate_brief(model="male", name="Swimwear_Brief", n_theta=96, n_v=28,
                   clearance=0.007, outline=None, legcut_xtorso=0.20,
                   tan_cut=0.0, smooth=6, wt=5, wz=3,
                   gusset=False, gusset_hw=0.045, gusset_rise=0.010):
    """体表に沿ったブリーフを生成する。

    元のビキニボトムを引き伸ばして男性用にするのは、前を上げ・後ろを下げ・幅を出すと
    全周を大きく引っ張ることになり、直すたび別の場所が裂けた（実測）。
    ここでは体表のハイトマップ（各方位・各高さの体の最大半径）の上に
    「体表＋クリアランス」の面を直接張る。フィットは原理的に破綻しない。
    輪郭は waist(θ) と hem(θ) の2本で決まり、両方あとから編集できる。
    """
    import bmesh
    o = outline or BRIEF_OUTLINE[model]
    f = measure(model, verbose=False)
    ayf = axis_y_fn(f["tgt_prof"])
    W = _outline_fn(o["waist"], o["power"])
    H = _outline_fn(o["hem"], o["power"])
    th = np.linspace(-math.pi, math.pi, n_theta, endpoint=False)
    wline, hline = W(th), H(th)
    zlo = float(np.min(hline)) - 0.02
    zhi = float(np.max(wline)) + 0.02
    # 真横セクターの除外は使わない（tan_cut=0）。ブリーフの脚ぐりは太腿を巻くので、
    # 太腿を体表から外すと脚ぐりの高さ(z≈0.80)が除外境界と重なって筋・ギザギザが出る。
    lc = (LEG_CUT[model][0], LEG_CUT[model][1], tan_cut, legcut_xtorso)
    hm = HeightMap(f["tgt_pts"], ayf, zlo, zhi, legcut=lc)
    grid = np.zeros((n_theta, n_v, 3))
    rad = np.zeros((n_theta, n_v))
    for i in range(n_theta):
        for j in range(n_v):
            z = wline[i] + (hline[i] - wline[i]) * (j / (n_v - 1))
            R = hm.max_r(math.cos(th[i]), math.sin(th[i]), z, wt=wt, wz=wz)
            rad[i, j] = R if R is not None else np.nan
    # 体表が取れなかったセル（腿を除外した方位など）は方位方向に補間して埋める
    for j in range(n_v):
        col = rad[:, j]
        ok = ~np.isnan(col)
        if ok.sum() < 3:
            col[:] = np.nanmax(rad) if np.isfinite(np.nanmax(rad)) else 0.12
        else:
            idx = np.arange(n_theta)
            col[~ok] = np.interp(idx[~ok], idx[ok], col[ok], period=n_theta)
        rad[:, j] = col
    # 方位・縦の両方向にならして布らしくする（体表の細かい凹凸を拾わない）
    for _ in range(smooth):
        rad = (np.roll(rad, 1, 0) + 2 * rad + np.roll(rad, -1, 0)) / 4.0   # θ方向は円環
        pad = np.concatenate([rad[:, :1], rad, rad[:, -1:]], axis=1)       # 縦は端を複製
        rad = (pad[:, :-2] + 2 * rad + pad[:, 2:]) / 4.0
    for i in range(n_theta):
        for j in range(n_v):
            z = wline[i] + (hline[i] - wline[i]) * (j / (n_v - 1))
            r = rad[i, j] + clearance
            grid[i, j] = (r * math.cos(th[i]), ayf(z) + r * math.sin(th[i]), z)

    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    bm = bmesh.new()
    vs = [[bm.verts.new(grid[i, j]) for j in range(n_v)] for i in range(n_theta)]
    for i in range(n_theta):
        i2 = (i + 1) % n_theta
        for j in range(n_v - 1):
            bm.faces.new((vs[i][j], vs[i2][j], vs[i2][j + 1], vs[i][j + 1]))
    # 股布（クロッチ）: 体を巻く帯だけだと前後の裾をまたぐ布が無く、股が開いたままになる
    # （ユーザー指摘 2026-08-17）。裾の前弧と後弧を股下でつなぐ面を張る。
    if gusset:
        hemv = np.array([grid[i, n_v - 1] for i in range(n_theta)])
        s = np.sin(th)
        fsel = np.nonzero((s < 0) & (np.abs(hemv[:, 0]) <= gusset_hw))[0]
        bsel = np.nonzero((s > 0) & (np.abs(hemv[:, 0]) <= gusset_hw))[0]
        if len(fsel) >= 2 and len(bsel) >= 2:
            F = hemv[fsel][np.argsort(hemv[fsel][:, 0])]
            B = hemv[bsel][np.argsort(hemv[bsel][:, 0])]
            n_w, n_u = 14, 10
            Fr, Br = _resample(F, n_w), _resample(B, n_w)
            gv2 = [[None] * n_u for _ in range(n_w)]
            for k in range(n_w):
                for m in range(n_u):
                    u = m / (n_u - 1)
                    q = Fr[k] * (1 - u) + Br[k] * u
                    q[2] += gusset_rise * math.sin(math.pi * u)   # 体側へ少し持ち上げる
                    gv2[k][m] = bm.verts.new(q)
            for k in range(n_w - 1):
                for m in range(n_u - 1):
                    bm.faces.new((gv2[k][m], gv2[k + 1][m], gv2[k + 1][m + 1], gv2[k][m + 1]))
            print(f"@@@ BRIEF 股布 前{len(fsel)}列×後{len(bsel)}列 -> {n_w}x{n_u} 面")
        else:
            print(f"@@@ BRIEF 股布スキップ（前{len(fsel)}列 後{len(bsel)}列）")
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    attr = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set("color", list(SWIM_RGBA) * len(me.vertices))
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    import json
    json.dump({"model": model, "outline": o}, open(BRIEF_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"@@@ BRIEF 生成 {name} verts={len(me.vertices)} faces={len(me.polygons)} "
          f"waist={o['waist']} hem={o['hem']}")
    return ob


def _boundary_loops(me):
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me)
    bnd = [e for e in bm.edges if len(e.link_faces) == 1]
    seen, loops = set(), []
    for e in bnd:
        if e in seen:
            continue
        comp, st = [], [e]
        while st:
            x = st.pop()
            if x in seen:
                continue
            seen.add(x); comp.append(x)
            for v in x.verts:
                for y in v.link_edges:
                    if len(y.link_faces) == 1 and y not in seen:
                        st.append(y)
        loops.append(sorted({v.index for e2 in comp for v in e2.verts}))
    bm.free()
    return loops


def lower_leg_opening(name, target_z, model="male", falloff=0.06, post_margin=-0.02):
    """脚ぐりの境界のうち後ろ側を下げて臀部を覆う。

    per-θ の裾最小値で判定すると、同じ方位に股布の低い頂点が入って need≈0 になり効かない
    （実測 3.7mm しか動かなかった）。境界ループそのものを掴んで動かす。
    ウエストの開口は動かさない（3ループのうち最も z が高いものを除外）。
    """
    f = measure(model, verbose=False)
    ayf = axis_y_fn(f["tgt_prof"])
    gob = bpy.data.objects[name]
    gv = obj_verts(gob)
    loops = _boundary_loops(gob.data)
    if len(loops) < 2:
        print("@@@ LOWER 開口が足りない"); return gv
    waist = max(loops, key=lambda L_: gv[L_][:, 2].mean())      # 一番上＝ウエスト
    legs = [L_ for L_ in loops if L_ is not waist]
    anchors, deltas = [], []
    for L_ in legs:
        for i in L_:
            if gv[i, 1] - ayf(gv[i, 2]) > post_margin and gv[i, 2] > target_z:
                anchors.append(i); deltas.append(target_z - gv[i, 2])
    if not anchors:
        print("@@@ LOWER 対象なし"); return gv
    A = gv[anchors]; D = np.array(deltas)
    move = np.zeros(len(gv))
    for i in range(len(gv)):
        d = np.linalg.norm(A - gv[i], axis=1)
        m = d < falloff
        if not m.any():
            continue
        w = 0.5 * (1 + np.cos(math.pi * d[m] / falloff))
        move[i] = float((D[m] * w).sum() / w.sum()) * float(w.max())
    nb = edge_neighbors(gob.data)
    for _ in range(4):
        nm = move.copy()
        for i, ns in enumerate(nb):
            if ns:
                nm[i] = 0.4 * move[i] + 0.6 * float(np.mean(move[ns]))
        move = nm
    gv[:, 2] += move
    set_verts(gob, gv)
    print(f"@@@ LOWER {name} 脚ぐり後ろ側 {len(anchors)} 点を z={target_z:.3f} へ / "
          f"影響 {int((np.abs(move)>1e-6).sum())} 頂点 max={-move.min()*1000:.1f}mm")
    return gv


def lower_hem(name, target_z, model="male", back_deg=170.0, blend=0.09, nbin=48):
    """裾（脚ぐり）の後ろ側を下げて臀部の被覆を広げる。

    元がビキニボトムで脚ぐりが背面 z=0.838 まで切れ上がっており（ハイレグ）、
    臀部が出る。後面セクターだけ裾を target_z まで下げ、上へ blend でなだらかに戻す。
    raise_waist の裾版。
    """
    f = measure(model, verbose=False)
    ayf = axis_y_fn(f["tgt_prof"])
    gob = bpy.data.objects[name]
    gv = obj_verts(gob)
    th = np.arctan2(gv[:, 1] - ayf(gv[:, 2]), gv[:, 0])
    back = -np.cos(th + math.pi / 2)                  # 後=+1, 前=-1
    bi = np.clip(((th + math.pi) / (2 * math.pi) * nbin).astype(int), 0, nbin - 1)
    hem = np.full(nbin, np.nan)
    for b in range(nbin):
        m = bi == b
        if m.any():
            hem[b] = gv[m, 2].min()
    ok = ~np.isnan(hem)
    hem[~ok] = np.interp(np.nonzero(~ok)[0], np.nonzero(ok)[0], hem[ok])
    for _ in range(4):
        hem = (np.roll(hem, 1) + 2 * hem + np.roll(hem, -1)) / 4.0
    lim = math.cos(math.radians(back_deg / 2))
    drop = np.zeros(len(gv))
    for i in range(len(gv)):
        if back[i] < lim:
            continue
        h = hem[bi[i]]
        need = h - target_z
        if need <= 0:
            continue
        w = np.clip(((h + blend) - gv[i, 2]) / blend, 0.0, 1.0)           # 裾ほど大きく
        s = (back[i] - lim) / (1.0 - lim)
        drop[i] = need * w * (0.5 * (1 - math.cos(math.pi * s)))
    nb = edge_neighbors(gob.data)
    for _ in range(5):
        nd = drop.copy()
        for i, ns in enumerate(nb):
            if ns:
                nd[i] = 0.4 * drop[i] + 0.6 * float(np.mean(drop[ns]))
        drop = nd
    gv[:, 2] -= drop
    set_verts(gob, gv)
    print(f"@@@ LOWER {name} 後ろ裾 -> z={target_z:.3f} 適用 {int((drop>1e-6).sum())} 頂点 "
          f"max={drop.max()*1000:.1f}mm")
    return gv


def look(show, center, dist, view="front", color='VERTEX'):
    """ビューポートで対象だけを表示して視点を合わせる（目視確認用）。

    既存データは目玉(hide_set)とモニタ(hide_viewport)が混在しているので両方触る
    （プロジェクト CLAUDE.md）。
    """
    from mathutils import Quaternion
    global _VIS_BACKUP
    if _VIS_BACKUP is None:                      # 最初の look() の時点の表示状態を控える
        _VIS_BACKUP = {o.name: (o.hide_viewport, o.hide_get())
                       for o in bpy.context.scene.objects}
    keep = set(show)
    for o in bpy.context.scene.objects:
        vis = o.name in keep
        o.hide_viewport = not vis
        try:
            o.hide_set(not vis)
        except RuntimeError:
            pass
    q = {"front":   Quaternion((0.70710678, 0.70710678, 0.0, 0.0)),
         "back":    Quaternion((0.0, 0.0, 0.70710678, 0.70710678)),
         "right":   Quaternion((0.5, 0.5, 0.5, 0.5)),
         "front34": Quaternion((0, 0, 1), math.radians(-35)) @ Quaternion((0.70710678, 0.70710678, 0.0, 0.0)),
         }[view]
    for area in bpy.context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        sp = area.spaces[0]
        sp.shading.type = 'SOLID'
        sp.shading.color_type = color
        sp.shading.show_xray = False
        sp.overlay.show_overlays = False
        r = sp.region_3d
        r.view_perspective = 'ORTHO'
        r.view_rotation = q
        r.view_location = Vector(center)
        r.view_distance = dist
    print(f"@@@ LOOK {view} shown={len(keep)} center={tuple(round(c,3) for c in center)} dist={dist}")


def restore_view():
    """look() を呼ぶ前の表示状態へ厳密に戻す。"""
    global _VIS_BACKUP
    if not _VIS_BACKUP:
        print("@@@ nothing to restore")
        return
    for o in bpy.context.scene.objects:
        st = _VIS_BACKUP.get(o.name)
        if st is None:
            continue
        o.hide_viewport = st[0]
        try:
            o.hide_set(st[1])
        except RuntimeError:
            pass
    print(f"@@@ restored visibility for {len(_VIS_BACKUP)} objects")
    _VIS_BACKUP = None


def write_out(model):
    objs = {bpy.data.objects[n] for n in GARMENTS[model]}
    out = os.path.join(HERE, f"swimwear_fit_{model}.blend")
    bpy.data.libraries.write(out, objs, fake_user=True, compress=True)
    print(f"@@@ WROTE {out} ({os.path.getsize(out)} bytes)")
    return out


def cleanup():
    """append した参照素体を消す（下着だけ残す）。"""
    o = bpy.data.objects.get("Ref_Body")
    if o:
        bpy.data.objects.remove(o, do_unlink=True)
        print("@@@ removed Ref_Body")
