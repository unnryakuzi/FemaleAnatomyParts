# MaleAnatomy プロジェクト固有ルール

Blender 解剖モデル編集プロジェクト用の作業ルール。

## ライセンス（2026-10-07 確定・切替済み）

**配布物のライセンスは「BodyParts3D（CC BY 4.0）の改変物／本モデルのデータの再配布・転売・共有は禁止」。**
CC BY-SA 2.1 JP には戻さない。文面の正は `scripts/listing/rewrite_license_texts.py`（LICENSE/CREDITS/README）と
`scripts/listing/license_desc_2026_10.js`（BOOTH/Gumroad の説明文）。

- 根拠: DBCLS 箕輪氏の回答（2026-10-06）「生命科学系データベースアーカイブから DL できるデータは CC BY 4.0」。
  製品の元データはアーカイブ旧リリース `20110915/BodyParts3D_3.0_obj_95.zip` と全934パーツ完全一致（`refs/provenance_audit_summary.md` §9）。
  always3d の配布物はこれを FBX に変換しただけ
- 2026-10 より前に配布した版（識別子なし）は CC BY-SA 2.1 JP のまま（CC は撤回できない）

### ★配布物には必ず識別子 `KT-L2026-10` を入れる（ユーザー指示 2026-10-07・全セッション共通）

新版を書き出す・zip を作り直す・別形式を足すときは、**全形式に識別子が入っていることを確かめてから出品する**。
識別子の有無で「旧ライセンス（BY-SA）版」と「転売禁止の新版」を見分ける。**形状に透かしを仕込む等はしない（やりすぎ・ユーザー判断）。**

| 形式 | 入れる場所 | 入れ方 |
|---|---|---|
| .blend | シーン `kabe_tech_license` / `kabe_tech_license_id`、全 MESH/EMPTY/ARMATURE に `kt_license` | `apply_license_mark.py` |
| .fbx | 上のカスタムプロパティ（user property） | `use_custom_props=True` で書き出す |
| .glb | scene.extras / mesh node の extras | `export_extras=True`。既存 glb なら `stamp_glb.py`（BIN 不変） |
| .obj / .mtl | 先頭コメント | `stamp_obj.py` |

- **`export_dist.py` は自動で入れて検証する**（識別子が無いと verify で止まる）。別の手段で書き出すときだけ上の個別スクリプトを使う
- 識別子の文字列・文面を変えるときは `apply_license_mark.py` の `MARK_ID` / `MARK_TEXT` だけを直す（他スクリプトはここを読む）
- 公開済みファイルに印だけ足すときは、書き出し直さずに stamp 系で足す（2026-10-07: 公開版の女性 .blend にはガイド線2本が残っており、書き出し直すと glb/obj のパーツ数が変わった）

## バージョン管理（詳細・体系は skill `blender-anatomy-mesh` §2 が正）
- 削除・再作成・大規模変更の**前に必ず** `save_snapshot('説明')`（復元: `list_snapshots()` → `restore_snapshot(i)`）
- モデルを変更したセッションの**終わりに必ず** `bump_version('patch'|'minor'|'major', '説明')`（.blend保存＋VERSION/CHANGELOG.md更新。`git_commit=True` でcommit同時実行）

## 関数使用上の注意
- `set_view()` はデフォルトでシェーディングモードを変更しない（`shading=None`）
- `bpy.ops.object.transform_apply()` を呼ぶ前に必ず対象オブジェクトのみ select する

## ビューポート表示制御（必須）
- 表示/非表示は `obj.hide_set()`（目玉アイコン）を使い `obj.hide_viewport` は使わない（共通ルール、理由は skill `blender-anatomy-mesh` 参照）
- **ただし既存データには `hide_viewport=True`（モニタアイコン）が混在している**（Body_Tpose・Head_Base・Breast_Base・一部の筋）。「全身表示」等の表示処理では **目玉(`hide_set`)とモニタ(`hide_viewport`)の両方を解除**しないと一部が取り残される
  - skill `blender-anatomy-mesh` の `visual_debug.show_full_body()` が両方解除＋median-zフレーミングを実装済み。`include_skin=False`(既定)で皮膚ベースは除外

## bpy.ops の使用制限（クラッシュ防止）
- 大規模メッシュ（>50k頂点）に対し Edit Mode 経由の `bpy.ops.mesh.*` は使わない
  （`bpy.ops.mesh.flip_normals` で 65k〜130k頂点メッシュ Blender クラッシュの実績あり）
- 代わりに bmesh API を使う：
  ```python
  import bmesh
  bm = bmesh.new()
  bm.from_mesh(mesh)
  # 操作（v.co 変更、f.normal_flip() 等）
  bm.normal_update()
  bm.to_mesh(mesh)
  bm.free()
  mesh.update()
  ```
- `bpy.ops.object.duplicate()` も Edit Mode 残留時に context エラーで失敗することがある。
  代わりに `new_mesh = obj.data.copy()` + `bpy.data.objects.new(name, new_mesh)` で複製する

## Z依存メッシュ変形ルール（水平線・段差を出さないために）
- Z依存の頂点変形を**複数パス重ねると**遷移境界に水平線が残る。**クリーン状態 × 単一パス**が原則
  1. 変形前スナップショットからパーツを再インポート（累積変形のないクリーンなメッシュ）
  2. 参照と新規の断面差を全Z域で計測（10〜20mm刻み）→ 移動平均でスムース化
  3. テーブルを線形補間した**単一パス**で全頂点に適用
- やり直しが必要になったらパスを追加せずクリーン状態に戻す

- **局所的なY平行移動（単一オブジェクト）** にはプラトー＋コサインフェード解析関数を使う
  - `z_plateau` 以下: 定数 `amp`（勾配ゼロ → 段差不発生）
  - `z_plateau` 〜 `z_end`: `amp * (1 + cos(π*t)) / 2` で0へ収束（C1連続）
  - `amp` = 補正必要域の実測Δ中央値、`z_plateau` = Δ最大Z、`z_end` = Δ≈0のZ
  - 実測テーブルの折れ線補間は使わない（10mm間隔の傾き変化が段差になる）

## 厚み保持の鉄則
- **shift は (z) 一次元関数のみ**。`shift(x, z)` の2次元グリッドは bilinear / nearest どちらでも厚みを破壊する
  - bilinear: 厚み方向の頂点ペアが微妙にずれた (x, z) を持つため、補間で異なる shift を受け 30〜40% 厚み減少
  - nearest: 同一ビンは厚み維持できるが、ビン境界で段差が生じてメッシュの質感が壊れる
- Z軸関数なら同じ (x, z) の頂点全てが完全に同じ shift を受け、厚みは局所的に完全保持（±1mm以内）
- X方向のばらつきは「許容するか別手法に切替えるか」をユーザーに確認する。Z関数では補正できない
- 集計は **median**（中央値）を使う。Body 表面のレイキャストは局所凹凸でノイズ混入、平均より median が外れ値耐性

## 変形試行錯誤の脱出ルール（迷路に陥ったら手法を変える）
- POST_*プレビュー版を3回以上作ってもユーザーが満足しない場合、自分の調整（offset値・Shrinkwrap・blend比率）を続けるのではなく、ユーザー編集ライン方式に切り替える：
  1. 対象部位の特徴ライン（例: Y_max contour）を Z 刻みで抽出してポリラインカーブにする
     - 命名: `CURRENT_<部位>_<特徴名>ライン`（例: `CURRENT_胸最長筋広背筋側ライン`）
     - 12〜14点に間引き、bevel_depth=0.002〜 で見やすく、show_in_front=True
  2. **抽出時の各点XYZをコード内に prev_values として保存**（後で差分計算するため必須）
  3. ユーザーが Edit Mode で各点を理想位置にドラッグ編集
  4. 編集後座標と prev_values の差分で shift_y_mm(z) を構築、全頂点に適用
- 「これじゃない」「分かりません？」「指示と違う」が3回続いたら手法ごと見直す合図

## Shrinkwrap・per-vertex push の失敗パターン（避ける）
- 解剖メッシュ間の突抜回避で以下は形状破綻するため避ける：
  - **Blender標準 Shrinkwrap modifier**（NEAREST_SURFACEPOINT + INSIDE）→ メッシュ全潰れ
  - **手動 per-vertex push**（BVH最近点 + outward方向押し戻し）→ tentacle状凹凸
  - **大幅な一律 Y offset**（-3mm以上）→ 解剖学的に過剰移動
- 代替策の優先順位：
  1. 上記「ユーザー編集ライン方式」（最も確実）
  2. 小規模offset（-1mm）で残突抜数百頂点を許容（視覚的に問題なければOK）
  3. Group変形（同一shift）— 隣接筋肉が同じ動きをすべき時のみ

## 薄いシート筋の突き抜け判定は目視を最終判定にする
- 広頚筋のような**薄いシート筋 × 深層筋**（胸鎖乳突筋等）の突き抜け修正では、レイキャスト/最近点の**数値メトリクスがフォールド・自由縁・湾曲で誤検出**し、完全ゼロを追うと堂々巡りになる
  - 単一 global outward は湾曲筋（内側=胸骨頭は前向き、外側は外向き）に合わず、特定帯だけ収束しない
  - 平滑化を強めると深い1点が散って残り、弱めると tentacle が出る
- **最終判定は赤(outer)/緑(inner)のオブジェクトカラー表示＋前外側3/4ビューの目視**にする。被覆域で緑が赤の前に出ていなければOK。上端(乳様突起)・下端(付着部)・外側縁から覗く緑は**元々覆われない自然な露出**で突き抜けではない
- 手法は「前面オフセットを中心軸へコサイン縮小（解析的な細り＝凹みなし）＋ 残帯だけ局所タック」が有効。per-vertex 一律 push より自然

## スナップショットから libraries.load した直後は付随データを掃除
- `bpy.data.libraries.load(snap)` でオブジェクトを append すると `Armature.00x` 等の付随オブジェクトも一緒に入り、ビューレイヤー外に居座る
- 直後に `isolate_objects` 等を呼ぶと「オブジェクトはビューレイヤーに無いため隠せません」エラーになる
- **append で元座標だけ取り出したら、付随 Armature/Mesh を即 `bpy.data.objects.remove(..., do_unlink=True)` で掃除**してから視覚処理に進む

## 左右非対称オブジェクトのミラーコピー定型
- 「左の<部位>を右にコピーして」と言われたとき、頂点数が左右で異なる場合は本体削除→ミラー複製
- **推奨はワールド座標ベイク方式**（origin位置に依存せず確実。詳細は memory `feedback-bmesh-mirror`）：
  ```python
  import bmesh
  new_me = src.data.copy()
  new_me.transform(src.matrix_world)        # ワールド空間に焼き込む
  bm = bmesh.new(); bm.from_mesh(new_me)
  for v in bm.verts: v.co.x = -v.co.x       # ワールドX=0で鏡像
  for f in bm.faces: f.normal_flip()        # 面法線反転
  bm.normal_update(); bm.to_mesh(new_me); bm.free(); new_me.update()
  ob = bpy.data.objects.new(dst_name, new_me)  # matrix_world は単位のまま
  for c in src.users_collection: c.objects.link(ob)  # material は data.copy で継承
  ```
- ミラー後 matcap（`shading.light='MATCAP'` + `studio_light='check_normal+y.exr'`）で左右の法線一致を必ず目視確認
- 左右で色が**一致**＝法線正常。色が違ったら片方の法線が逆 → bmesh で再度 `f.normal_flip()`
- **修復用途:** 片側が破損（ゴミ座標）した場合、健全な反対側からミラーして作り直す

## コレクション構造（v1.63.1で再編）
- 筋肉は `筋肉` 親 ＋ `筋肉_<部位>`（頭頸部/胴体/右上腕…左足/未分類の16個）に統一。**旧 `表層筋`/`深層筋` 親と `Rig_<部位>`/`深層筋_<部位>` 子は廃止し、各部位で表層+深層を統合**（表層/深層の区別なし）
- 他: `骨格`(骨)・`女性外皮`(皮膚)・`歯`・`靱帯・腱`・`_RenderSetup`・`_ガイドライン`
- リグは Mixamo命名の `Armature` 1本（旧 `Armature.001` は統合・削除済み）

## 重複パーツ整理ルール（同一筋が複数コレクションに散在）
- 「<コレクション>が正、他の重複を削除して」系の指示の定型（詳細は memory `feedback-duplicate-cleanup`）
- 正規化base名（`.001`/`_旧`/63字切り詰めハッシュ`_xxxxxxx`を除去）＋**頂点数+名前接頭辞**で対応付け
- 使い捨ての複製は **DECIMATE+ARMATURE モディファイア付き**で識別（ユーザーはRig再設定する）＝オブジェクト単位で判定（旧 `Rig_胴体` コレクションは廃止、現在は `筋肉_<部位>` に統合）。正版はモディファイアなし原本
- **対応する原本が無い唯一の筋は絶対保持**（首/舌骨/斜角筋/板状筋/大円筋/広頚筋等）
- **削除前に必ず幾何検証**：頂点数一致＋重心差。**重心差が異常大（>1m）はゴミ座標破損のサイン** → base＋評価後(armature)両方の重心を確認し、破損ならミラーで修復
- 各バッチ前に `save_snapshot`、削除後に残存重複ゼロを再検証

## 頂点グループ単位の筋分割
- 統合筋メッシュ（例:背中筋群=4筋）を `bmesh.verts.layers.deform` の dominant group 判定で個別オブジェクトへ分割（詳細は memory `feedback-vertex-group-split`）
- 分割後の頂点数合計＝元メッシュ（ロスゼロ）を検証。ミラー由来は頂点グループ名が反対側のまま→改名＋既存個別筋との名前衝突を事前チェック

## 認識合わせプロトコル（曖昧な方向語が出たら必ず実行）
- 「下面」「内側」「下側」「浮いている」など、座標系依存の方向語が指示にある場合、**実装前に必ずデバッグサーフェスで可視化してユーザー確認**
  1. 現状の対象面を別オブジェクトとしてグリッドメッシュで抽出、赤色マテリアル
  2. 理想面（Body 表面など）を別オブジェクトで抽出、緑色マテリアル
  3. `space.shading.color_type = 'MATERIAL'` でビューポートに色付き表示
  4. ユーザーに視点切替（LEFT / BACK / FRONT）でビジュアル確認してもらう
- 複数候補（A/B/C）の **Z範囲プロトタイプを並行作成**し、表示切替で選んでもらうのが最速
- 方向（+Y が腹か背中か）の判定は推測ではなく **必ず顔・乳房等の解剖ランドマークで実測**して確定する
- 「DIAG_*」のようなユーザー記述のガイド線は **ユーザー期待位置の参照**であり、Body 表面と一致するとは限らない

## Blender オブジェクト比較・切替ルール
- オブジェクトを置換・比較するときは **削除せずコレクションで管理** する
  - 新版 → `XXX_新版(説明)` コレクションに入れる
  - 旧版 → `XXX_旧版(比較用)` コレクションに入れて初期非表示にする
    - `collection.hide_viewport = False`（制限フラグはOFF）
    - `layer_collection.hide_viewport = True`（👁アイコンで制御）← これが正しい方法
    - ※ `collection.hide_viewport=True` にすると👁アイコンが効かなくなるので使わない
  - ユーザーはアウトライナーのコレクション横アイコンで表示/非表示を切替できる
- コレクション名は日本語で分かりやすくつける
- 旧版オブジェクトは名前末尾に `_旧` を付けて新版と名前衝突を避ける
- 比較が終わり不要になったら明示的に確認してから削除する

## Female化フレームとグループ間噛み合い（重要）
- `3DAnatomyFemale.blend` は `3DAnatomyman_Japanese_fbx/Man_All.blend` を**部位グループ別のオブジェクトスケール**で女性化したもの
- **Man_All原本は全オブジェクトが `scale=(0.01,0.01,0.01)`/`loc=(0,0,0)`**。配置は頂点座標(co)に焼き込まれ、全パーツが同一フレームを共有して完璧に噛み合う
- **Female化はオブジェクト変換のみ**でメッシュ頂点(co)は不変。よって現ファイル内でも `co×0.01` = Man_All世界座標を再構成できる（解剖学的整合の検証に使える）
- 部位グループごとに異なるスケール/pivotを掛けたため、**グループ境界（特に肩）で噛み合いが崩れる**。代表スケール（相対 X/Y/Z）:
  - 肩甲骨グループ 0.92/1.12/0.90（肩甲骨・大円筋）、回旋筋腱板 1.09均一、上腕(腕)グループ 1.07/1.09/0.94(遠方pivot)、胴体表層筋 0.98/1.03/0.99、骨盤/下肢 1.17/1.14/1.05、胸郭椎骨 0.84/1.02/0.93
- **グループ間噛み合い崩れの修正定型**: メッシュcoがMan_All共通フレームのままなので、**再インポート不要**。対象オブジェクトの `matrix_world` を基準骨（例: 肩甲骨）の `matrix_world` へ統一すれば、Man_Allの相対配置を完全再現できる（頂点・UV・テクスチャ完全保持）
  ```python
  M = bpy.data.objects["右肩甲骨(みぎけんこうこつ)"].matrix_world.copy()
  for n in ["右棘上筋(...)", ...]:
      bpy.data.objects[n].matrix_world = M.copy()
  ```

### 肩関節の腱付着部ギャップ → A-pose化で解決（v1.65.0）
- 原因判明: femaleizationで**腕グループだけT-poseへ回転**していた（胴体・肩甲骨・大胸筋・広背筋は中立フレーム=A-pose整合のまま）。そのため腕がT-poseに開いて肩の腱付着部がギャップしていた（T-poseで大胸筋11.5/広背筋10.6mm）
- 修正(v1.65.0): **腕全体（上腕・前腕・手の筋+骨 左右計144パーツ）のmatrix_worldを同側肩甲骨フレームへ統一**しA-pose化。Man_All準拠のA-pose配置を整合復元（coは不変）。肩ギャップが大幅解消（A-poseで大胸筋/広背筋/大円筋 0.7〜1.8mm）。モデルは**Man_All準拠のA-pose**（腕は鉛直から約10°）
- v1.58.0で回旋筋腱板4筋＋大円筋を先行して肩甲骨フレームへ統一済みだった分も、この全腕統一に包含され整合
- ※「腕をMan_All A-poseへ戻す/再T-pose化する」には同方式（腕パーツのmatrix_worldを肩甲骨 or 別フレームへ統一）で可能。腕パーツのcoはMan_All A-poseのまま保持されている

### 胸腰移行部T12-L1の望遠鏡状めり込み（v1.59.0・修正済み）
- 胸椎群0.84と腰椎群1.17を別pivotでスケールしたため、T12がL1にめり込んでいた（椎間Z重なり-79mm／正常は-25mm）。**過大化した腰椎が上へ乗り上げ**、仙骨↔L5は正常だった
- 修正: **過大な腰椎をZ28%圧縮**してL1をT12の下へ落とす（胸郭・頭・全長・皮膚は不動）
- **皮膚は欠陥骨格（telescope=縮んだ脊柱）に焼き付いている**。骨格を正すと生じる長さ差(54mm)は消えず、頭を上げれば頭が皮膚突き抜け／一様Z圧縮すれば頭が潰れる＝**どこかの皮膚に皺寄せ**される
- ただし**外側輪郭は固定端の筋（脊柱起立筋・広背筋・腰方形筋＝骨盤↔肋骨が固定）が支える**ため、**内部の骨だけ動かす修正（腰椎Z圧縮等）は皮膚への皺寄せゼロ**で済む

### 骨を動かしたら付着筋も追従（鉄則）
- 肋骨・椎骨を移動/圧縮したら、付着する筋も同じper-vertex変換で追従させる。置き去りにすると筋が元位置に残り突き抜ける（v1.59.0で肋間筋・肋骨挙筋を置き去りにし突抜発生→追従で解消）
  - 肋骨 → 内/外/最内肋間筋・肋下筋・胸横筋・肋骨挙筋(長/短)・上後鋸筋・前鋸筋・大胸筋
  - 椎骨(専属) → 回旋筋・横突間筋・棘間筋（その椎間に閉じた深層筋）
- **両端が固定の跨ぎ筋は据え置き**：脊柱起立筋・広背筋・腹筋・腰方形筋・多裂筋（骨盤↔肋骨など両端固定なので間の骨が動いても本体不変）
- 肋間筋など**左右一体オブジェクト**は world x の符号で片側頂点だけ処理（右=x<0／左=x>0）

### 累積編集の歪み除去（クリーン再構築）
- ライン編集の重ね掛け等で表面に波打ち/段差が残ったら、編集前スナップショットの清浄形状を `libraries.load` で読み（topology一致＝index対応）、現在との正味シフトを **z刻みmedian→平滑化→単一パス適用**（`co=(clean_x, clean_y+f(clean_z), clean_z)`）。pure Y変形時に有効、修正効果を保ちつつ歪みが消える

## 解剖モデルの色付け（v1.67.0で確立）
- **色は頂点カラー駆動の単一マテリアルに統一する**と FBX/glTF/OBJ 全形式へ伝搬する（391筋ともUV無し＝画像テクスチャ不可・プロシージャルは.blend限定のため）
  - 各メッシュに `FLOAT_COLOR`/`POINT` のカラーアトリビュート（例 `Col`）を焼き、共有マテリアル `Anatomy_VertexColor`（`ShaderNodeVertexColor`→Principled Base Color）を全対象に割当。色情報は全て頂点カラーが担うのでマテリアルは1個でよい
  - 焼込みは `attr.data.foreach_set('color', rgba_flat)` で一括（数万〜十数万頂点でも高速）。**色はlinear**（`srgb_to_linear`）で書く
  - SOLIDビューで見るには `space.shading.color_type='VERTEX'`
- **色伝搬の実証済み挙動**：glTF=`COLOR_0`出力（baseColorFactor=白×頂点カラー）／FBX=頂点カラーレイヤー保持（`colors_type='SRGB'`、再import 15/15確認）／OBJ=`export_colors=True`でv行末尾にRGB（拡張形式・ビューア依存）
  - **OBJ等の頂点カラー非対応ビューア用フォールバック**：共有マテリアルの Principled Base Color の `default_value` に代表色（筋なら赤褐色）を入れると MTL の `Kd` がその色になり、非対応環境でも赤く見える
- **解剖学的リアル色の基準値**（PoseManiacs実測 median）：筋肉 sRGB(0.75,0.45,0.33)≈HSV(0.048,0.55,0.77) サーモン/テラコッタ。彩度を上げすぎ・暗くしすぎると肝色になり不自然。腱靱帯=白クリーム sRGB(0.85,0.82,0.75)、骨=アイボリー sRGB(0.88,0.85,0.78)
- **左右対称筋は同色**にする：正規化base名（先頭の右/左・末尾`.001`・よみがな括弧を除去）の md5 ハッシュ→12色パレットのindexで決定論割当
- **筋内部の腱（付着部）の白み**は頂点カラーで近似：各筋メッシュをPCAして主軸方向の正規化位置の両端を白クリームにブレンド（中央=筋色）。縦走の腱は出るが、腹直筋の腱画など横方向の腱は主軸が縦のため不可（必要なら該当筋だけ手動で腱面を別マテリアル分離）

## プレビュー画像のレンダリング
> **★推奨＝ヘッドレス版（2026-06-14実証, MCP/GUI不要）**: `blender -b <file> -P scripts/listing/render_previews.py -- <female|male>`。
> `bpy.ops.render.opengl`(GUI必須)ではなく **Workbenchをレンダーエンジンにして `render.render()`** にすることで `-b` でも撮れる。可視化は `hide_render`＋コレクション単位PRESETで出し分け、背景は `film_transparent=True` で透過にして後段(`normalize_and_thumbs.py`)で184合成（モデル間color management差を回避）、view_transformは両モデルStandardでトーン統一。**MCPの1ファイル制約から解放され、男女を1コマンドずつで撮れる**。詳細は `出品手順_販売サイト.md` §2。
> 以下は旧来のGUI/MCP内ビューポート撮影法（参考・単発の確認用）。

### （旧）OpenGLビューポートレンダー（GUI/MCP内）
- プレビューは **Workbenchエンジン＋`bpy.ops.render.opengl(write_still=True)`**（ビューポートのSOLID/`color_type='VERTEX'`シェーディングをそのまま出力）。カメラは `_RenderSetup` の `Camera`(front34=ヨー35°)/`Camera_Back`、解像度1000x1400
- **最重要：OpenGLレンダーは `hide_render` ではなく `hide_get`（目玉アイコン）基準**。ビューポートで見えているものがそのまま写る。撮影前に必ず次の2点を確認（v1.67.0 front34で両方やらかして再レンダーになった）：
  1. ガイドライン/`DIAG_*`/`CURRENT_*ライン`等の **CURVEを全て `hide_set(True)`**（`_ガイドライン` layer_collection も `hide_viewport=True` で二重に隠す）。表示のまま撮ると腹部・肩に赤/黄の線が写り込む
  2. **`Breast_Base`（乳房）を `hide_set(False)` で表示**。非表示のまま撮ると女性なのに大胸筋だけで乳房が消える
- 撮影は `temp_override(window, area, region)` で VIEW_3D コンテキストを渡し、`overlay.show_overlays=False`／`region_3d.view_perspective='CAMERA'` にしてから実行
- ※この表示調整はレンダー用の一時変更。**`.blend` には保存しない**（`hide_render` 等はFBX/glTFエクスポートの除外設定に影響しうるので元の状態を尊重する）

### 男女統一アングル（商品画像の必須ルール）
男性(Man_All)と女性(3DAnatomyFemale)でプレビューのアングルがバラバラだと商品として不揃い。**両モデルで同一カメラ**に統一する（`region_3d` 直接設定でも `_RenderSetup` カメラでも、結果のアングルを一致させる）：
- **回転(QUAT固定)**: `front`=(0.707,0.707,0,0)／`front34`=`Quaternion((0,0,1),radians(-35)) @ front`（右前方・**モデルの右が手前/顔が画面左**で男女統一）／`back`=(0,0,0.707,0.707)。すべて `view_perspective='ORTHO'`
- **距離(充填・遠すぎ厳禁)**: `view_distance = z_span × 1.05`（`z_span`=表示メッシュbboxのZ範囲、median中心・clip0.9で外れ値除外）。全身がフレーム縦いっぱい＋僅かな余白。pad<0.7は頭足が切れ、pad>1.2は余白過多
- **closeup(臓器/胴体/前腕)**: 対象中心へ `view_location`、`view_distance` 0.30〜0.62、解像度1100×1300
- **構成順(男女共通+固有)**: `01_front`(筋)→`02_front34`(筋)→`03_back`(筋)→`04_skeleton_front`(骨格)→固有（女性:`05_torso_closeup`/`06_forearm_tendon`、男性:`05_organs`/`06_vessels_nerves`/`07_skin`/`08_torso_closeup`）。**1枚目=正面=サムネ/メイン画像**
- 背景=(0.72,0.72,0.72)、studio light、`color_type='VERTEX'`、解像度 全身1000×1400
- **⚠️color management差に注意**: `scene.view_settings.view_transform` がモデル間で違うと、同じ `background_color=(0.72)` でも背景の明度がズレる（実測: Female=Filmic→193／Standard→220／Raw→184。Man_All=184）。**撮影後にPILで背景グレー（`|R-G|<7 & |G-B|<7 & min(RGB)>178`）を一律 `(184,184,184)` に正規化**すると男女のサムネ並び（thumb_set）の境界矩形が消える。色味は Female=Filmic と Man=現状で近いので view_transform は無理に揃えず、背景だけ後処理で統一するのが楽

## 出品（Gumroad/BOOTH）更新の自動操作手順（v1.67.0で確立・acc1/acc2共通）
新バージョンを出した後、両マーケットの出品をブラウザ自動操作で更新する手順。**skill `browser-control` を使う**。

### ★まず読む: 完全ランブックと再利用スクリプト（2026-06-14整備）
- **手順書**: `出品手順_販売サイト.md`（事前準備→ローカル素材→Gumroad→BOOTH→検証チェックリスト。商品ID/配布物は `scripts/listing/config.json` が一次情報）
- **スクリプト**（Brave を `-Profile "PC"` で起動後に実行）:
  - `blender -b <master> -P scripts/listing/export_dist.py -- <female|male> <ver>` — **配布用4形式(blend/fbx/glb/obj)書き出し**＋出力を読み直して自動検証
  - `python scripts/listing/make_zips.py <female|male> <ver>` — 形式別zip4本
  - `python scripts/listing/normalize_and_thumbs.py` — 背景184正規化＋サムネ3枚再生成
  - `node scripts/listing/gumroad.js <covers|desc|thumb|files|verify> <female|male|set>`
  - `node scripts/listing/booth.js <all|title|images|files|save|verify> <product>`
  - `node scripts/listing/audit_dist.js [local|booth|gumroad]` — **4形式が揃っているかの監査**（欠けたら exit 1）
- **★「配布物に4形式入ってる?」はこの監査で答える**（記憶や推測で答えない）。書き出しの罠（非表示オブジェクトの欠落・`compress=True`）と販路別のファイル差し替え作法（BOOTHは旧削除が先／Gumroadは1本ずつアップして都度保存・setはバンドル）は skill `anatomy-listing` §0.5〜0.6 と `出品手順_販売サイト.md` §2.5〜2.6 が正。
- **★Gumroadの罠（再発防止）**: 公開メイン画像は「Description先頭画像」だが、**旧版の「Product covers」アセットが残っていると、そちらがメインを上書きする**（Male v1.0.0の残骸でメインがグレーだった事例）。`gumroad.js covers <product>` で全削除（狭VPで aria-label「Remove cover」が出る）→説明欄先頭が昇格。Female/Setは covers 0枚。
- **★BOOTHファイルは自動アップ可**: D&Dゾーンを**クリックで一時input生成→filechooser発火**→生CDP `DOM.setFileInputFiles`（50MB制限回避）。「手動必須」は誤り。
- **★検証**: 「完全完了」は**公開ページのメイン画像を実画面で目視**するまで報告しない（説明欄だけ見て誤判定した事故あり）。

### 商品（URL/ID）
| 販路 | 商品 | 編集URL | 公開URL |
|---|---|---|---|
| Gumroad | 女性 | `gumroad.com/products/zdlbhd/edit` | `liberation58.gumroad.com/l/zdlbhd` |
| Gumroad | 男性 / セット | `.../products/hgbvor/edit` / `.../dbwncg/edit` | `/l/hgbvor` / `/l/dbwncg` |
| BOOTH | 女性 | `manage.booth.pm/items/8481858/edit` | `kabe-tech.booth.pm/items/8481858` |
| BOOTH | 男性 / セット | `.../items/8496247/edit` / `.../8496725/edit` | `/items/8496247` / `/8496725` |

素材：`配布パッケージ_v{X}/`（previews/・models/・index/）と `配布zip_v{X}/`（形式別zip: blend/fbx/glb/obj、各<1.2GB）。文言は `商品説明文_v{X}.md`（日英）。

- **説明文を貼る際は編集用の見出し行を必ず除外する**。`商品説明文_v{X}.md` の「商品紹介文（コピペ用）」等の見出しをそのまま貼り付けない（v1.67.0でBOOTH紹介文の1行目に「商品紹介文（コピペ用）」が混入していた）。貼付後は先頭行が本文（例「女性解剖モデル【カラー版】｜…」）で始まることを確認する

### Brave起動（必ずPCプロファイルで）
- **出品者ログイン（liberation58 / kabe-tech）があるのは `PC`（=`Profile 3`）プロファイル**。必ず指定して起動：
  ```powershell
  pwsh -File C:\Users\abesh\tools\browser-auto\brave-debug.ps1 -Profile "PC"
  ```
  （`-ListProfiles` で一覧。表示名・ディレクトリ名どちらでも可。未指定だと last_used が別プロファイルだとログイン無しになる）
- 既にポートが開いていると `ALREADY_OPEN` で何もしない。**プロファイルを切り替えたい時は一度Braveを閉じてから** `-Profile` 付きで起動
- 接続は `connect.js` の `withBrowser`（connectOverCDP）

### 大容量ファイル（>50MB）のアップロード ★最重要
- Playwright の `setInputFiles` は connectOverCDP だと **50MB制限**で失敗（"Cannot transfer files larger than 50Mb..."）
- **生CDP `DOM.setFileInputFiles`（ローカルパス指定）を使えば300〜450MBでもOK**（日本語パス可・複数同時可・co-located不要）：
  ```js
  const client = await context.newCDPSession(page);
  await client.send('DOM.enable');
  const doc = await client.send('DOM.getDocument', { depth: -1 });
  const q = await client.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
  await client.send('DOM.setFileInputFiles', { files: [absPath1, absPath2, ...], nodeId: q.nodeIds[idx] });
  ```
- ※launchPersistentContextは実プロファイルだと起動不安定、プロファイルをコピーするとABE（アプリ連動暗号化）でCookie復号できずログイン喪失。**「通常Brave＋デバッグポート＋connectOverCDP＋生CDP」が唯一実用的**

### Gumroad の操作詳細
- タブ：Product / Content / Receipt / Share。タイトル＝最初の text input。説明＝contenteditable（`Ctrl+Home`で先頭にカラー版バナー挿入）
- **カバー画像＝Description本文(tiptap)の先頭に置いた画像**。新Gumroadエディタでは本文先頭の画像群がそのまま商品カバーとして公開ページに表示される（v1.67.0で判明）。`input[0]`(accept画像・multiple)は**カバー専用ではなく本文画像挿入**用で、`setInputFiles`するとエディタのカーソル位置に挿入される（`Ctrl+Home`で本文先頭へ寄せてから挿入）。`input[1]`=audio, `input[2]`=正方形サムネ
  - ※「Cover」セクションの小サムネストリップ(w30〜120の右上×で削除)は**ウィンドウ幅が狭い時だけ**出る。Previewパネルが出る広い幅では消え、本文カルーセル(`.tiptap img`)管理になる
- **サムネイル**：input[2] は**正方形必須**（非正方形は "Image must be square"）。正方形画像を別途作って設定
- **カバー差し替え/削除（広レイアウトの確実手順）**：本文先頭画像なので `.tiptap img`（または `.ProseMirror img`）を**クリックして選択→`Delete`キーで削除**。差し替えは「対象画像を削除→`Ctrl+Home`で先頭にカーソル→`input[0]`に新画像を`setInputFiles`で先頭挿入」が確実（v1.67.0 front34差替で実証）。順序は `.tiptap img` の並び順＝公開カバー順。ストリップ小サムネ右上×やカルーセルhoverの「Remove」は広レイアウトでは出ないことがある
  - ⚠️ カバーが残った状態で `input[0]` にアップすると**本文に画像が増えるだけで既存カバーは消えない**（削除と追加は別操作）。未保存なら**リロードで本文の誤挿入を破棄**できる
- **ダウンロードファイル**：Contentタブ。`input[0]`(accept=""・multiple) に setFileInputFiles。アップすると新フォルダができるので命名。**旧フォルダ/ファイルの削除は左の「⋮」メニュー（Move up/down/**Delete**）、各ファイルも展開して「⋮」→Delete**
- 保存：右上「Save changes」。保存後の「購入者へ通知（notify customers）」は任意（Skip可）

### BOOTH の操作詳細
- タイトル/価格＝React制御input（**ネイティブvalue setter＋`input`/`change`イベント**で設定）。商品名は値に「女性解剖」を含むinput。紹介文＝textarea（recaptcha以外の方）
- **商品画像**：「画像を追加」クリックで隠しinput生成→setInputFiles（画像は小さいのでPlaywrightでも可）。**1番目がメイン画像**。削除はサムネにホバー→`<i class="icon-cancel">`（親が`<button onclick>`）。**`window.confirm`が出るので `page.on('dialog', d=>d.accept())` 必須**
- **作品ファイル**：「変更する」→モーダル「ファイルの追加・管理」。**ドロップゾーン文言をクリックすると.zip対応の隠しinputが生成される**→生CDPで setFileInputFiles。1ファイル1.2GB上限・総容量10GB（使用量バー注意）
- **作品ファイル削除の罠**：行は「ファイル名リンク」と「削除」が**別カラム（DOM上は親子/兄弟でない）＝行インデックス対応**。Y座標突合は誤爆しやすい。**安全策＝先に旧を全削除→新を再アップロード**（曖昧さ回避）。削除も confirmダイアログ accept 必須。「チェックをつけたファイルがユーザーに提供」＝新ファイルのチェックON確認
- 保存：「公開で保存する」（R-18維持）

### ログイン・破損防止の鉄則
- **Braveを強制終了するとログインセッションが飛ぶことがある**。出品作業中は安易に kill/再起動しない。プロファイル切替が要るなら最初から `-Profile "PC"` で起動しておく
- 作業後はユーザーに「Braveを普通に再起動すればデバッグポートは閉じる」と伝える。プロファイルをコピーした場合（Cookie含む）は作業後に削除する
