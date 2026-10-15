# pelvis_section.py の断面を男女（＋試作）で並べて描く（システムの Python）
# python pelvis_section_plot.py <出力 png> <ラベル=json> ...
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("C:/Windows/Fonts/meiryo.ttc"); plt.rcParams["font.family"] = font_manager.FontProperties(fname="C:/Windows/Fonts/meiryo.ttc").get_name()
OUT = sys.argv[1]; SETS = [(s.split("=", 1)[0], json.load(open(s.split("=", 1)[1], encoding="utf-8"))) for s in sys.argv[2:]]
COL = {"bone": ("#888888", 1.4), "rib": ("#8b5a2b", 1.2), "eo": ("#1f77b4", 0.8), "io": ("#2ca02c", 0.8), "ta": ("#ff7f0e", 0.8), "ra": ("#d4b000", 0.8), "la": ("#000000", 1.0), "py": ("#d62728", 0.8)}
LV = list(SETS[0][1]["levels"])
fig, axes = plt.subplots(len(SETS), len(LV), figsize=(5.0 * len(LV), 5.2 * len(SETS)))
for r, (lab, S) in enumerate(SETS):
    for c, L in enumerate(LV):
        ax = axes[r, c]; sec = S["levels"][L]
        allp = np.array([p for k in ("eo",) for seg in sec["segs"].get(k, []) for p in seg])
        cy = (allp[:, 1].min() + allp[:, 1].max()) / 2 if len(allp) else 0
        for k, (col, lw) in COL.items():
            for seg in sec["segs"].get(k, []):
                p = np.array(seg); ax.plot(p[:, 0] * 1000, (p[:, 1] - cy) * 1000, color=col, lw=lw)
        ax.set_aspect("equal"); ax.invert_xaxis(); ax.set_xlim(190, -190); ax.set_ylim(-150, 150)
        ax.set_title("%s  腸骨稜の頂点から%smm" % (lab, ("%+d" % -int(L)).replace("+", "上").replace("-", "下")), fontsize=8); ax.tick_params(labelsize=6)
fig.text(0.01, 0.005, "灰=寛骨 茶=肋骨 青=外腹斜筋 緑=内腹斜筋 橙=腹横筋 黄=腹直筋 黒=白線 赤=錐体筋（上が背中・右が体の左）", fontsize=9)
plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig(OUT, dpi=100); print("saved", OUT)
