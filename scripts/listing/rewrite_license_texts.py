# -*- coding: utf-8 -*-
"""配布パッケージの LICENSE.txt / CREDITS.txt / README.txt を 2026-10 ライセンスに書き換える。

  python scripts/listing/rewrite_license_texts.py <パッケージdir> "<商品名(英)>" <旧版> <新版>

2026-10 に BodyParts3D の元データが CC BY 4.0（生命科学系データベースアーカイブ配布分）と確定したため、
CC BY-SA 2.1 JP から「BodyParts3D 部分は CC BY 4.0／本モデルのデータは再配布・転売禁止」へ切り替えた。
（経緯: refs/provenance_audit_summary.md §9。DBCLS 箕輪氏の回答 2026-10-06）
- CREDITS.txt の「CHANGES MADE…」節（本派生で加えた変更）は旧ファイルから引き継ぐ（CC BY の変更明示義務）
- README.txt はライセンス行・ライセンス節・版番号だけを差し替える
"""
import re
import sys
from pathlib import Path

MARK_ID = "KT-L2026-10"
BP3D_LIC = "https://creativecommons.org/licenses/by/4.0/legalcode.ja"
BP3D_LIC_EN = "https://creativecommons.org/licenses/by/4.0/"
BP3D_SRC = "https://dbarchive.biosciencedbc.jp/jp/bodyparts3d/download.html"
BP3D_LICPAGE = "https://dbarchive.biosciencedbc.jp/jp/bodyparts3d/lic.html"
RULE = "=" * 64
SUB = "-" * 64

TERMS_JA = (
    "本モデルは「BodyParts3D」© ライフサイエンス統合データベースセンター\n"
    "（CC 表示 4.0 国際）を改変して作成しました。\n"
    "商用・非商用を問わず、作品の制作に利用・改変できます。対象はイラスト・\n"
    "漫画・映像などのほか、モデルを単体で取り出せない形でのゲームへの組み込み\n"
    "も含みます。本モデルのデータそのもの（改変したものを含む）の再配布・転売・\n"
    "共有は禁止します。"
)
TERMS_EN = (
    "This model is an adaptation of \"BodyParts3D\" (c) The Database Center for\n"
    "Life Science (CC BY 4.0).\n"
    "You may use and modify it to create your own works, commercial or not:\n"
    "illustrations, comics, video and more, including embedding it in a game in\n"
    "a form where the model cannot be extracted on its own. Redistributing,\n"
    "reselling or sharing the model data itself (including modified versions)\n"
    "is prohibited."
)


def license_txt(name):
    return "\n".join([
        RULE, "LICENSE / ライセンス", RULE, "",
        "\"%s\" (c) 2026 Kabe (Kabe-Tech)  —  license version %s" % (name, MARK_ID), "",
        "[日本語]", TERMS_JA, "",
        "[English]", TERMS_EN, "",
        SUB, "SOURCE DATA / 元データ", SUB,
        "BodyParts3D, (c) The Database Center for Life Science",
        "licensed under CC BY 4.0 (Creative Commons Attribution 4.0 International)",
        "BodyParts3D © ライフサイエンス統合データベースセンター licensed under CC表示 4.0 国際",
        "  License / ライセンス: " + BP3D_LIC_EN,
        "                       " + BP3D_LIC,
        "  Source / 入手先:      " + BP3D_LICPAGE, "",
        "The restrictions above apply to this model (Kabe-Tech's adaptation).",
        "They do not limit your rights to the original BodyParts3D data, which",
        "anyone can obtain from the source above under CC BY 4.0.",
        "上記の制限は本モデル（Kabe-Tech による改変物）に対するものです。元データの",
        "BodyParts3D そのものは、上記の入手先から CC BY 4.0 で誰でも入手できます。", "",
        "Models distributed before October 2026 (without the identifier %s" % MARK_ID,
        "embedded in the files) were provided under CC BY-SA 2.1 JP.",
        "2026年10月より前に配布した版（ファイル内に識別子 %s が無いもの）は" % MARK_ID,
        "CC BY-SA 2.1 JP で提供しました。",
        "", "Contact / お問い合わせ: https://kabe-tech.com/contact.html",
        RULE, "",
    ])


def extract_changes(old_credits):
    m = re.search(r"-{20,}\nCHANGES MADE[^\n]*\n(?:[^\n-][^\n]*\n)?-{20,}\n(.*?)\n-{20,}\n", old_credits, re.S)
    return m.group(1).rstrip() if m else None


def credits_txt(name, changes):
    out = [
        RULE, "CREDITS / ATTRIBUTION  —  クレジット / 帰属表示", RULE, "",
        SUB, "ATTRIBUTION / 出典表記", SUB,
        "\"%s\" (c) 2026 Kabe (Kabe-Tech)" % name,
        "is an adaptation of \"BodyParts3D\" (c) The Database Center for Life Science,",
        "licensed under CC BY 4.0 (" + BP3D_LIC_EN + ").", "",
        "「%s」(c) 2026 Kabe (Kabe-Tech) は、" % name,
        "「BodyParts3D」© ライフサイエンス統合データベースセンター（CC 表示 4.0 国際）",
        "を改変して作成したものです。", "",
        SUB, "SOURCES / 出典", SUB,
        "- BodyParts3D (c) The Database Center for Life Science (DBCLS)",
        "    License: CC BY 4.0  " + BP3D_LIC_EN,
        "    " + BP3D_LICPAGE,
        "    Data: Release 3.0 (2011-09-15), polygon reduction rate 95%",
        "- %s (this adaptation) (c) 2026 Kabe (Kabe-Tech)" % name,
        "    https://kabe-tech.com/   Contact: https://kabe-tech.com/contact.html", "",
    ]
    if changes:
        out += [SUB, "CHANGES MADE IN THIS ADAPTATION / 本モデルで加えた主な変更", SUB, changes, ""]
    out += [RULE, ""]
    return "\n".join(out)


README_LICENSE_BLOCK = "\n".join([
    "IMPORTANT: LICENSE / 重要：ライセンス", SUB,
    TERMS_JA, "", TERMS_EN, "",
    "Details and source attribution: LICENSE.txt / CREDITS.txt",
    "詳細と出典表記は LICENSE.txt / CREDITS.txt を参照してください。", "",
])


def rewrite_readme(text, old_ver, new_ver):
    text = re.sub(r"(License / ライセンス:\s+).*", r"\1See LICENSE.txt (no redistribution / resale)", text, count=1)
    # ライセンス節: 「---- / ...LICENSE... / ----」から次の「----」見出し or 「====」まで
    pat = re.compile(r"(-{20,}\n)[^\n]*LICENSE[^\n]*\n-{20,}\n.*?(?=\n-{20,}\n|\n={20,})", re.S)
    text, n = pat.subn(lambda m: m.group(1) + README_LICENSE_BLOCK, text, count=1)
    if n != 1:
        raise SystemExit("README のライセンス節が見つからない")
    # 旧出典の連鎖（always3d → BodyParts3D）の行を出典に置き換える
    # 男性は2行、女性・骨格は4行（「…CREDITS.txt。」で終わる）
    text = re.sub(r"Derived from \"3DAnatomyman\".*?CREDITS\.txt。\n",
                  "Adapted from \"BodyParts3D\" (c) DBCLS, CC BY 4.0. See CREDITS.txt.\n"
                  "「BodyParts3D」(DBCLS, CC 表示 4.0 国際) を改変。詳細 CREDITS.txt。\n", text, flags=re.S)
    if old_ver and new_ver:
        text = text.replace(old_ver, new_ver)
    return text


def main():
    pkg, name = Path(sys.argv[1]), sys.argv[2]
    old_ver = sys.argv[3] if len(sys.argv) > 3 else None
    new_ver = sys.argv[4] if len(sys.argv) > 4 else None
    # 元ファイルの形式を保つ（解剖モデル=UTF-8/LF、骨格=BOM付き/CRLF でメモ帳向け）
    raw = (pkg / "README.txt").read_bytes()
    enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    nl = "\r\n" if b"\r\n" in raw else "\n"

    def read(f):
        return (pkg / f).read_text(encoding="utf-8-sig").replace("\r\n", "\n")

    def write(f, s):
        (pkg / f).write_text(s, encoding=enc, newline=nl)

    changes = extract_changes(read("CREDITS.txt"))
    if changes is None:
        print("[warn] CHANGES 節が見つからない（変更明示を手で確認すること）")
    write("LICENSE.txt", license_txt(name))
    write("CREDITS.txt", credits_txt(name, changes))
    write("README.txt", rewrite_readme(read("README.txt"), old_ver, new_ver))
    left = [f.name for f in pkg.glob("*.txt") if f.name != "LICENSE.txt" and re.search(r"BY-SA|表示-継承|ShareAlike|always3d", read(f.name))]
    print("[rewrite] %s 完了。旧ライセンス語の残り: %s" % (pkg.name, left or "なし"))


if __name__ == "__main__":
    main()
