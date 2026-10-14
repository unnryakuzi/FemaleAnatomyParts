# -*- coding: utf-8 -*-
"""配布物の .blend から 解剖名インデックス（CSV / HTML）と anatomy_terms.json を作る。.blend は保存しない。

  blender -b 配布パッケージ_v1.68.0/models/FemaleAnatomy_v1.68.0.blend -P scripts/listing/build_index.py -- <index dir> <female|male> [前の版の anatomy_terms.json]

v1.66.0 で作った索引の形式をそのまま再現する（2026-10-14 に v1.67.1 の .blend から作り直して、既存の CSV と全行一致を確認）:
  - 行 = MESH 1個。region = 入っているコレクション名。ラベルは各オブジェクトの name_ja / name_kana / name_en / name_la
  - 並び = region の文字コード順 → 英語名の順。conf=low は ★ と赤字
  - anatomy_terms.json = 前の版の json ＋ この .blend で新たに使う語（scripts/anatomy_terms.json から）。_meta の出典表記は新ライセンスに
"""
import bpy, sys, os, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import apply_labels  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:]
OUT, MODEL = a[0], a[1]
os.makedirs(OUT, exist_ok=True)
terms = apply_labels.load_terms()

TITLE = {"female": "女性解剖モデル 解剖名インデックス / Female Anatomy Model — Term Index",
         "male": "男性解剖モデル 解剖名インデックス / Male Anatomy Model — Term Index"}[MODEL]
STEM = {"female": "解剖名インデックス", "male": "解剖名インデックス_Man"}[MODEL]
# 出典表記は README（rewrite_license_texts.py）と同じ文
SOURCE = "「BodyParts3D」(DBCLS, CC 表示 4.0 国際) を改変。Adapted from \"BodyParts3D\" (c) DBCLS, CC BY 4.0. See CREDITS.txt."

# 前の版の anatomy_terms.json があれば、ラベルの確度(conf)はまずそちらで引く（前の版の索引と同じ結果にするため）
prev = json.load(open(a[2], encoding="utf-8")) if len(a) > 2 else {"_meta": dict(terms.get("_meta", {}))}
rows, used = [], set()
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    res, key = apply_labels.lookup(o.name, prev)
    if res is None:
        res, key = apply_labels.lookup(o.name, terms)
    if res is not None:
        used.add(key)
    conf = res["conf"] if res else ("" if "name_en" in o else "low")   # 対訳表に無くてもラベル付き（種子骨など）は v1.67 と同じく空
    region = o.users_collection[0].name if o.users_collection else ""
    rows.append((region, o.get("name_ja", o.name), o.get("name_kana", ""), o.get("name_en", ""), o.get("name_la", ""), conf or ""))
rows.sort(key=lambda r: (r[0], r[3], r[1]))

with open(os.path.join(OUT, STEM + ".csv"), "w", encoding="utf-8-sig", newline="\r\n") as f:   # v1.67 と同じ CRLF
    f.write("region,name_ja,kana,name_en,name_la,conf\n")
    for r in rows:
        f.write(",".join('"%s"' % x.replace('"', '""') if ("," in x or '"' in x) else x for x in r) + "\n")

h = ['<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>解剖名インデックス / Anatomy Index</title>',
     '<style>body{font-family:"Yu Gothic",sans-serif;margin:24px;color:#222}h1{font-size:20px}h2{font-size:15px;margin-top:22px;border-bottom:2px solid #888;padding-bottom:3px}table{border-collapse:collapse;width:100%;font-size:12px;margin-top:6px}th,td{border:1px solid #ccc;padding:3px 6px;text-align:left}th{background:#f0f0f0}.low{color:#b00}.note{font-size:11px;color:#666}</style></head><body>',
     "<h1>%s</h1>" % TITLE,
     '<p class="note">日本語(読み) / English / Latin。★=要照合(low confidence)。出典: %s 総パーツ %d。</p>' % (html.escape(SOURCE, quote=False), len(rows))]
regions = []
for r in rows:
    if r[0] not in regions:
        regions.append(r[0])
for g in regions:
    rr = [r for r in rows if r[0] == g]
    h.append("<h2>%s (%d)</h2>" % (html.escape(g), len(rr)))
    h.append("<table><tr><th>日本語</th><th>読み</th><th>English</th><th>Latin</th></tr>")
    for _, ja, kana, en, la, conf in rr:
        low = conf == "low"
        h.append('<tr%s><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            ' class="low"' if low else "", "★ " if low else "", html.escape(ja), html.escape(kana), html.escape(en), html.escape(la)))
    h.append("</table>")
h.append("</body></html>")
open(os.path.join(OUT, STEM + ".html"), "w", encoding="utf-8", newline="\r\n").write("\n".join(h))   # v1.67 と同じ CRLF・末尾改行なし

# 前の版の anatomy_terms.json があれば、それに今回の .blend で新たに使う語を足す（既存の語と並びは変えない）
sub = dict(prev)
sub["_meta"] = dict(prev.get("_meta", {})); sub["_meta"]["source_note"] = "出典 " + SOURCE
# 表記ゆれのキー（例 仙骨;仙椎[1－5] と [N－N]）で同じ語が二重に入らないよう、英・羅が同じ語が既にあれば足さない
have = {(v.get("en"), v.get("la")) for k, v in prev.items() if k != "_meta" and isinstance(v, dict)}
added_terms = [k for k in sorted(used) if k in terms and k not in sub and (terms[k].get("en"), terms[k].get("la")) not in have]
sub.update({k: terms[k] for k in added_terms})
print("[build_index] 対訳を足した語:", added_terms)
json.dump(sub, open(os.path.join(OUT, "anatomy_terms.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[build_index] rows=%d regions=%d terms=%d -> %s" % (len(rows), len(regions), len(sub) - 1, OUT))
