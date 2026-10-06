================================================================
 Male Anatomy Model  v1.2.1
 男性解剖モデル（écorché / 全身・内臓・血管・神経 / カラー版）
================================================================

(c) 2026 Kabe (Kabe-Tech)   https://kabe-tech.com
Contact / お問い合わせ:      https://kabe-tech.com/contact.html
License / ライセンス:        See LICENSE.txt (no redistribution / resale)

----------------------------------------------------------------
WHAT THIS IS / 概要
----------------------------------------------------------------
A static, full male anatomy reference model in A-pose. 939 separate
meshes: the skeleton, superficial + deep muscles, teeth, ligaments/
tendons, the internal systems — viscera/organs, blood vessels, brain
& nerves, the male reproductive organs — plus 2 optional underwear
meshes (see NEW below). The outer skin is included but can be hidden
to expose the musculature (écorché). Meshes carry trilingual labels
(Japanese / English / Latin, TA/FMA-based) as custom properties.

A-pose・純静的の男性解剖リファレンスモデル（フル解剖）。骨格・表層筋・
深層筋・歯・靱帯腱に加え、内臓・血管・脳神経・男性生殖器まで内部系統を
網羅した 939 個の独立メッシュ（うち 2 個は任意の下着。下記 NEW 参照）。
外皮は同梱されており、非表示にすれば筋層（écorché）を見られます。
各メッシュに日本語/英語/ラテン語の3言語ラベル（標準解剖名 TA/FMA 準拠）
をカスタムプロパティとして付与。

* Static model. NO rig / armature (intentional).
* 静的モデル。リグ（アーマチュア）は含みません（意図的）。
* Contains anatomical genitalia and internal organs (medical/educational).
* 解剖学的な生殖器・内臓を含みます（医学・教育用途）。

----------------------------------------------------------------
NEW in v1.2.1 / v1.2.1 の変更点
----------------------------------------------------------------
1) OPTIONAL UNDERWEAR / 任意の下着（2 メッシュ）

   下着_皮膚用(Brief_skin)    fitted to the SKIN surface
   下着_筋肉用(Brief_muscle)  fitted to the MUSCLE surface

   In the .blend they live in their own collection "_下着", so you can
   hide or delete the whole collection in one click and get exactly the
   v1.1.0 model back. Nothing else was changed: no vertex of the body
   was touched. Brief_skin is shown by default; Brief_muscle is hidden
   (use it when you hide the skin and want the brief to sit on the
   muscle surface instead).
   In .glb / .fbx / .obj both are present as ordinary named objects —
   hide or delete whichever you do not need. Brief_muscle sits inside
   the skin, so with the skin shown it is not visible.

   .blend では専用コレクション "_下着" に入れてあります。コレクションごと
   非表示／削除すれば v1.1.0 と完全に同じ状態に戻ります。素体メッシュは
   1 頂点も変更していません。既定では Brief_skin のみ表示（Brief_muscle は
   非表示）。皮膚を隠して筋層を見るときは Brief_muscle に切り替えてください。
   .glb / .fbx / .obj では通常の名前付きオブジェクトとして 2 つとも入って
   います。不要な方を非表示／削除してください。Brief_muscle は皮膚の内側に
   あるため、皮膚表示のままなら見えません。

2) LABELS ACTUALLY EMBEDDED / ラベルを実データへ付与

   In v1.1.0 the trilingual labels shipped only in index/ (CSV + HTML);
   they were NOT embedded in the model files. They are now embedded as
   custom properties on 932 of the 939 meshes.

   v1.1.0 では 3 言語ラベルが index/ の CSV・HTML にしか入っておらず、
   モデルファイル側には付与されていませんでした。v1.2.1 では 939 メッシュ
   中 932 個にカスタムプロパティとして実際に埋め込んでいます。

   Not labelled (7): the 2 underwear meshes, and 皮膚 / 頭毛 / 眉毛 / 耳 /
   口唇 (integument parts not present in the term dictionary).
   未付与の 7 個は下着 2 個と、皮膚・頭毛・眉毛・耳・口唇（用語辞書に
   未収録の外皮パーツ）です。索引 CSV も同様。

----------------------------------------------------------------
ANATOMICAL COLOR / カラー着色（v1.1.0 から継続）
----------------------------------------------------------------
Every mesh is colored by SYSTEM as vertex colors (no UV/texture
needed): muscles salmon/terracotta with per-muscle variation + cream
tendon attachments, bones ivory, ligaments white, teeth enamel-white
(gums pink), ARTERIES red / VEINS blue, brain pink-beige & nerves
cream-yellow, organs in realistic tones (liver red-brown, lungs pink,
heart red, kidneys red-brown), reproductive organs skin-red,
skin/eyes/hair natural. Left/right pairs share hue.
Color travels through all formats: glTF (COLOR_0), FBX (vertex color
layer), OBJ (per-vertex RGB; .mtl Kd falls back to muscle color).

全メッシュを系統別に頂点カラーで着色（UV/テクスチャ不要）。
筋肉=サーモン／テラコッタ（筋ごとに色味変化＋腱付着部クリーム白）、
骨=アイボリー、靱帯=白、歯=エナメル白（歯肉ピンク）、動脈=赤／静脈=青、
脳=ピンクベージュ・神経=クリーム黄、臓器=実物色（肝=赤茶・肺=ピンク・
心=赤・腎=赤茶）、生殖器=肌赤、皮膚/眼/毛=自然色。左右の筋は同色。
色は全形式に伝搬（glTF=COLOR_0、FBX=頂点カラー、OBJ=頂点RGB／.mtl の
Kd は筋色にフォールバック）。

Viewer note / 表示のこつ: in Blender, set the viewport shading color
to "Attribute" (Solid mode) to see the vertex colors.
Blender では Solid 表示のカラーを「アトリビュート」にすると見えます。

----------------------------------------------------------------
CONTENTS / 同梱物
----------------------------------------------------------------
README.txt / LICENSE.txt / CREDITS.txt

models/
  MaleAnatomy_v1.2.1.blend   Native Blender (recommended). No modifiers
                             are used — every mesh is already at full
                             resolution. モディファイアは未使用＝最初から
                             フル解像度です
  MaleAnatomy_v1.2.1.glb     glTF 2.0 — labels in "extras" + vertex color
  MaleAnatomy_v1.2.1.fbx     FBX — labels in user properties + vertex color
  MaleAnatomy_v1.2.1.obj     Wavefront OBJ (+ .mtl) + per-vertex RGB

index/
  解剖名インデックス_Man.csv   Name index for Excel (UTF-8 BOM, 931 rows)
  解剖名インデックス_Man.html  Printable index grouped by system
  anatomy_terms.json          JA->EN->LA dictionary

Each download is one format (blend / fbx / glb / obj); README, LICENSE,
CREDITS and index/ are included in every one.
ダウンロードは形式ごとに分かれています（blend / fbx / glb / obj）。
README・LICENSE・CREDITS・index/ はどれにも入っています。

----------------------------------------------------------------
LABELS BY FORMAT / 形式ごとのラベル
----------------------------------------------------------------
.blend  custom properties on 932 parts (name_ja / name_kana /
        name_en / name_la)
.glb    the same 4 properties in each node's "extras"
.fbx    the same 4 properties as user properties
.obj    NO custom properties (OBJ format limit); the object NAME is
        the Japanese anatomical name.

→ For English / Latin names when using .obj, look up
  index/解剖名インデックス_Man.csv.
→ .obj を使うときの英・羅名は index/解剖名インデックス_Man.csv で
  引いてください。

----------------------------------------------------------------
NOTE ON ACCURACY / 訳語について
----------------------------------------------------------------
Internal-system terms (vessels, nerves, organs) are marked conf=low in
the index where they should be cross-checked against FMA. 内臓・血管・
神経の一部は要照合(★)として索引に明示しています。

----------------------------------------------------------------
SCALE / スケール
----------------------------------------------------------------
Real-world scale (meters). Height approx. 1.684 m.
実寸（メートル）。全高およそ 1.684 m。

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

================================================================
