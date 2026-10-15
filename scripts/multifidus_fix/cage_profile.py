# 肋骨のかごと、その外にあるパーツの、中心からの距離を高さ z（1cm 刻み）× 向き θ（10°刻み）で測る。.blend は保存しない
#  r_rib = その向きで最も外側にある肋骨・肋軟骨・胸骨の点まで、r_shell = それより外にある「かごと一緒に動かさないパーツ」の最も内側の点まで
#  外のパーツ = 筋・骨・腱のうち、かご（肋骨・肋軟骨・胸骨・肋間筋・胸横筋・肋骨挙筋）、かごに付いて動く筋、作り直す腹壁の深い層を除く全部
#  （2026-10-15: 外形の筋7種だけで測ったら、肩甲骨・肩甲下筋・鎖骨の方へも広げて干渉が増えた）
#  中心 = その高さの肋骨の前後の真ん中（x=0）。θ: 0°=右横、+90°=背中（+Y）、-90°=前
#  あわせて肋骨（右）の番号ごとの高さ（最も外側の点）も出す（男女の高さの対応づけ用）
# blender -b <blend> -P cage_profile.py -- <出力 json> [z の刻み mm=10] [候補 npz（キー=base名, 値=ワールド座標）]
import bpy, sys, json, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]; OUT = a[0]; DZ = float(a[1]) / 1000 if len(a) > 1 else 0.010
CAND = np.load(a[2]) if len(a) > 2 else None
base = lambda n: n.split("(")[0].split(".")[0]
KAN = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}
MOVE = ("肋間筋", "胸横筋", "肋骨挙筋", "小胸筋", "鎖骨下筋", "上後鋸筋", "下後鋸筋", "胸腸肋筋", "大胸筋腹部", "内腹斜筋", "腹横筋", "腹直筋", "錐体筋")
def kind(b):
    if (("肋骨" in b or "肋軟骨" in b) and "挙筋" not in b) or b in ("胸骨柄", "胸骨体", "剣状突起"): return "rib"
    if any(s in b for s in MOVE): return None
    return "shell"
USE = [c for c in bpy.data.collections if c.name.startswith("筋肉") or c.name in ("表層筋", "深層筋", "靱帯・腱", "骨格")]
objs = sorted({(o, kind(base(o.name))) for c in USE for o in c.all_objects if o.type == 'MESH' and kind(base(o.name))}, key=lambda t: t[0].name)
def world(o):
    if CAND is not None and base(o.name) in CAND.files: return CAND[base(o.name)].astype(float)
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
def tris(o):
    me = o.data; me.calc_loop_triangles(); t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t); return t.reshape(-1, 3)
_rz = np.concatenate([world(o)[:, 2] for o, k in objs if k == "rib"]); Z0, Z1 = _rz.min() - 0.03, _rz.max() + 0.03
data = {}
for o, k in objs:
    W = world(o)
    if W[:, 2].max() < Z0 or W[:, 2].min() > Z1: continue
    data[o] = (W, tris(o), k)
levels = {}
for n in range(1, 13):
    o = next(o for o, k in objs if base(o.name) == "右第%s肋骨" % KAN[n]); W = world(o); levels[n] = float(W[np.argmin(W[:, 0]), 2])
names = sorted({base(o.name) for o in data})
ribW = np.concatenate([v[0] for o, v in data.items() if v[2] == "rib"])
zs = np.arange(ribW[:, 2].min() + 0.003, ribW[:, 2].max() - 0.003, DZ)
def section(z):
    P = {"rib": [], "shell": []}; NM = {"rib": [], "shell": []}
    for o, (V, T, k) in data.items():
        if V[:, 2].min() > z or V[:, 2].max() < z: continue
        dt = V[:, 2][T] - z; m = (dt.min(1) < 0) & (dt.max(1) > 0); Tm, dm = T[m], dt[m]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            c = (dm[:, i] < 0) != (dm[:, j] < 0)
            if not c.any(): continue
            t_ = (dm[c, i] / (dm[c, i] - dm[c, j]))[:, None]; A = V[Tm[c, i]]; Bv = V[Tm[c, j]]
            P[k].append((A + t_ * (Bv - A))[:, :2]); NM[k].append(np.full(int(c.sum()), names.index(base(o.name))))
    return {k: np.concatenate(v) if v else np.zeros((0, 2)) for k, v in P.items()}, {k: np.concatenate(v) if v else np.zeros(0, int) for k, v in NM.items()}
rows = []
for z in zs:
    P, NMS = section(z); R, S = P["rib"], P["shell"]; SN = NMS["shell"]
    if len(R) < 20: continue
    cy = float((R[:, 1].min() + R[:, 1].max()) / 2)
    def pol(Q): d = Q - np.array([0.0, cy]); return np.degrees(np.arctan2(d[:, 1], -d[:, 0])), np.hypot(d[:, 0], d[:, 1])
    ra, rr = pol(R); sa, sr = pol(S) if len(S) else (np.zeros(0), np.zeros(0))
    prof = {}
    for th in range(-180, 180, 10):
        m = np.abs(((ra - th + 180) % 360) - 180) < 5
        if not m.any(): continue
        r_rib = float(rr[m].max())
        ms = (np.abs(((sa - th + 180) % 360) - 180) < 5) & (sr > r_rib - 0.002) if len(S) else np.zeros(0, bool)
        prof[th] = [round(r_rib, 5), round(float(sr[ms].min()), 5) if ms.any() else None, names[int(SN[ms][np.argmin(sr[ms])])] if ms.any() else None]
    rows.append(dict(z=round(float(z), 4), cy=round(cy, 5), prof=prof))
json.dump(dict(levels=levels, rows=rows), open(OUT, "w", encoding="utf-8"))
print("DONE", len(rows), "slices", {k: round(v, 3) for k, v in levels.items()})
