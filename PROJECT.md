# 女性解剖学3Dモデル — プロジェクト方針

**メインファイル**: `3DAnatomyFemale.blend`  
**作業ディレクトリ**: `C:\Users\abesh\Documents\Blender\MaleAnatomy\`  
**現バージョン**: v1.33.1

---

## 目的

この女性解剖学3Dモデルを**商品として販売する**。  
Booth / Gumroad を皮切りに、BlenderMarket / CGTrader へ拡大。

**絶対に守ること**: 機能追加・品質改善より「販売開始」が最優先。完璧を待たずに出す。

---

## ライセンス

元素材: **3DAnatomyMan**（Always3D / BodyParts3D）  
ライセンス: **CC BY-SA 2.1 JP**

| 項目 | 内容 |
|---|---|
| 商用販売 | ✅ OK |
| 改変・女性化 | ✅ OK |
| 派生物の販売 | ✅ OK |
| 継承義務 | ⚠️ 配布時に同ライセンス（CC BY-SA）で出す義務 |
| クレジット表記 | ⚠️ BodyParts3D / Always3D を必ず明記 |

販売商品には必ず `LICENSE.txt` と `CREDIT.txt` を同梱すること。

---

## モデル仕様

| 項目 | 内容 |
|---|---|
| 骨格 | 272個（個別オブジェクト、日本語名+ふりがな） |
| 表層筋 | 274個（Rig_部位別16コレクション） |
| 深層筋 | 175個（深層筋_部位別16サブコレクション） |
| 外皮参照 | 1個（Body_Tpose、静止参照用） |
| 合計メッシュ | 720個 |
| Armature | 22ボーン Mixamo互換（Unity Humanoid対応） |
| ウェイト | 全720メッシュに1ボーン100%割り当て済み |
| マテリアル | 6種（Material_Bone / Muscle_Surface / Muscle_Fiber / Muscle_Deep / Skin_Ref / Skin_Tex） |

### コレクション構造

```
骨格（272個）
Rig_右上腕 / 左上腕 / 右前腕 / 左前腕 / 右手 / 左手
Rig_右大腿 / 左大腿 / 右下腿 / 左下腿 / 右足 / 左足
Rig_胴体 / 頭頸部 / 骨盤 / 未分類
深層筋（非表示）
  └─ 深層筋_右上腕 〜 深層筋_骨盤 / 未分類（16サブコレクション）
女性外皮（Body_Tpose）
```

### Armatureボーン構成

```
Hips
├── Spine → Spine1 → Spine2 → Neck → Head
├── Spine2 → LeftShoulder → LeftArm → LeftForeArm → LeftHand
├── Spine2 → RightShoulder → RightArm → RightForeArm → RightHand
├── Hips → LeftUpLeg → LeftLeg → LeftFoot → LeftToeBase
└── Hips → RightUpLeg → RightLeg → RightFoot → RightToeBase
```

座標系: キャラクターは +Y 向き、左腕（Left）= +X側、右腕（Right）= −X側

---

## 販売フェーズ（現在: フェーズ1）

### フェーズ1: 販売開始（〜4週間）

#### Week 1: ファイル整備
- [x] コレクション整理（寛骨を骨格へ、深層筋16サブコレクション作成）
- [x] マテリアル整理（7→6種、命名統一）
- [x] 全メッシュへのウェイト設定（720個、1ボーン方式）
- [ ] リグ動作確認（T-Pose / A-Pose Action保存）
- [ ] 不要データブロック削除（orphan purge）

#### Week 2: 多形式エクスポート
出力先: `release/v1.0/`

```
FemaleAnatomy_v1.0.blend
FemaleAnatomy_v1.0.fbx         （T-Pose、リグ込み）
FemaleAnatomy_v1.0_APose.fbx   （A-Pose、リグ込み）
FemaleAnatomy_v1.0.glb         （Web/AR用）
FemaleAnatomy_LITE_v1.0.fbx    （軽量版 <10MB、Unity向け）
parts/                          （部位別16分割）
LICENSE.txt
CREDIT.txt
README_JP.md
README_EN.md
```

#### Week 3: ポートフォリオ撮影
- 360°ターンテーブル動画（全身・骨のみ・筋肉のみ）
- 部位アップ静止画（8〜12カット）
- リグ動作デモ動画（10〜20秒）

#### Week 4: 出品

| プラットフォーム | 価格 | 備考 |
|---|---|---|
| Booth | ¥7,800（フル版）/ ¥2,800（部位別） | 日本語ページ |
| Gumroad | $59（Full）/ $24（Parts） | 英語ページ |

告知: X（#blender3d #anatomy #b3d）、Reddit /r/blender、BlenderArtists.org

#### フェーズ1完了後の判断基準
- 月10本以上 → フェーズ2（BlenderMarket/CGTrader拡大）へ
- 月3〜9本 → 商品ページ改善後に拡大
- 月3本未満 → 価格・内容を見直し

### フェーズ2以降（フェーズ1の実績を見てから決定）
- BlenderMarket / CGTrader / Fab への展開
- 起始・停止PDF（解剖学チートシート）同梱
- TurboSquid CheckMate Pro認証取得
- メッシュ差し替えによるCC BY-SA縛り解除（長期）

---

## 差別化ポイント

- **日本語+ふりがな** — 解剖モデルで国内ほぼ唯一
- **女性ベース** — 解剖モデルは男性が多数派で希少
- **筋肉445個・骨格272個を個別オブジェクト化** — 部位の表示/非表示が自在
- **深層筋まで分離** — 教育用途で高い価値
- **Mixamo互換リグ** — Unity Humanoid対応、ゲーム/VR即戦力

---

## 競合

| 競合 | 価格 | 弱点 |
|---|---|---|
| Plasticboy Anatomy V9 | $299〜$2,499 | 英語のみ、CC非対応（再配布禁止） |
| CGTrader各種 | $20〜$300（リグなし） | ほぼリグなし、日本語なし |
| TurboSquid各種 | $800〜$2,400（リグあり） | 高額、日本語なし |

---

## やらないこと（絵に描いた餅を防ぐ）

- 販売前にYouTube動画を作り込む
- 販売前にメッシュ差し替えを始める
- 販売前にBlenderアドオン化作業を始める
- ポートフォリオを「完璧」にしてから出す（80点で出す）
- Pythonスクリプトでテクスチャを作り込む（旧目標、現在は対象外）

---

## FBXエクスポート設定（Mixamo互換）

```python
bpy.ops.export_scene.fbx(
    filepath=output_path,
    use_selection=True,
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',
    bake_space_transform=True,
    axis_forward='-Z',
    axis_up='Y',
    object_types={'ARMATURE', 'MESH'},
    use_mesh_modifiers=True,
    mesh_smooth_type='FACE',
    add_leaf_bones=False,
)
```

---

## 重要ファイルパス

| ファイル | 用途 |
|---|---|
| `3DAnatomyFemale.blend` | メインシーン |
| `backups/` | 作業前スナップショット |
| `scripts/` | Python自動化スクリプト18個 |
| `release/v1.0/` | 販売パッケージ出力先（未作成） |
| `C:\...\FemaleAnatomyTexture\knowledge\` | 解剖学知識ベース（PDF化候補） |
| `C:\...\FemaleAnatomyTexture\README.txt` | 元素材ライセンス確認済み |

---

## バージョン管理

### gitで管理するもの
- スクリプト (`scripts/*.py`)
- ドキュメント (`*.md`, `VERSION`)
- 解剖学知識ベース (`knowledge/`)

### gitで管理しないもの（バイナリ・大容量）
- `.blend` ファイル（500MB超のため .gitignore 除外済み）
- `.fbx` / `.glb` 等のエクスポートファイル
- `backups/` 内のスナップショット

### .blendファイルのバックアップルール
**.blendはgit管理外のため、作業の前後で手動バックアップを作成して変更履歴を保護する。**

| タイミング | 操作 | 命名規則 |
|---|---|---|
| **大きな変更の前** | `backups/` にコピー | `3DAnatomyFemale_before_<作業内容>_YYYYMMDD.blend` |
| **セッション終了時** | `bump_version()` を呼ぶ | `.blend`保存 + `CHANGELOG.md`記録 |

```python
# Blender内で実行（作業前スナップショット）
import bpy, shutil, os
from datetime import datetime
src = bpy.data.filepath
dst = os.path.join(os.path.dirname(src), "backups",
      f"3DAnatomyFemale_before_<説明>_{datetime.now().strftime('%Y%m%d')}.blend")
bpy.ops.wm.save_mainfile()
shutil.copy2(src, dst)
print(f"バックアップ: {dst}")
```

```python
# セッション終了時（バージョン更新）
bump_version('patch', '変更内容')   # 位置調整・微修正
bump_version('minor', '変更内容')   # 筋肉追加・大幅再配置
bump_version('major', '変更内容')   # 構造的変更
```

- `VERSION` ファイル: 現在バージョン
- `CHANGELOG.md`: 変更履歴（`bump_version()` が自動記録）
