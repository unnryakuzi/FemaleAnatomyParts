# interference.py の結果を男性版と比べる（システムの Python）
#  「余分な干渉」= 女性での干渉点の割合 − 男性の同じ組み合わせでの割合（元データの重なりは差し引く）
# python int_report.py <male.json> <female.json> [他の female.json ...]
import sys, json
male = json.load(open(sys.argv[1], encoding="utf-8")); fs = [(p.split("/")[-1].replace(".json", ""), json.load(open(p, encoding="utf-8"))) for p in sys.argv[2:]]
def excess(fem, k):
    out = []
    for q, (c, fr, mx) in fem[k]["pairs"].items():
        mfr = male.get(k, {}).get("pairs", {}).get(q, [0, 0.0, 0.0])[1]
        if fr - mfr > 0.5: out.append((q, round(fr - mfr, 1), mx))
    return sorted(out, key=lambda x: -x[1])
print("パーツ          " + " | ".join("%-38s" % n for n, _ in fs))
keys = sorted(fs[0][1], key=lambda k: -sum(x[1] for x in excess(fs[0][1], k)))
for k in keys:
    cells = []
    for n, fem in fs:
        if k not in fem: cells.append(" " * 38); continue
        ex = excess(fem, k); s = sum(x[1] for x in ex)
        cells.append(("%5.1f%% " % s + " ".join("%s%.0f%%/%.0fmm" % (q[:6], fr, mx) for q, fr, mx in ex[:2]))[:38].ljust(38))
    print("%-12s " % k + " | ".join(cells))
