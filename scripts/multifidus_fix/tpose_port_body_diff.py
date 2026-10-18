# Tポーズ版へ v1.68.0 の修正を移す（2026-10-18）: tpose_port_body_render.py の2つのタグの画像を並べ、色が変わった画素を赤で示す（システムの Python）
# python tpose_port_body_diff.py <画像フォルダ> <出力フォルダ> <タグA=見出しA> <タグB=見出しB> [しきい値=24]
import sys, os, glob, re, numpy as np
from PIL import Image, ImageDraw, ImageFont
SRC, DST = sys.argv[1:3]; (TA, LA), (TB, LB) = (s.split("=", 1) for s in sys.argv[3:5]); TH = int(sys.argv[5]) if len(sys.argv) > 5 else 24
os.makedirs(DST, exist_ok=True); F = ImageFont.truetype(r"C:\Windows\Fonts\YuGothB.ttc", 28); FS = ImageFont.truetype(r"C:\Windows\Fonts\YuGothM.ttc", 24)
for pa in sorted(glob.glob(os.path.join(SRC, "*_%s.png" % TA))):
    v = os.path.basename(pa)[: -len("_%s.png" % TA)]; pb = os.path.join(SRC, "%s_%s.png" % (v, TB))
    if not os.path.exists(pb): continue
    A = np.asarray(Image.open(pa).convert("RGB")).astype(int); B = np.asarray(Image.open(pb).convert("RGB")).astype(int)
    d = np.abs(A - B).max(2) > TH
    g = (B.mean(2, keepdims=True) * 0.6 + 70).clip(0, 255).repeat(3, 2); g[d] = (230, 30, 30)
    ims = [(LA, A), (LB, B), ("色が変わった画素（赤）%d 画素" % int(d.sum()), g)]
    w, h = A.shape[1], A.shape[0]; HEAD = 90; GAP = 12
    sheet = Image.new("RGB", (3 * w + 2 * GAP, h + HEAD), (255, 255, 255)); dr = ImageDraw.Draw(sheet)
    for i, (lab, im) in enumerate(ims):
        x = i * (w + GAP); sheet.paste(Image.fromarray(im.astype(np.uint8)), (x, HEAD)); dr.text((x + 14, 8), lab, fill=(20, 20, 20), font=F)
        dr.text((x + 14, 50), v.split("_", 1)[1], fill=(90, 90, 90), font=FS)
    out = os.path.join(DST, v + ".png"); sheet.save(out); print("SHEET", out, int(d.sum()))
