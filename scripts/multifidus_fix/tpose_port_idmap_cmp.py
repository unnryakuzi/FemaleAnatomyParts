# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: 01_ray_idmap.py（色の焼き付けと同じ光線）の結果を2つ比べ、体の表面で「当たるパーツ」が変わる画素を数える（システムの Python）
#  焼き直すかの判断材料: パーツが変わる画素＋同じパーツでも形を動かしたパーツに当たる画素（色・凹凸が変わりうる）を出す
#  KEY=ids（既定）= ID マップ（乳房の下・外腹斜筋の奥の腹直筋に読み替えた番号）、KEY=first = 色の焼き付け（bake_color.py: 最初に当たったパーツ。乳房を含む）
# python tpose_port_idmap_cmp.py <A.npz> <B.npz> <動かしたパーツの一覧 json（名前のリスト）> <差分画像 png> [ラベルA ラベルB]
import sys, os, json, collections, numpy as np
from PIL import Image
A, B = np.load(sys.argv[1]), np.load(sys.argv[2]); MOVED = set(json.load(open(sys.argv[3], encoding="utf-8"))); OUT = sys.argv[4]
LA, LB = (sys.argv[5], sys.argv[6]) if len(sys.argv) > 6 else ("A", "B"); KEY = os.environ.get("KEY", "ids")
na = [n for n, _ in json.load(open(sys.argv[1][:-4] + "_names.json", encoding="utf-8"))] + ["Breast_Base"]   # 番号 = パーツ数 は乳房
nb = [n for n, _ in json.load(open(sys.argv[2][:-4] + "_names.json", encoding="utf-8"))] + ["Breast_Base"]
def names(ids, nm):
    out = np.full(ids.shape, "", object); m = ids >= 0; out[m] = np.array(nm, object)[ids[m]]; return out
cov = A["cov"] & B["cov"]; NA, NB = names(A[KEY], na), names(B[KEY], nb)
print("比べるもの:", "色の焼き付け（最初に当たるパーツ）" if KEY == "first" else "ID マップ")
hit = cov & ((NA != "") | (NB != "")); ch = hit & (NA != NB)
mv = hit & ~ch & np.isin(NB, list(MOVED))
print("体の表面の画素 %d（光線がパーツに当たる %d）" % (cov.sum(), hit.sum()))
print("当たるパーツが変わる画素: %d（%.2f%%）" % (ch.sum(), ch.sum() / max(hit.sum(), 1) * 100))
print("同じパーツだが、形を動かしたパーツに当たる画素: %d（%.2f%%）" % (mv.sum(), mv.sum() / max(hit.sum(), 1) * 100))
pairs = collections.Counter(zip(NA[ch], NB[ch]))
print("変わり方（%s → %s, 画素数）:" % (LA, LB))
for (x, y), c in pairs.most_common(25): print("  %6d  %s → %s" % (c, x.split("(")[0] or "(なし)", y.split("(")[0] or "(なし)"))
mvp = collections.Counter(NB[mv])
print("形を動かしたパーツに当たる画素（パーツ別）:")
for x, c in mvp.most_common(15): print("  %6d  %s" % (c, x.split("(")[0]))
img = np.full(cov.shape + (3,), 255, np.uint8); img[cov] = (215, 215, 215); img[hit] = (170, 170, 170); img[mv] = (60, 140, 255); img[ch] = (230, 30, 30)
Image.fromarray(img[::-1]).save(OUT); print("IMG", OUT, "（赤=当たるパーツが変わる、青=形を動かしたパーツに当たる）")
