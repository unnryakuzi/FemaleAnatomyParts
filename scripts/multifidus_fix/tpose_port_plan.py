# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 3つのダンプ（tpose_port_dump.py）を比べて、移すパーツを決める（システムの Python）
#  snap   = マスター v1.67（backups/snapshot_20261014_180805_欠落43パーツ追加前.blend）
#  tpose  = Tポーズ版（3DAnatomyFemale_Tpose_final_20261014.blend）
#  master = マスター v1.68.0（3DAnatomyFemale.blend）
#  移す = マスターで形・色が変わったパーツのうち、Tポーズ版が snap とビット一致（頂点・行列）しているもの＋足した43個のうち腕以外でマスターと違うもの
#  腕の6個（前腕骨間膜・手の虫様筋・掌側骨間筋）は Tポーズ版のものを残す（腕は T ポーズにして捻りなどの編集が入っているため）
# python tpose_port_plan.py <snap 接頭辞> <tpose 接頭辞> <master 接頭辞> <出力 plan.json>
import sys, json, collections, numpy as np
SP, TP, MP, OUT = sys.argv[1:5]
J = {k: json.load(open(p + ".json", encoding="utf-8")) for k, p in (("snap", SP), ("tpose", TP), ("master", MP))}
Z = {k: np.load(p + ".npz") for k, p in (("snap", SP), ("tpose", TP), ("master", MP))}
S, T, M = (J[k]["objects"] for k in ("snap", "tpose", "master"))
ARM6 = ("前腕骨間膜", "手の虫様筋", "掌側骨間筋")
def same(a, b): return a["cohash"] == b["cohash"] and a["topo"] == b["topo"] and np.array_equal(np.array(a["M"]), np.array(b["M"]))
def wd(fa, na, fb, nb):
    A = Z[fa][J[fa]["objects"][na]["key"]].astype(np.float64); B = Z[fb][J[fb]["objects"][nb]["key"]].astype(np.float64)
    d = np.linalg.norm(A - B, axis=1) * 1000; return [round(float(np.median(d)), 3), round(float(d.max()), 3)]
assert set(S) <= set(T) and set(T) == set(M), "パーツ名の集合が想定と違う"
st = collections.Counter("一致" if same(S[n], T[n]) else "違う" for n in S)
print("snap と tpose（共有 %d 個）:" % len(S), dict(st))
plan = dict(move=[], color=[], colls=[], keep_arm=[], conflict=[], same_added=[])
for n in sorted(M):
    m, t = M[n], T[n]
    if n in S:
        s = S[n]; shape = m["whash"] != s["whash"]; color = m["cols"] != s["cols"]; colls = m["colls"] != s["colls"]
        if not (shape or color or colls): continue
        if not same(s, t): plan["conflict"].append(dict(n=n, shape=shape, color=color, colls=colls)); continue
        assert m["topo"] == t["topo"] and np.array_equal(np.array(m["M"]), np.array(t["M"])), n
        if shape: plan["move"].append(dict(n=n, why="v1.68.0 で形が変わった", wd=wd("master", n, "tpose", n)))
        if color: plan["color"].append(dict(n=n, attrs=sorted(k for k in m["cols"] if m["cols"][k] != s["cols"].get(k))))
        if colls: plan["colls"].append(dict(n=n, frm=t["colls"], to=m["colls"]))
    else:
        if any(a in n for a in ARM6): plan["keep_arm"].append(dict(n=n, wd=wd("master", n, "tpose", n))); continue
        if same(m, t): plan["same_added"].append(n); continue
        assert m["topo"] == t["topo"] and m["nv"] == t["nv"] and np.array_equal(np.array(m["M"]), np.array(t["M"])), n
        plan["move"].append(dict(n=n, why="足した43個（マスターで作り直し済み）", wd=wd("master", n, "tpose", n)))
        if m["cols"] != t["cols"]: plan["color"].append(dict(n=n, attrs=sorted(k for k in m["cols"] if m["cols"][k] != t["cols"].get(k))))
for k, v in plan.items(): print("%-10s %d" % (k, len(v)))
for c in plan["conflict"]: print("  要確認（Tポーズ版で形が違うのにマスターで変わった）:", c)
for c in plan["color"]: print("  色:", c)
for c in plan["colls"]: print("  コレクション:", c)
for c in plan["keep_arm"]: print("  残す（腕）:", c["n"], c["wd"])
json.dump(plan, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("WROTE", OUT)
