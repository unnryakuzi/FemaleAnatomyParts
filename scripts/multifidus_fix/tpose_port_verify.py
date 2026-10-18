# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 書き込み後のTポーズ版（new）を、マスター・元のTポーズ版と照合する（システムの Python）
#  移したパーツ = マスターとビット一致（頂点・ワールド座標・行列・色・コレクション、属性と評価後の角の法線）
#  それ以外 = 元のTポーズ版とビット一致（頂点・行列・色・コレクション・材質・プロパティ・モディファイア・表示）
# python tpose_port_verify.py <plan.json> <tpose 接頭辞> <master 接頭辞> <new 接頭辞> [<attrs master.json> <attrs new.json>]
import sys, json, collections
a = sys.argv[1:]; PLAN = json.load(open(a[0], encoding="utf-8"))
T, M, N = (json.load(open(p + ".json", encoding="utf-8"))["objects"] for p in a[1:4])
mv = {r["n"] for r in PLAN["move"]}; cl = {r["n"] for r in PLAN["color"]}; cc = {r["n"] for r in PLAN["colls"]}
ARM = {r["n"] for r in PLAN["keep_arm"]} if "ARM6" in sys.argv[-1:] else set()   # 末尾に ARM6 を付けると、腕の6個は「置き直した」（行列・頂点だけ変わる）として照合
if ARM: sys.argv = sys.argv[:-1]; a = sys.argv[1:]
assert set(N) == set(T), "パーツ名の集合が変わった"
bad = collections.Counter(); ok = collections.Counter()
KEYS = ("cohash", "topo", "whash", "M", "cols", "colls", "mats", "props", "mods", "parent", "hide", "nv")
for n, x in N.items():
    if n in mv:    ref, want, lab = M, ("cohash", "topo", "whash", "M") + (("cols",) if n in cl else ()), "移した"
    elif n in ARM: ref, want, lab = T, tuple(k for k in KEYS if k not in ("cohash", "whash", "M")), "腕を置き直した"
    else:          ref, want, lab = T, KEYS, "そのまま"
    want = tuple(k for k in want if not (k == "colls" and n in cc))
    diff = [k for k in want if x[k] != ref[n][k]]
    if n in mv:                                                            # 移したパーツの、色以外の属性はTポーズ版のまま
        diff += ["T:" + k for k in ("mats", "props", "mods", "parent", "hide") if x[k] != T[n][k]]
        if n not in cl and x["cols"] != T[n]["cols"]: diff.append("T:cols")
    if n in cc and x["colls"] != M[n]["colls"]: diff.append("colls")
    (bad if diff else ok)[lab] += 1
    if diff: print("  NG", lab, n, diff)
print("一致:", dict(ok), " 不一致:", dict(bad))
if len(a) > 5:
    AM, AN = (json.load(open(p, encoding="utf-8")) for p in a[4:6])
    c = collections.Counter()
    for n in AN:
        ref = AM[n] if n in mv else None
        if ref is None: continue
        for k in set(ref) | set(AN[n]): c[(k, ref.get(k) == AN[n].get(k))] += 1
    print("移したパーツの属性（マスターと一致=True）:", sorted(c.items()))
