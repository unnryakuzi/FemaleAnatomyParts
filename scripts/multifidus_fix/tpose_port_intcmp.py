# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: interference.py の結果を「移植後・移植前・マスター」で比べる（システムの Python）
#  マスターと違う組み合わせ（相手が Tポーズ版で形の違うパーツ＝腕まわりのはず）と、移植前より増えた組み合わせを出す
#  男性版の値（int_report.py と同じ「余分な干渉」= 女性 − 男性）も、男性 json があれば並べる
# python tpose_port_intcmp.py <new.json> <before.json> <master.json> <near.json（spec の一覧）> [男性 json ...]
import sys, json
N, B, M = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:4]); SPEC = {s.split("(")[0] for s in json.load(open(sys.argv[4], encoding="utf-8"))["spec"]}
MALE = {}
for p in sys.argv[5:]:
    for k, v in json.load(open(p, encoding="utf-8")).items(): MALE.setdefault(k, v)
def fr(D, k, q): return D.get(k, {}).get("pairs", {}).get(q, [0, 0.0, 0.0])
def tot(D, k): return sum(v[1] for v in D.get(k, {}).get("pairs", {}).values())
def excess(D, k):
    return sum(max(0.0, v[1] - MALE.get(k, {}).get("pairs", {}).get(q, [0, 0.0, 0.0])[1]) for q, v in D.get(k, {}).get("pairs", {}).items())
same_m, diff_m, rows = 0, [], []
for k in sorted(N):
    qs = set(N[k]["pairs"]) | set(M.get(k, {}).get("pairs", {})) | set(B.get(k, {}).get("pairs", {}))
    dm = [(q, fr(N, k, q)[1], fr(M, k, q)[1], fr(B, k, q)[1], fr(N, k, q)[2]) for q in qs if abs(fr(N, k, q)[1] - fr(M, k, q)[1]) > 0.05]
    if not dm: same_m += 1
    else: diff_m.append((k, dm))
    rows.append((k, tot(N, k), tot(B, k), tot(M, k), excess(N, k) if MALE else None, excess(B, k) if MALE else None, excess(M, k) if MALE else None))
print("マスターと全組み合わせが同じ: %d / %d パーツ" % (same_m, len(N)))
print("マスターと違う組み合わせ（相手, 移植後%, マスター%, 移植前%, 移植後の最大深さmm）。* = 相手が Tポーズ版で形の違うパーツ")
for k, dm in diff_m:
    print("  %-14s " % k + "  ".join("%s%s %.1f/%.1f/%.1f(%.0fmm)" % ("*" if q.split("#")[0] in SPEC else "", q, a, b, c, d) for q, a, b, c, d in sorted(dm, key=lambda x: -abs(x[1] - x[2]))[:5]))
print("\n干渉の合計%（全相手の和）: 移植後 / 移植前 / マスター" + ("   男性より余分: 移植後 / 移植前 / マスター" if MALE else ""))
for r in sorted(rows, key=lambda r: -(r[1] - r[2])):
    print("  %-14s %6.1f / %6.1f / %6.1f" % r[:4] + ("   %6.1f / %6.1f / %6.1f" % r[4:] if MALE else ""))
