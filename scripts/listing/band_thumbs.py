# カラー版のサムネに、筋肉解剖ボディ・骨格と同じ作りの帯（太字の系統名＋要点1行）を入れる（2026-10-31 ユーザー決定: Gumroad 案2）
#   背景は他の系統と同じ「上が白・下が明るいグレー」。人物は thumb_<p>(_sw).png から背景グレー(184)を抜いて置き直す
#   出力: thumbnails/thumb_<female|male|set>_band_<ja|en>.png（ja=BOOTH用の下着版、en=Gumroad用のカラーそのまま）
#   試作のときは STYLE=A で、背景グレーのまま下に明るい帯を足した版も作れる
# python scripts/listing/band_thumbs.py [出力フォルダ（既定 thumbnails）]
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

ROOT = "C:/Users/abesh/Documents/Blender/MaleAnatomy/thumbnails"
OUT = sys.argv[1] if len(sys.argv) > 1 else ROOT
STYLES = os.environ.get("STYLE", "B")
S, CAP = 1400, 230
SRC = {"female": ("thumb_female_sw.png", "thumb_female.png"),
       "male": ("thumb_male_sw.png", "thumb_male.png"),
       "set": ("thumb_set_sw.png", "thumb_set.png")}
TXT = {"ja": {"female": ("カラー解剖モデル", "女性　・　716パーツ　・　筋肉・骨格　・　3言語ラベル"),
              "male": ("カラー解剖モデル", "男性　・　939パーツ　・　筋肉・骨格・内臓・血管・神経"),
              "set": ("カラー解剖モデル　男女セット", "女性716＋男性939パーツ　・　3言語ラベル　・　A-pose")},
       "en": {"female": ("COLORED ANATOMY MODEL", "Female  ·  716 parts  ·  muscles & skeleton  ·  trilingual labels"),
              "male": ("COLORED ANATOMY MODEL", "Male  ·  939 parts  ·  muscles, skeleton, organs, vessels & nerves"),
              "set": ("COLORED ANATOMY SET", "Female + Male  ·  716 + 939 parts  ·  trilingual labels")}}


def figure_rgba(path):
    """背景グレー(184)のうち外周につながる部分を透明にして、人物だけを切り出す"""
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    near = np.abs(a - 184).max(axis=2) <= 10
    lab, _ = ndimage.label(near)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge))
    alpha = Image.fromarray(np.where(bg, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    im = Image.open(path).convert("RGBA"); im.putalpha(alpha)
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())


def compose(fig, style, t1, t2, lang):
    box_w, box_h = S - 80, S - CAP - 50
    sc = min(box_w / fig.width, box_h / fig.height)
    fig = fig.resize((round(fig.width * sc), round(fig.height * sc)), Image.LANCZOS)
    bg = Image.new("RGBA", (S, S))
    d = ImageDraw.Draw(bg)
    if style == "A":
        d.rectangle([0, 0, S, S - CAP], fill=(184, 184, 184, 255))
        d.rectangle([0, S - CAP, S, S], fill=(240, 240, 240, 255))
    else:
        for y in range(S):   # compose_thumb2.py と同じグラデーション
            c = round(250 - 22 * y / S); d.line([(0, y), (S, y)], fill=(c, c, c, 255))
    bg.alpha_composite(fig, ((S - fig.width) // 2, 30 + (box_h - fig.height) // 2))
    d = ImageDraw.Draw(bg)
    f1 = ImageFont.truetype("C:/Windows/Fonts/meiryob.ttc", 92 if lang == "ja" else 84)
    f2 = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 38)
    d.text((60, S - CAP + 18), t1, font=f1, fill=(25, 25, 25)); d.text((64, S - CAP + 140), t2, font=f2, fill=(80, 80, 80))
    for t, f in ((t1, f1), (t2, f2)): assert d.textlength(t, font=f) < S - 100, t   # 1行に収まること
    return bg.convert("RGB")


for key, (sw, plain) in SRC.items():
    for lang, src in (("ja", sw), ("en", plain)):   # BOOTH=下着版(sw)・日本語、Gumroad=カラーそのまま・英語
        fig = figure_rgba(os.path.join(ROOT, src))
        for style in STYLES:
            t1, t2 = TXT[lang][key]
            p = os.path.join(OUT, f"thumb_{key}_band_{lang}.png" if STYLES == "B" else f"band{style}_{key}_{lang}.png")
            compose(fig, style, t1, t2, lang).save(p); print(p)
