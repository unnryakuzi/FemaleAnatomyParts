# cage_profile.py の結果を男性と比べる（システムの Python）: 向きの範囲ごとのすき間の中央値、男性との差、外のパーツへのめり込み（すき間 < -1mm）の升
# python cage_gapcmp.py <男性 json> <ラベル=json> ...
import sys, json, numpy as np
TH = list(range(-180, 180, 10))
def grid(J):
    zs = np.array([r["z"] for r in J["rows"]]); G = np.full((len(zs), len(TH)), np.nan); N = np.full(G.shape, None, object)
    for i, r in enumerate(J["rows"]):
        for j, th in enumerate(TH):
            p = r["prof"].get(str(th))
            if p and p[1] is not None: G[i, j] = (p[1] - p[0]) * 1000; N[i, j] = p[2] if len(p) > 2 else None
    lv = np.array([J["levels"][str(n)] for n in range(1, 12)]); return zs, G, N, lv
Mj = json.load(open(sys.argv[1], encoding="utf-8")); zm, Gm, Nm, lm = grid(Mj)
REG = {"前(-120〜-60)": lambda t: -120 <= t <= -60, "前横(-150,-30)": lambda t: t in (-150, -140, -40, -30), "横(±180〜-160, -20〜0)": lambda t: t in (-180, -170, -160, -20, -10, 0, 170),
       "後横(20〜60,120〜160)": lambda t: 20 <= t <= 60 or 120 <= t <= 160, "背中(70〜110)": lambda t: 70 <= t <= 110}
print("%-10s " % "" + " ".join("%-22s" % r for r in REG) + "  男性との差の中央値  めり込み升")
for spec in sys.argv[2:]:
    lab, f = spec.split("=", 1); J = json.load(open(f, encoding="utf-8")); zf, Gf, Nf, lf = grid(J)
    o = np.argsort(lf); D = []; cells = []; pen = []
    for i, z in enumerate(zf):
        zz = float(np.interp(z, lf[o], lm[o])); k = np.argmin(np.abs(zm - zz))
        for j, t in enumerate(TH):
            if np.isfinite(Gf[i, j]) and np.isfinite(Gm[k, j]):
                cells.append((t, Gf[i, j], Gm[k, j]))
            if np.isfinite(Gf[i, j]) and Gf[i, j] < -1 and not (np.isfinite(Gm[k, j]) and Gm[k, j] < -1): pen.append((round(z, 3), t, round(Gf[i, j], 1), Nf[i, j]))
    C = np.array([(c[0], c[1], c[2]) for c in cells])
    row = []
    for r, fn in REG.items():
        m = np.array([fn(t) for t in C[:, 0]]); row.append("%5.1f (男 %5.1f)        " % (np.median(C[m, 1]), np.median(C[m, 2])))
    print("%-10s " % lab + " ".join(x[:22] for x in row) + "  %5.1f mm          %d" % (np.median(np.abs(C[:, 1] - C[:, 2])), len(pen)))
    if pen: print("     めり込み（男性では無い所）:", sorted(pen, key=lambda p: p[2])[:12])
