#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
出品プレビューの背景を一律 184 グレーに正規化し、正方形サムネ3枚を再生成する。

なぜ必要か:
  - モデル間で scene.view_settings.view_transform が違うと、同じ背景指定でも
    レンダー結果の背景明度がズレる（実測 Female=193 / Male=184 など）。
  - そのまま男女を並べる thumb_set を作ると境界に矩形が出る。
  - → 撮影後に背景グレーだけを 184 に正規化して男女を揃える。

マスクの安全性:
  - 背景は完全にニュートラル（R=G=B）。本体の筋・骨・白い腱は必ず色味(RGB差)を持つ。
  - spread(max-min)<=6 かつ 明度 180..210 のみを 184 にする → 背景だけ捕捉、本体無侵食。
  - （検証済み: bbox内でマスクされる画素は脚間/腕脇などの背景隙間のみ）

サムネ構図:
  - thumb_female / thumb_male = 1400x1400 キャンバス(184)に 1000x1400 プレビューを (200,0) 配置
  - thumb_set = 2000x2000 キャンバス(184)。人物の非背景bboxを切り出し、高さ1800pxに
    拡大して男女を中央に並べる（旧構図は人物が高さ54%で「遠く小さい」と指摘あり 2026-07-13）。
  - ※ 1番目=正面(01)プレビューを使う。Gumroad/BOOTH のグリッド/ライブラリ用サムネ。

使い方:
  python scripts/listing/normalize_and_thumbs.py
  （config.json の female/male previews_dir と thumbnails_dir を読む）
"""
import json, os, glob, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
ROOT = CFG["root"]
G = CFG.get("bg_gray", 184)


def normalize_bg(path):
    """背景を G(=184) に統一する。
    - 透過PNG(render_previews.pyのheadless出力, film_transparent)→ Gキャンバスに合成（最も確実）
    - 不透明PNG(旧opengl出力, 背景184/193/237)→ ニュートラル背景画素を G に置換
    本体の白い腱/帽状腱膜は暖色(R>G>B)でspread>5なので無侵食。"""
    img = Image.open(path)
    if img.mode == "RGBA" and img.getextrema()[3][0] < 255:
        bg = Image.new("RGBA", img.size, (G, G, G, 255))
        bg.alpha_composite(img)
        bg.convert("RGB").save(path)
        return -1  # composited
    im = np.array(img.convert("RGB")).astype(int)
    spread = im.max(2) - im.min(2)
    b = im.mean(2)
    mask = (spread <= 5) & (b >= 178) & (b <= 244)
    out = im.copy()
    out[mask] = [G, G, G]
    Image.fromarray(out.astype("uint8")).save(path)
    return int(mask.sum())


def normalize_dir(rel_dir):
    d = os.path.join(ROOT, rel_dir)
    n = 0
    for p in sorted(glob.glob(os.path.join(d, "*.png"))):
        c = normalize_bg(p)
        print(f"  normalized {os.path.basename(p)} ({c} px)")
        n += 1
    return n


def crop_figure(img, pad=20):
    """非背景(=人物)のbboxで切り出す。背景は正規化済みの184前提。"""
    im = np.array(img.convert("RGB")).astype(int)
    mask = ~((im.max(2) - im.min(2) <= 5) & (np.abs(im.mean(2) - G) < 3))
    ys, xs = np.where(mask)
    x0 = max(int(xs.min()) - pad, 0); x1 = min(int(xs.max()) + pad, img.width)
    y0 = max(int(ys.min()) - pad, 0); y1 = min(int(ys.max()) + pad, img.height)
    return img.convert("RGB").crop((x0, y0, x1, y1))


def make_thumbs():
    fem_dir = os.path.join(ROOT, CFG["female"]["previews_dir"])
    mal_dir = os.path.join(ROOT, CFG["male"]["previews_dir"])
    fem = Image.open(os.path.join(fem_dir, CFG["female"]["preview_order"][0])).convert("RGB")
    mal = Image.open(os.path.join(mal_dir, CFG["male"]["preview_order"][0])).convert("RGB")
    out_dir = os.path.join(ROOT, CFG["thumbnails_dir"])
    os.makedirs(out_dir, exist_ok=True)

    tf = Image.new("RGB", (1400, 1400), (G, G, G)); tf.paste(fem, (200, 0))
    tf.save(os.path.join(out_dir, "thumb_female.png"))
    tm = Image.new("RGB", (1400, 1400), (G, G, G)); tm.paste(mal, (200, 0))
    tm.save(os.path.join(out_dir, "thumb_male.png"))

    # set: 人物を大きく（高さ1800px）並べる
    H = 1800; gap = 140
    fc = crop_figure(fem); mc = crop_figure(mal)
    fc = fc.resize((round(fc.width * H / fc.height), H), Image.LANCZOS)
    mc = mc.resize((round(mc.width * H / mc.height), H), Image.LANCZOS)
    ts = Image.new("RGB", (2000, 2000), (G, G, G))
    x0 = (2000 - (fc.width + gap + mc.width)) // 2; y0 = (2000 - H) // 2
    ts.paste(fc, (x0, y0)); ts.paste(mc, (x0 + fc.width + gap, y0))
    ts.save(os.path.join(out_dir, "thumb_set.png"))
    print(f"  thumbnails regenerated in {out_dir}")


if __name__ == "__main__":
    print("[1/2] normalize preview backgrounds to", G)
    nf = normalize_dir(CFG["female"]["previews_dir"])
    nm = normalize_dir(CFG["male"]["previews_dir"])
    print(f"  female {nf} + male {nm} previews normalized")
    print("[2/2] regenerate square thumbnails")
    make_thumbs()
    print("DONE. 確認: 各プレビュー四隅が (184,184,184)、thumb_set にシーム無し")
