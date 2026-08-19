================================================================
 Female Anatomy Model  v1.66.1
 女性解剖モデル（écorché / 筋肉・骨格）
================================================================

(c) 2026 Kabe (Kabe-Tech)   https://kabe-tech.com
Contact / お問い合わせ:      https://kabe-tech.com/contact.html
License / ライセンス:        CC BY-SA 2.1 JP  (see LICENSE.txt)

----------------------------------------------------------------
WHAT THIS IS / 概要
----------------------------------------------------------------
A static, anatomically corrected female anatomy ECORCHE in A-pose
(outer body/head skin removed to show the musculature; the breast
form is kept). 673 separate meshes (skeleton, muscles, teeth,
cartilage, ligaments, breast form). Every mesh carries trilingual
labels (Japanese / English / Latin, TA/FMA-based) as custom properties.

A-pose・純静的の女性解剖écorché（筋層を見せるため全身・頭部の外皮は
除去、胸の形状は残存）。骨格・筋肉・歯・軟骨・靱帯・胸形状を 673 個の
独立メッシュに分割。各メッシュに日本語/英語/ラテン語の3言語ラベル
（標準解剖名 TA/FMA 準拠）をカスタムプロパティとして付与しています。

* This is a STATIC model. It has NO rig / armature (intentional).
* これは静的モデルです。リグ（アーマチュア）は含みません（意図的）。

----------------------------------------------------------------
CONTENTS / 同梱物
----------------------------------------------------------------
README.txt              This file / 本ファイル
LICENSE.txt             License terms / ライセンス条文（日英）
CREDITS.txt             Required attribution / 必須クレジット（日英）

models/
  FemaleAnatomy_v1.66.1.blend   Native Blender file (recommended)
                                Blender ネイティブ（最も忠実・推奨）
  FemaleAnatomy_v1.66.1.glb     glTF 2.0 binary — labels kept in
                                node "extras" / ラベルを extras で保持
  FemaleAnatomy_v1.66.1.fbx     FBX — labels kept as user properties
                                / ラベルをユーザープロパティで保持
  FemaleAnatomy_v1.66.1.obj     Wavefront OBJ (+ .mtl)
  FemaleAnatomy_v1.66.1.mtl     Materials for the OBJ

index/
  解剖名インデックス.csv          Name index for Excel (UTF-8 BOM, 673 rows)
                                日英羅の対訳索引（Excel用）
  解剖名インデックス.html         Printable index grouped by region
                                部位別索引（ブラウザでPDF印刷可）
  anatomy_terms.json            JA->EN->LA dictionary (285 unique terms)
                                対訳辞書

----------------------------------------------------------------
LABELS BY FORMAT / 形式ごとのラベルの残り方
----------------------------------------------------------------
.blend  full custom properties (name_ja / name_kana / name_en / name_la)
.glb    custom properties kept in each node's "extras"
.fbx    custom properties kept as user-defined properties
.obj    NO custom properties (OBJ limitation). The object NAME equals
        the Japanese anatomical name, so use index/解剖名インデックス.csv
        to look up English / Latin.

.obj はカスタムプロパティを保持できません（OBJ の仕様）。オブジェクト名＝
日本語の解剖名なので、英語/ラテン語は index/解剖名インデックス.csv で
引いてください。

----------------------------------------------------------------
SCALE / スケール
----------------------------------------------------------------
Modeled at real-world scale (meters). Adult female proportions.
実寸（メートル）でモデリング。成人女性プロポーション。

----------------------------------------------------------------
IMPORTANT: LICENSE / 重要：ライセンス（CC BY-SA 2.1 JP）
----------------------------------------------------------------
You may use this model commercially, modify it, and redistribute it.
You MUST keep the attribution (CREDITS.txt), link the license, and
indicate changes. Derivatives must also be CC BY-SA 2.1 JP.

商用利用・改変・再配布が可能です。CREDITS.txt のクレジット保持、
ライセンスへのリンク提示、変更の明示が必要です。派生物も
CC BY-SA 2.1 JP で頒布してください。詳細は LICENSE.txt / CREDITS.txt。

----------------------------------------------------------------
SOURCE / 出典
----------------------------------------------------------------
Derived from "3DAnatomyman" (always3d), itself derived from
"BodyParts3D" (c) DBCLS. Full chain in CREDITS.txt.
「3DAnatomyman」(always3d)→「BodyParts3D」(DBCLS) の派生。
詳細は CREDITS.txt。
================================================================
