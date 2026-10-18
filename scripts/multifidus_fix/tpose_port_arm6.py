# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 腕の6個（前腕骨間膜・手の虫様筋・掌側骨間筋）を、男性の形のまま Tポーズの骨・筋と同じ変換で置き直す
#  Tポーズ版の6個は「周りの変形を頂点ごとに写す＋押し込み」で作られていて折れていた（折れ辺 712〜2575本、男性・マスター 0本、辺の伸び最大13倍）
#  Tポーズ版の手・前腕の骨と手の筋は、マスターと同じ頂点のまま1つの行列（橈骨と同じ）で置かれている（0.0003mm 以内で一致）。尺骨だけ別の行列（回内）
#   - 手の虫様筋・掌側骨間筋: 行列を橈骨（＝手の骨・手の筋）と同じにし、頂点はマスター（Man_All）のまま
#   - 前腕骨間膜: Tポーズ版の前腕の筋は「橈骨の行列で置いた形を、前腕の軸のまわりに回内の角度 × φ(s) だけ回したもの」になっている
#     （s = 尺骨の軸方向の位置 0..1、φ は肘側 1＝尺骨と一緒 → 手首側 0＝橈骨・手と一緒。前腕の筋 26個で残差 中央 0.0〜0.1mm）。
#     膜にも同じ φ(s) をかける（1変数の関数のねじり）。前腕の筋の頂点から φ(s) を当てはめ直して使う。そのあと干渉が減る位置へ剛体で少し動かす（OFFSET）
#     試した別案（2026-10-18 実測）: 橈骨・尺骨までの距離の比で動きを分ける案は、折れ辺 11〜15・深指屈筋などとの干渉 25〜27%（マスター 5〜7%）で採らなかった
# blender -b <Tポーズ版 .blend> -P tpose_port_arm6.py -- <plan.json> <take npz（arm__・fa__ あり）> <保存先 .blend>
import bpy, sys, os, json, numpy as np
from mathutils import Matrix
a = sys.argv[sys.argv.index("--") + 1:]; PLAN = json.load(open(a[0], encoding="utf-8")); X = np.load(a[1]); OUT = os.path.abspath(a[2])
assert os.path.normcase(OUT) != os.path.normcase(os.path.abspath(bpy.data.filepath)) or os.environ.get("INPLACE") == "1", "同じファイルに保存するなら INPLACE=1"
PHIS = np.linspace(-0.2, 1.2, 141); BINS = np.arange(-0.2, 1.6001, 0.05)
# ねじったあとの膜を、干渉が減る位置へ剛体で少し動かす（Δφ = 回内の角度に対する割合、du/dv = 軸に垂直な2方向の平行移動 m）。
#  tpose_port_membrane_search.py で、骨への付き（各骨に近い10%の点の距離の中央値）2mm 以内の条件で選んだ（2026-10-18: 右 31.5→22.9%、左 27.1→18.5%、交差回数の確認なし・2点に1点）
OFFSET = {"右": (0.06, -0.001, -0.002), "左": (0.09, 0.0, -0.001)}
def rot(k, ang):
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]); return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K
base = lambda n: n.split("(")[0]
obj = {base(o.name): o for o in bpy.data.objects if o.type == 'MESH'}
def wco(o):
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); M = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
def screw(G0, G4):
    # 尺骨の行列 G4 = 橈骨の行列 G0 からの剛体の動き（Rrel, trel）を、軸 k・角度 ang・軸上の点 c・軸方向の並進 dax に分ける
    S = np.linalg.norm(G0[:3, :3], axis=0); assert np.allclose(S, np.linalg.norm(G4[:3, :3], axis=0), rtol=1e-6), "橈骨と尺骨の倍率が違う"
    Rrel = (G4[:3, :3] / S) @ (G0[:3, :3] / S).T; trel = G4[:3, 3] - Rrel @ G0[:3, 3]
    ang = float(np.arccos(np.clip((np.trace(Rrel) - 1) / 2, -1, 1)))
    ev, evec = np.linalg.eig(Rrel); k = np.real(evec[:, np.argmin(np.abs(ev - 1))]); k /= np.linalg.norm(k)
    if np.linalg.norm(rot(k, ang) - Rrel) > 1e-6: k = -k
    dax = float(trel @ k); c = np.linalg.lstsq(np.eye(3) - Rrel + np.outer(k, k), trel - dax * k, rcond=None)[0]
    return k, ang, c, dax
def twist(P0, phi, k, ang, c, dax):
    return np.einsum("nij,nj->ni", np.array([rot(k, f * ang) for f in phi]), P0 - c) + c + phi[:, None] * dax * k
log = {}
for side in sorted({base(r["n"])[0] for r in PLAN["keep_arm"]}):
    rad, uln = obj[side + "橈骨"], obj[side + "尺骨"]; G0 = np.array(rad.matrix_world); G4 = np.array(uln.matrix_world)
    for kk in ("第三中手骨", "三角骨", "母指対立筋"):                         # 手の骨・手の筋が橈骨と同じ行列であること
        assert np.array_equal(np.array(obj[side + kk].matrix_world), G0), (side + kk, "の行列が橈骨と違う")
    k, ang, c, dax = screw(G0, G4)
    tu = (wco(uln) - c) @ k; t_lo, t_hi = float(tu.min()), float(tu.max())
    S_, F_, R_ = [], [], []
    for key in (f for f in X.files if f.startswith("fa__" + side)):          # 前腕の筋から φ(s) を当てはめる
        n = key[4:]; o = bpy.data.objects[n]; co = X[key].astype(np.float64)
        assert len(co) == len(o.data.vertices), n
        P0 = co @ G0[:3, :3].T + G0[:3, 3]; PT = wco(o); idx = np.arange(0, len(P0), max(1, len(P0) // 2000))
        Q = np.stack([(P0[idx] - c) @ rot(k, f * ang).T + c + f * dax * k for f in PHIS]); err = np.linalg.norm(Q - PT[idx][None], axis=2)
        j = np.argmin(err, 0); e = err[j, np.arange(len(idx))]; ok = e < 0.001
        S_ += list((((PT[idx] - c) @ k - t_lo) / (t_hi - t_lo))[ok]); F_ += list(PHIS[j][ok]); R_ += list(e[ok])
    S_, F_ = np.array(S_), np.array(F_)
    cen, med = [], []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        m = (S_ >= lo) & (S_ < hi)
        if m.sum() >= 30: cen.append((lo + hi) / 2); med.append(float(np.median(F_[m])))
    cen, med = np.array(cen), np.array(med)
    log[side + "_φ(s)"] = dict(rot_deg=round(np.degrees(ang), 2), axial_mm=round(dax * 1000, 3), n_fit=int(len(S_)),
                               resid_med_mm=round(float(np.median(R_)) * 1000, 3), table=[[round(x, 3), round(y, 3)] for x, y in zip(cen, med)])
    for r in (r for r in PLAN["keep_arm"] if base(r["n"])[0] == side):
        n = r["n"]; b = base(n); o = bpy.data.objects[n]; me = o.data
        co = X["arm__" + n].astype(np.float64); assert len(co) == len(me.vertices), (n, len(co), len(me.vertices))
        if "前腕骨間膜" in b:
            P0 = co @ G0[:3, :3].T + G0[:3, 3]; s = ((P0 - c) @ k - t_lo) / (t_hi - t_lo); phi = np.interp(s, cen, med)
            PT = twist(P0, phi, k, ang, c, dax)
            dphi, du, dv = OFFSET.get(side, (0.0, 0.0, 0.0)); u = np.cross(k, [0, 0, 1.0]); u /= np.linalg.norm(u); v_ = np.cross(k, u)   # search と同じ向き
            PT = (PT - c) @ rot(k, dphi * ang).T + c + du * u + dv * v_
            Gi = np.linalg.inv(G0); loc = PT @ Gi[:3, :3].T + Gi[:3, 3]
            log[b] = dict(phi_min=round(float(phi.min()), 3), phi_med=round(float(np.median(phi)), 3), phi_max=round(float(phi.max()), 3), offset=[dphi, du, dv])
        else:
            loc = co; log[b] = "手の行列（橈骨と同じ）で剛体"
        o.matrix_world = Matrix(G0.tolist())
        me.vertices.foreach_set("co", loc.astype(np.float32).ravel()); me.update()
        print("SET", b, log[b], flush=True)
    print("PHI", side, {kk: v for kk, v in log[side + "_φ(s)"].items() if kk != "table"}, flush=True)
bpy.context.view_layer.update()
json.dump(log, open(os.path.join(os.path.dirname(os.path.abspath(a[1])), os.path.splitext(os.path.basename(OUT))[0] + "_arm6.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)                                    # 記録は take npz と同じ作業フォルダへ（φ(s) の表・ずらし量）
if os.path.normcase(OUT) == os.path.normcase(os.path.abspath(bpy.data.filepath)): bpy.ops.wm.save_mainfile()
else: bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print("SAVED", OUT)
