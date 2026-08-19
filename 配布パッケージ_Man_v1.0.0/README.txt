================================================================
 Male Anatomy Model  v1.0.0
 男性解剖モデル（écorché / 全身・内臓・血管・神経）
================================================================

(c) 2026 Kabe (Kabe-Tech)   https://kabe-tech.com
Contact / お問い合わせ:      https://kabe-tech.com/contact.html
License / ライセンス:        CC BY-SA 2.1 JP  (see LICENSE.txt)

----------------------------------------------------------------
WHAT THIS IS / 概要
----------------------------------------------------------------
A static, full male anatomy reference model in A-pose. 931 separate
meshes covering the skeleton, superficial + deep muscles, teeth,
ligaments/tendons, AND the internal systems — viscera/organs, blood
vessels, brain & nerves, and the male reproductive organs. The outer
skin is removed (écorché) to show the musculature. Every mesh carries
trilingual labels (Japanese / English / Latin, TA/FMA-based) as custom
properties.

A-pose・純静的の男性解剖リファレンスモデル（フル解剖）。骨格・表層筋・
深層筋・歯・靱帯腱に加え、内臓・血管・脳神経・男性生殖器まで内部系統を
網羅した 931 個の独立メッシュ。外皮は除去（écorché）し筋層を見せます。
各メッシュに日本語/英語/ラテン語の3言語ラベル（標準解剖名 TA/FMA 準拠）
をカスタムプロパティとして付与。

* Static model. NO rig / armature (intentional).
* 静的モデル。リグ（アーマチュア）は含みません（意図的）。
* Contains anatomical genitalia and internal organs (medical/educational).
* 解剖学的な生殖器・内臓を含みます（医学・教育用途）。

----------------------------------------------------------------
CONTENTS / 同梱物
----------------------------------------------------------------
README.txt / LICENSE.txt / CREDITS.txt

models/
  MaleAnatomy_v1.0.0.blend   Native Blender (recommended). Heavy muscles
                             carry a Decimate modifier — turn it OFF to
                             get full resolution. 重い筋はDecimate付き＝
                             OFFでフル解像度に戻せます（軽量/高精細両対応）
  MaleAnatomy_v1.0.0.glb     glTF 2.0 — labels kept in node "extras"
  MaleAnatomy_v1.0.0.fbx     FBX (modifiers baked)
  MaleAnatomy_v1.0.0.obj     Wavefront OBJ (+ .mtl), modifiers baked

index/
  解剖名インデックス_Man.csv   Name index for Excel (UTF-8 BOM, 931 rows)
  解剖名インデックス_Man.html  Printable index grouped by system
  anatomy_terms.json          JA->EN->LA dictionary

----------------------------------------------------------------
LABELS BY FORMAT / 形式ごとのラベル
----------------------------------------------------------------
.blend  full custom properties on all 931 parts (name_ja/kana/en/la)
.glb    full custom properties in each node's "extras" (all 931)
.fbx    custom properties on most parts; a minority are omitted by the
        FBX exporter (object names with special characters).
.obj    NO custom properties (OBJ limit); the object NAME = Japanese name.

→ For COMPLETE English / Latin names for every part, use the .blend or
  .glb, or look up index/解剖名インデックス_Man.csv (covers all 931).
→ 全パーツの英・羅名は .blend / .glb か、index/解剖名インデックス_Man.csv
  （931件すべて収録）で引いてください。FBX/OBJは一部ラベルが付きません。

----------------------------------------------------------------
NOTE ON ACCURACY / 訳語について
----------------------------------------------------------------
Internal-system terms (vessels, nerves, organs) are marked conf=low in
the index where they should be cross-checked against FMA. 内臓・血管・
神経の一部は要照合(★)として索引に明示しています。

----------------------------------------------------------------
SCALE / スケール
----------------------------------------------------------------
Real-world scale (meters). 実寸（メートル）。

----------------------------------------------------------------
LICENSE (CC BY-SA 2.1 JP) — IMPORTANT
----------------------------------------------------------------
Commercial use, modification, and redistribution are allowed. Because of
ShareAlike, anyone who obtains this model gets the SAME rights and may
redistribute/resell it; the seller cannot forbid that. You must keep
CREDITS.txt, link the license, and indicate changes.

商用利用・改変・再配布が可能です。継承(SA)条件により、入手者も同じ権利を
持ち再配布・転売できます（販売者が独自に禁止できません）。CREDITS.txt の
保持、ライセンスへのリンク、変更の明示が必要です。詳細は LICENSE.txt。

Derived from "3DAnatomyman" (always3d), from "BodyParts3D" (c) DBCLS.
「3DAnatomyman」(always3d)→「BodyParts3D」(DBCLS) の派生。詳細 CREDITS.txt。
================================================================
