# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: exposure.py の結果（14方向）を「移植後・移植前・マスター」と男性版で比べる（システムの Python）
# python tpose_port_expcmp.py <new.json> <before.json> <master.json> [男性 json ...]
import sys, json
N, B, M = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:4])
MALE = {}
for p in sys.argv[4:]:
    for k, v in json.load(open(p, encoding="utf-8")).items(): MALE.setdefault(k, v)
g = lambda D, k: D[k]["exposed"] if k in D else float("nan")
rows = sorted(N, key=lambda k: -max(g(N, k) - g(M, k), g(N, k) - g(B, k)))
print("露出%%（14方向のどれかで見える点の割合）: 移植後 / 移植前 / マスター / 男性   差（移植後−マスター）が大きい順")
for k in rows:
    d = g(N, k) - g(M, k)
    top = sorted(N[k]["per"].items(), key=lambda x: -x[1])[:2]
    print("  %-14s %6.2f / %6.2f / %6.2f / %6s   %+6.2f   %s" % (k, g(N, k), g(B, k), g(M, k), ("%.2f" % g(MALE, k)) if k in MALE else "-", d,
          " ".join("%s %.2f" % t for t in top if t[1] > 0)))
same = sum(abs(g(N, k) - g(M, k)) < 0.01 for k in N); print("マスターと同じ値（差 0.01%% 未満）: %d / %d" % (same, len(N)))
