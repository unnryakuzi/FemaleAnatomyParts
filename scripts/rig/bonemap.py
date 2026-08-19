# -*- coding: utf-8 -*-
"""骨オブジェクト名 → Mixamo互換22ボーン の対応表。
Blender側スクリプトからもimportして使う（同じ規則を二重管理しないため）。
判定は「上から順に最初に当たったルール」を採用する＝順序が意味を持つ。
"""
import re

L, R = "Left", "Right"


def side(name):
    if name.startswith("右"):
        return R
    if name.startswith("左"):
        return L
    return None


# (判定関数, ボーン名) を上から順に評価する。
# sideがNoneの中心骨は左右非依存のボーンへ入れる。
RULES = [
    # --- 歯（上顎歯・下顎歯とも Head。下顎骨自体もHeadなので開口は表現しない） ---
    (lambda n: any(k in n for k in ["切歯", "犬歯", "臼歯"]), lambda n: "Head"),

    # --- 頭部（頭蓋を構成する骨はすべてHead） ---
    (lambda n: any(k in n for k in [
        "前頭骨", "頭頂骨", "側頭骨", "後頭", "蝶形骨", "篩骨", "鋤骨",
        "涙骨", "鼻骨", "鼻軟骨", "上顎骨", "下顎骨", "口蓋骨", "頬骨",
        "下鼻甲介", "環椎", "軸椎",
    ]), lambda n: "Head"),

    # --- 頸部 ---
    (lambda n: ("頚椎" in n) or ("隆椎" in n) or ("舌骨" in n) or ("甲状軟骨" in n),
     lambda n: "Neck"),

    # --- 手（手根骨・中手骨・指骨）※「趾」ではなく「指」 ---
    (lambda n: any(k in n for k in [
        "手舟状骨", "月状骨", "三角骨", "豆状骨", "大菱形骨", "小菱形骨",
        "有頭骨", "有鈎骨", "中手骨",
    ]) or ("指" in n and "節骨" in n),
     lambda n: f"{side(n)}Hand"),

    # --- 踵骨腱（アキレス腱）: 「踵骨」を含むので足のルールより先に置く ---
    # 実測(SkeletonSKU 2026-08-08): Z幅24cmの長い腱。Foot に付けると足関節±30°で
    # 腱全体がふくらはぎから振り出されて明らかに破綻する。Leg なら下腿軸に沿ったまま。
    (lambda n: "踵骨腱" in n, lambda n: f"{side(n)}Leg"),

    # --- 足指（趾骨・種子骨） ---
    (lambda n: ("趾" in n and "節骨" in n) or ("種子骨" in n),
     lambda n: f"{side(n)}ToeBase" if side(n) else "LeftToeBase"),

    # --- 足（足根骨・中足骨） ---
    (lambda n: any(k in n for k in [
        "距骨", "踵骨", "足舟状骨", "立方骨", "楔状骨", "中足骨",
    ]), lambda n: f"{side(n)}Foot"),

    # --- 下腿 ---
    (lambda n: any(k in n for k in ["脛骨", "腓骨"]),
     lambda n: f"{side(n)}Leg"),

    # --- 大腿 ---
    # 膝蓋骨は脛骨ではなく大腿骨と関節する（膝蓋大腿関節）。Leg に付けると膝90°屈曲で
    # 大腿骨から30mm離れて宙に浮く。UpLeg なら3mm（レストと同じ）を保つ。実測で確認済み。
    (lambda n: ("大腿骨" in n) or ("膝蓋骨" in n), lambda n: f"{side(n)}UpLeg"),

    # --- 前腕 ---
    (lambda n: ("橈骨" in n) or ("尺骨" in n), lambda n: f"{side(n)}ForeArm"),

    # --- 上腕 ---
    (lambda n: "上腕骨" in n, lambda n: f"{side(n)}Arm"),

    # --- 肩帯 ---
    (lambda n: ("鎖骨" in n) or ("肩甲骨" in n), lambda n: f"{side(n)}Shoulder"),

    # --- 骨盤 ---
    (lambda n: ("寛骨" in n) or ("仙骨" in n) or ("仙椎" in n) or ("尾骨" in n),
     lambda n: "Hips"),

    # --- 腰椎 ---
    (lambda n: "腰椎" in n, lambda n: "Spine"),

    # --- 胸郭は分割しない: 胸椎・肋骨・肋軟骨・胸骨をまとめて Spine1 ---
    # 胸郭は「胸椎→肋骨→肋軟骨→胸骨」で閉じた輪をなす。1ボーン100%の剛体バインドでは
    # 2ボーンに割ると必ず2箇所で切れる。実測(SkeletonSKU 2026-08-08)では胸骨が
    # 柄(Spine2)と体(Spine1)に分かれており、胴を捻ると**胸骨体が胸郭から完全に取り残された**。
    # → 胸郭全体を Spine1 に集約する。回転中心が T12/L1（胸郭の下端）になるので
    #   「胸郭が腰から生えて動く」自然な挙動になる。
    #   Spine2 は割当なしになるが、子の Neck/Head/Shoulder/腕 は動くので上半身の動きは残る。
    (lambda n: any(k in n for k in [
        "胸椎", "肋骨", "肋軟骨", "胸骨体", "胸骨柄", "剣状突起",
    ]), lambda n: "Spine1"),
]

# NOTE: かつて胸椎/肋骨を 1-6=Spine2 / 7-12=Spine1 に割る _thorax() があったが、
# 胸郭が前面（胸骨）で割れて破綻したため廃止した。番号を読む _num()/_KANJI_NUM も
# 他から使われていないので併せて削除している（2026-08-08）。


def map_bone(name):
    base = re.sub(r"\(.*?\)", "", name).strip()
    for test, bone in RULES:
        if test(base):
            b = bone(base)
            if b and "None" not in b:
                return b
    return None


MIXAMO_BONES = [
    "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
