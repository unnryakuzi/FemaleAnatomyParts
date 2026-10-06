# -*- coding: utf-8 -*-
"""既存の .glb に 2026-10 ライセンスの識別情報を足す（書き出し直さずに JSON チャンクだけ書き換える）。

  python scripts/listing/stamp_glb.py <in.glb> <out.glb>

scene.extras に kabe_tech_license / kabe_tech_license_id、mesh を持つ node.extras に kt_license を入れる。
バイナリ（BIN チャンク）は1バイトも触らない。
"""
import json
import struct
import sys

from apply_license_mark import MARK_ID, MARK_TEXT


def stamp(src, dst):
    b = open(src, "rb").read()
    magic, ver, _ = struct.unpack("<4sII", b[:12])
    assert magic == b"glTF" and ver == 2
    jlen, jtype = struct.unpack("<II", b[12:20])
    assert jtype == 0x4E4F534A
    j = json.loads(b[20:20 + jlen])
    rest = b[20 + jlen:]
    for sc in j.get("scenes", []):
        sc.setdefault("extras", {}).update({"kabe_tech_license": MARK_TEXT, "kabe_tech_license_id": MARK_ID})
    n = 0
    for nd in j.get("nodes", []):
        if "mesh" in nd:
            nd.setdefault("extras", {})["kt_license"] = MARK_ID
            n += 1
    js = json.dumps(j, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + len(rest)
    with open(dst, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(rest)
    print("[stamp_glb] %s: mesh node %d 個に %s" % (dst, n, MARK_ID))


if __name__ == "__main__":
    stamp(sys.argv[1], sys.argv[2])
