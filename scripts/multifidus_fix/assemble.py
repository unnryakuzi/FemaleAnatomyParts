# 選んだ候補（パーツ → 候補 id）から、置き直すパーツのワールド座標 npz を作る（システムの Python）
#  候補 id は build_candidates.py の cands.json のもの（G0〜G11 / nb:<パーツ名> / B）。"own:<名前>" と書くと、左右を対象の側に合わせた nb:<右/左名前>
#  追加の npz（例: 多裂筋）はそのまま足す
# python assemble.py <work/wc> <cands.json> <選択 json> <出力 npz> [追加 npz ...]
import sys, json, numpy as np
W, CJ, SJ, OUT = sys.argv[1:5]; EXTRA = sys.argv[5:]
mj = json.load(open(W + "/male.json", encoding="utf-8")); M = np.load(W + "/male.npz")
C = json.load(open(CJ, encoding="utf-8")); sel = json.load(open(SJ, encoding="utf-8"))
out = {}
for k, cid in sel.items():
    if cid.startswith("own:"): cid = "nb:" + k[0] + cid[4:]
    c = next((c for c in C[k]["cands"] if c["id"] == cid), None)
    if c is None and cid.startswith("G"):    # 同じ変換の別名（例 nb:左頭板状筋 = G0）で重複除去されたグループは、グループ表から直接取る
        g = json.load(open(W + "/affine_report.json", encoding="utf-8"))["groups"][int(cid[1:])]
        A = np.vstack([np.array(g), [0, 0, 0, 1]]); c = dict(T=A.tolist(), sv=np.linalg.svd(A[:3, :3], compute_uv=False).round(3).tolist(), dev_med=None)
    assert c is not None, (k, cid)
    T = np.array(c["T"]); src = C[k]["src"]; X = M["w_%d" % mj["full"][src]].astype(float)
    if C[k]["mirror"]: X = X * np.array([-1.0, 1, 1])
    out[k] = (X @ T[:3, :3].T + T[:3, 3]).astype(np.float32)
    print(k, cid, "sv", c["sv"], "ずれ", c["dev_med"])
for e in EXTRA:
    Z = np.load(e)
    for k in Z.files: out[k] = Z[k]; print(k, "←", e.split("/")[-1])
np.savez_compressed(OUT, **out); print("parts", len(out))
