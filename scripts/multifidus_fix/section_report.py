# section_dump.py の断面から、肋骨の外面と外形の筋の内面のすき間（中心から放射方向）を男女で比べ、断面図を描く（システムの Python）
# python section_report.py <sec_female.json> <sec_male.json> <出力 png>
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("C:/Windows/Fonts/meiryo.ttc"); plt.rcParams["font.family"] = font_manager.FontProperties(fname="C:/Windows/Fonts/meiryo.ttc").get_name()
F = json.load(open(sys.argv[1], encoding="utf-8")); M = json.load(open(sys.argv[2], encoding="utf-8")); OUT = sys.argv[3]
def pts(sec, k):
    s = sec["segs"].get(k, []); return np.array([p for seg in s for p in seg]) if s else np.zeros((0, 2))
def profile(sec):
    R = pts(sec, "rib"); S = pts(sec, "shell")
    c = np.array([0.0, (R[:, 1].min() + R[:, 1].max()) / 2])          # 肋骨の前後の真ん中を中心に
    def polar(P):
        d = P - c; return np.degrees(np.arctan2(d[:, 1], -d[:, 0])), np.hypot(d[:, 0], d[:, 1])   # 0°=右横, +90°=後ろ(+Y), -90°=前
    ta_, tr = polar(R); sa, sr = polar(S); out = {}
    for th in range(-170, 181, 10):
        m = np.abs(((ta_ - th + 180) % 360) - 180) < 5
        if not m.any(): continue
        rr = tr[m].max()
        ms = (np.abs(((sa - th + 180) % 360) - 180) < 5) & (sr > rr - 0.002)
        if not ms.any(): continue
        out[th] = (rr, sr[ms].min())
    return c, out
lv = sorted(F, key=int)
rows = []
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
for ax, L in zip(axes.ravel(), [l for l in lv if l in ("6", "7", "8", "9", "10")][:5] + [None]):
    if L is None:
        ax.axis("off"); continue
    for sec, col, lab in ((M[L], "#1f77b4", "男性"), (F[L], "#d62728", "女性")):
        c, prof = profile(sec)
        for k, sty in (("rib", dict(lw=1.2)), ("shell", dict(lw=0.6, alpha=0.6))):
            for seg in sec["segs"].get(k, []):
                p = np.array(seg) - c; ax.plot(p[:, 0] * 1000, p[:, 1] * 1000, color=col, **sty)
        side = [th for th in prof if -60 <= th <= 60]
        gap = [(prof[th][1] - prof[th][0]) * 1000 for th in side]
        rows.append((L, lab, round(float(np.median([prof[th][0] for th in side])) * 1000, 1), round(float(np.median([prof[th][1] for th in side])) * 1000, 1), round(float(np.median(gap)), 1), round(float(max(gap)), 1)))
    ax.set_title("第%s肋骨の高さ（太線=肋骨・細線=外形の筋、赤=女性・青=男性）" % L, fontsize=9); ax.set_aspect("equal"); ax.invert_xaxis(); ax.set_xlabel("左右 mm（右が左側）"); ax.set_ylabel("前後 mm（上が背中）")
plt.tight_layout(); plt.savefig(OUT, dpi=110)
print("肋骨の高さ  モデル   横（±60°）の中央値: 肋骨の外面まで / 外形の筋の内面まで / すき間（中央値・最大）mm")
for r in rows: print("  第%s肋骨  %s  %6.1f / %6.1f / %5.1f・%5.1f" % r)
