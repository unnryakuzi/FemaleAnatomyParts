# -*- coding: utf-8 -*-
"""製品メッシュ(man_geom.json)と BodyParts3D v4.0(bp3d_index.json) を突合する。

1) 製品オブジェクト名 -> 解剖名インデックスCSV -> name_en
2) name_en の語集合で BP3D の English name と対応付け
3) 対応した重心から相似変換(スケール+軸並べ替え+平行移動)を最小二乗で推定
4) 変換後の bbox 中心距離・サイズ比を出して「同一セグメンテーションか」を判定
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
REFS = os.path.join(ROOT, "refs", "BodyParts3D_v4.0")

STOP = {"of", "the", "part"}


def words(s):
    s = re.sub(r"[^A-Za-z0-9 ]", " ", (s or "").lower())
    return frozenset(w for w in s.split() if w and w not in STOP)


def load_csv(path):
    """name_ja -> name_en"""
    out = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out[row["name_ja"]] = row["name_en"]
    return out


def center(rec, kmin="bmin", kmax="bmax"):
    return [(rec[kmin][i] + rec[kmax][i]) / 2.0 for i in range(3)]


def size(rec, kmin="bmin", kmax="bmax"):
    return [rec[kmax][i] - rec[kmin][i] for i in range(3)]


def fit_axis_map(src, dst):
    """src(BP3D,mm) -> dst(製品) の軸対応・符号・スケール・平行移動を推定。

    軸並べ替えは製品側が Blender OBJ 書き出しで入れ替わっている可能性があるため、
    6通りの軸割当×符号を総当たりして残差最小を選ぶ。
    """
    import itertools
    n = len(src)
    best = None
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            # 各出力軸 j は src[perm[j]] * signs[j] * s + t
            num = den = 0.0
            # 共通スケール s を全軸まとめて最小二乗
            sm = [sum(p[perm[j]] * signs[j] for p in src) / n for j in range(3)]
            dm = [sum(p[j] for p in dst) / n for j in range(3)]
            for p, q in zip(src, dst):
                for j in range(3):
                    a = p[perm[j]] * signs[j] - sm[j]
                    b = q[j] - dm[j]
                    num += a * b
                    den += a * a
            if den <= 0:
                continue
            s = num / den
            t = [dm[j] - s * sm[j] for j in range(3)]
            err = 0.0
            for p, q in zip(src, dst):
                for j in range(3):
                    e = s * p[perm[j]] * signs[j] + t[j] - q[j]
                    err += e * e
            rms = (err / n) ** 0.5
            if best is None or rms < best[0]:
                best = (rms, perm, signs, s, t)
    return best


def apply_t(p, perm, signs, s, t):
    return [s * p[perm[j]] * signs[j] + t[j] for j in range(3)]


def main():
    bp = json.load(open(os.path.join(REFS, "bp3d_index.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(REFS, "man_geom.json"), encoding="utf-8"))
    ja2en = load_csv(os.path.join(ROOT, "解剖名インデックス_Man.csv"))

    # BP3D: isa ツリー優先、語集合 -> レコード
    bpmap = {}
    for r in bp:
        if "bmin" not in r:
            continue
        k = words(r["en"])
        if not k:
            continue
        if k not in bpmap or (r["tree"] == "isa" and bpmap[k]["tree"] != "isa"):
            bpmap[k] = r

    pairs, unmatched = [], []
    for m in man:
        ja = re.sub(r"\(.*?\)$", "", m["name"]).strip()
        ja = re.sub(r"\.\d{3}$", "", ja)
        en = ja2en.get(ja)
        if not en:
            unmatched.append((m["name"], "索引に無い"))
            continue
        r = bpmap.get(words(en))
        if not r:
            unmatched.append((m["name"], "BP3Dに対応名なし: " + en))
            continue
        pairs.append((m, r, en))

    print("製品オブジェクト:", len(man))
    print("名前で対応がついた:", len(pairs))
    print("対応がつかない:", len(unmatched))

    src = [center(r) for _, r, _ in pairs]
    dst = [center(m) for m, _, _ in pairs]
    rms, perm, signs, s, t = fit_axis_map(src, dst)
    print("\n--- 推定した相似変換 (BP3D mm -> 製品座標) ---")
    print("軸対応 perm=%s 符号=%s スケール=%.6f 平行移動=[%.4f %.4f %.4f]"
          % (perm, signs, s, t[0], t[1], t[2]))
    print("重心残差 RMS = %.4f (製品座標単位)" % rms)

    rows = []
    for m, r, en in pairs:
        c = apply_t(center(r), perm, signs, s, t)
        d = sum((c[i] - center(m)[i]) ** 2 for i in range(3)) ** 0.5
        sb = sorted(abs(v) * s for v in size(r))
        sm_ = sorted(size(m))
        ratio = [(sm_[i] / sb[i]) if sb[i] > 1e-9 else 0 for i in range(3)]
        rows.append({
            "name": m["name"], "en": en, "bp_file": r["file"], "bp": r["bp"],
            "fma": r["fma"], "verts_product": m["verts"], "faces_product": m["faces"],
            "center_dist": round(d, 5),
            "size_ratio": [round(x, 4) for x in ratio],
        })

    rows.sort(key=lambda x: -x["center_dist"])
    dst_json = os.path.join(REFS, "match_report.json")
    json.dump({"transform": {"perm": perm, "signs": signs, "scale": s,
                             "translate": t, "rms": rms},
               "matched": rows, "unmatched": unmatched},
              open(dst_json, "w", encoding="utf-8", newline=""),
              ensure_ascii=False, indent=1)

    ds = sorted(r["center_dist"] for r in rows)
    q = lambda p: ds[int(len(ds) * p)] if ds else 0
    print("\n--- 重心一致度(製品座標=メートル想定) ---")
    print("中央値 %.5f / 90%%点 %.5f / 最大 %.5f" % (q(.5), q(.9), ds[-1]))
    print("\n--- 一致が悪い上位10 ---")
    for r in rows[:10]:
        print("  %-40s dist=%.4f sizeratio=%s" % (r["name"][:40], r["center_dist"],
                                                  r["size_ratio"]))
    print("\n-> ", dst_json)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
