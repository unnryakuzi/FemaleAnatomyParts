# -*- coding: utf-8 -*-
"""compare/ の3枚組を「製品 | BP3D | 重ね」の横並び1枚に合成する。"""
import os
import re
from PIL import Image, ImageDraw

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
SRC = os.path.join(ROOT, "refs", "BodyParts3D_v4.0", "compare")
DST = os.path.join(ROOT, "refs", "BodyParts3D_v4.0", "compare_sheets")

LABEL = {"1_product": "PRODUCT (Man_All)", "2_bp3d": "BodyParts3D v4.0 (_99)",
         "3_overlay": "OVERLAY  grey=product / red=BP3D"}


def main():
    os.makedirs(DST, exist_ok=True)
    groups = {}
    for fn in os.listdir(SRC):
        m = re.match(r"(.+)_(front|side)_(1_product|2_bp3d|3_overlay)\.png$", fn)
        if m:
            groups.setdefault((m.group(1), m.group(2)), {})[m.group(3)] = fn

    for (tag, view), d in sorted(groups.items()):
        if len(d) != 3:
            continue
        ims = [Image.open(os.path.join(SRC, d[k])) for k in
               ("1_product", "2_bp3d", "3_overlay")]
        w, h = ims[0].size
        pad, top = 8, 34
        sheet = Image.new("RGB", (w * 3 + pad * 4, h + top + pad), (238, 238, 238))
        dr = ImageDraw.Draw(sheet)
        dr.text((pad, 6), "%s  [%s]" % (tag.replace("_", " "), view), fill=(20, 20, 20))
        for i, im in enumerate(ims):
            x = pad + i * (w + pad)
            sheet.paste(im, (x, top))
            dr.rectangle([x, top, x + w - 1, top + h - 1], outline=(150, 150, 150))
            dr.text((x + 6, top + 6), list(LABEL.values())[i], fill=(10, 10, 10))
        out = os.path.join(DST, "%s_%s.png" % (tag, view))
        sheet.save(out)
        print("->", os.path.basename(out))


if __name__ == "__main__":
    main()
