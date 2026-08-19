# 指示書：kabe-tech.com に解剖モデル商品をポートフォリオ追加

この指示書は MaleAnatomy プロジェクト（Blender解剖モデル販売）から渡されたもの。
kabe-tech サイトのリポジトリ側セッションで、以下の商品をポートフォリオ／作品紹介に追加してほしい。

## やること

1. kabe-tech.com の既存ポートフォリオ（作品紹介）の構造・書式を調査し、**それに合わせて**解剖モデルの紹介を追加する（新規ページでもカード追加でも、サイトの流儀に従う）
2. 紹介には下記の販売リンク6つを掲載する（Gumroad=海外向け・BOOTH=国内向けの2系統）
3. プレビュー画像を同梱素材からサイトに合わせて選定・最適化（リサイズ/WebP化等はサイトの慣例に従う）
4. 完了後、実描画（Playwright等でレイアウト計測＋スクリーンショット）まで確認してから報告すること（ユーザーのグローバルルール）

## 商品情報（事実）

### 製品名
- **Female Anatomy Model / 女性解剖モデル**（v1.66.1）
- **Male Anatomy Model / 男性解剖モデル**（v1.0.0）
- **男女セット / Male + Female Complete Pair**

### 共通仕様（コピーの素材に）
- A-pose・実寸（メートル）・純静的（リグなし）の écorché（皮膚除去解剖モデル）
- 全パーツに **日本語/英語/ラテン語の3言語ラベル**（標準解剖名 TA/FMA 準拠）をカスタムプロパティ＋CSV/HTML索引で付与
- 4形式同梱: .blend / .glb (glTF 2.0) / .fbx / .obj (+.mtl)
- ライセンス: **CC BY-SA 2.1 JP**（商用可・改変可・再配布可。出典: BodyParts3D©DBCLS → 3DAnatomyman(always3d) の派生）
- 女性版: **673パーツ**（骨格・筋肉・歯・靱帯腱・胸の形状）
- 男性版: **931パーツ**（骨格・筋肉・歯・靱帯腱 ＋ **内臓36・血管57・脳神経92・生殖器12**＝フル解剖）
- 制作ツール: Blender（+ Claude によるラベリング/パッケージング自動化）

### 販売リンク（6つ）

| 販路 | 商品 | 価格 | URL |
|---|---|---|---|
| Gumroad | Female Anatomy Model | $20 | https://liberation58.gumroad.com/l/zdlbhd |
| Gumroad | Male Anatomy Model | $20 | https://liberation58.gumroad.com/l/hgbvor |
| Gumroad | Male + Female Bundle | $32 | https://liberation58.gumroad.com/l/dbwncg |
| BOOTH | 女性解剖モデル | ¥2,980 | https://kabe-tech.booth.pm/items/8481858 |
| BOOTH | 男性解剖モデル | ¥2,980 | https://kabe-tech.booth.pm/items/8496247 |
| BOOTH | 【男女セット】 | ¥4,800 | https://kabe-tech.booth.pm/items/8496725 |

ショップトップ: https://kabe-tech.booth.pm / https://liberation58.gumroad.com

## 画像素材（ローカルパス）

- 女性版: `C:\Users\abesh\Documents\Blender\MaleAnatomy\配布パッケージ_v1.66.1\previews\`
  - 01_front / 02_front34(サムネ向き) / 03_back / 04_parts_colored(673分割の訴求) / 05_torso_closeup(品質訴求) / 06_index_sample(索引)
- 男性版: `C:\Users\abesh\Documents\Blender\MaleAnatomy\配布パッケージ_Man_v1.0.0\previews\`
  - 01_front / 02_front34(サムネ向き) / 03_back / 04_parts_colored / **05_internal_systems(内臓・血管・神経=最大の差別化画像)** / 06_index_sample

## 注意事項

- **BOOTH側はR-18登録**（解剖学的な生殖器・乳房形状を含むため）。ポートフォリオ掲載画像は **04_parts_colored・05_internal_systems・05_torso_closeup・03_back 等の局部が目立たないカット**を優先し、サイトのトーンに合わせて選定すること
- ライセンスは CC BY-SA 2.1 JP。サイト記載時は「商用利用可（CC BY-SA 2.1 JP）」程度の表記でOK（詳細は商品ページに記載済み）
- 文言の雛形は以下も参照可能（同プロジェクト内）:
  - `C:\Users\abesh\Documents\Blender\MaleAnatomy\商品説明文_v1.66.0.md`（女性版・日英）
  - `C:\Users\abesh\Documents\Blender\MaleAnatomy\商品説明文_Man_v1.0.0.md`（男性版・日英）

## 紹介文の例（短縮版・そのまま使用可）

> **Anatomy Model シリーズ（女性/男性/ペア）**
> 医学・教育・作画・3DCG向けの解剖3Dモデル。骨格・筋肉から内臓・血管・神経まで、
> 女性673／男性931の独立パーツに分割し、全パーツへ日英羅3言語の解剖名ラベルを付与。
> blend/glb/fbx/obj の4形式同梱、商用利用可（CC BY-SA 2.1 JP）。Gumroad・BOOTHで販売中。
