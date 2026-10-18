# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: tpose_port_render.py の画像を、視点ごとにタグの順で横に並べた1枚にする（システムの Python）
# python tpose_port_sheet.py <画像フォルダ> <出力フォルダ> <タグ=見出し> [<タグ=見出し> ...]
#  例: ... master="マスター v1.68.0（Aポーズ）" before="Tポーズ版 移植前" after="Tポーズ版 移植後"
import sys, os, glob, re
from PIL import Image, ImageDraw, ImageFont
SRC, DST = sys.argv[1:3]; COLS = [s.split("=", 1) for s in sys.argv[3:]]; os.makedirs(DST, exist_ok=True)
FONT = ImageFont.truetype(r"C:\Windows\Fonts\YuGothB.ttc", 30); SMALL = ImageFont.truetype(r"C:\Windows\Fonts\YuGothM.ttc", 26)
views = sorted({re.sub(r"_[^_]+\.png$", "", os.path.basename(p)) for p in glob.glob(os.path.join(SRC, "*.png"))})
for v in views:
    ims = [(lab, Image.open(os.path.join(SRC, "%s_%s.png" % (v, tag))).convert("RGB")) for tag, lab in COLS if os.path.exists(os.path.join(SRC, "%s_%s.png" % (v, tag)))]
    if len(ims) < 2: continue
    w, h = ims[0][1].size; HEAD = 96; GAP = 12
    sheet = Image.new("RGB", (len(ims) * w + (len(ims) - 1) * GAP, h + HEAD), (255, 255, 255)); dr = ImageDraw.Draw(sheet)
    title = v.split("_", 1)[1] if "_" in v else v
    for i, (lab, im) in enumerate(ims):
        x = i * (w + GAP); sheet.paste(im, (x, HEAD))
        dr.text((x + 16, 10), lab, fill=(20, 20, 20), font=FONT); dr.text((x + 16, 54), title, fill=(90, 90, 90), font=SMALL)
    out = os.path.join(DST, v + ".png"); sheet.save(out); print("SHEET", out)
