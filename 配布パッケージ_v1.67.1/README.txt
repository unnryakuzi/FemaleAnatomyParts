================================================================
 Female Anatomy Model  v1.67.1
 女性解剖モデル（écorché / 筋肉・骨格 / カラー版）
================================================================

(c) 2026 Kabe (Kabe-Tech)   https://kabe-tech.com
Contact / お問い合わせ:      https://kabe-tech.com/contact.html
License / ライセンス:        See LICENSE.txt (no redistribution / resale)

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
NEW in v1.67.1: ANATOMICAL COLOR / カラー版（v1.67.1 新規）
----------------------------------------------------------------
Every mesh is now colored as VERTEX COLORS (no UV/texture needed):
muscles in a salmon/terracotta reddish-brown with per-muscle
variation, tendon attachment areas fading to cream-white, ligaments
(linea alba, iliotibial tract, etc.) white, bones ivory, breast form
skin tone. Left/right pairs share the same hue.
The color travels through all formats: glTF (COLOR_0), FBX (vertex
color layer), OBJ (per-vertex RGB; .mtl Kd falls back to the muscle
color for viewers that ignore vertex colors).

全メッシュを頂点カラーで着色（UV/テクスチャ不要）。筋肉=サーモン／
テラコッタ系の赤褐色（筋ごとに色味を微変化）、腱の付着部=クリーム白
へグラデーション、靱帯（白線・腸脛靱帯など）=白、骨=アイボリー、
胸形状=肌色。左右の筋は同色。色は全形式に伝搬します（glTF=COLOR_0、
FBX=頂点カラー、OBJ=頂点ごとのRGB／非対応ビューア用に .mtl の Kd を
筋色にフォールバック）。

----------------------------------------------------------------
CONTENTS / 同梱物
----------------------------------------------------------------
README.txt              This file / 本ファイル
LICENSE.txt             License terms / ライセンス条文（日英）
CREDITS.txt             Required attribution / 必須クレジット（日英）

models/
  FemaleAnatomy_v1.67.1.blend   Native Blender file (recommended)
                                Blender ネイティブ（最も忠実・推奨）
  FemaleAnatomy_v1.67.1.glb     glTF 2.0 binary — labels kept in
                                node "extras" / ラベルを extras で保持
  FemaleAnatomy_v1.67.1.fbx     FBX — labels kept as user properties
                                / ラベルをユーザープロパティで保持
  FemaleAnatomy_v1.67.1.obj     Wavefront OBJ (+ .mtl)
  FemaleAnatomy_v1.67.1.mtl     Materials for the OBJ

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
IMPORTANT: LICENSE / 重要：ライセンス
----------------------------------------------------------------
本モデルは「BodyParts3D」© ライフサイエンス統合データベースセンター
（CC 表示 4.0 国際）を改変して作成しました。
商用・非商用を問わず、作品の制作に利用・改変できます。対象はイラスト・
漫画・映像などのほか、モデルを単体で取り出せない形でのゲームへの組み込み
も含みます。本モデルのデータそのもの（改変したものを含む）の再配布・転売・
共有は禁止します。

This model is an adaptation of "BodyParts3D" (c) The Database Center for
Life Science (CC BY 4.0).
You may use and modify it to create your own works, commercial or not:
illustrations, comics, video and more, including embedding it in a game in
a form where the model cannot be extracted on its own. Redistributing,
reselling or sharing the model data itself (including modified versions)
is prohibited.

Details and source attribution: LICENSE.txt / CREDITS.txt
詳細と出典表記は LICENSE.txt / CREDITS.txt を参照してください。

----------------------------------------------------------------
SOURCE / 出典
----------------------------------------------------------------
Adapted from "BodyParts3D" (c) DBCLS, CC BY 4.0. See CREDITS.txt.
「BodyParts3D」(DBCLS, CC 表示 4.0 国際) を改変。詳細 CREDITS.txt。
================================================================
