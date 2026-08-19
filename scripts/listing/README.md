# scripts/listing — 出品自動化ツール

Gumroad / BOOTH のカラー版出品を**セッションをまたいで安定再現**するためのツール群。
完全な手順・チェックリストは **`../../出品手順_販売サイト.md`**（こちらを先に読む）。

## 構成
| ファイル | 役割 |
|---|---|
| `config.json` | **一次情報**。商品ID・配布物パス・プレビュー順・zip接頭辞。新バージョンで更新する箇所はここだけ |
| `export_dist.py` | **配布用4形式(blend/fbx/glb/obj)をヘッドレス書き出し**＋出力を読み直して自動検証 |
| `make_zips.py` | 形式別zip4本を組み立て（README/LICENSE/CREDITS/index同梱・previewsは入れない） |
| `audit_dist.js` | **読み取り専用の監査**。local/BOOTH/Gumroadに4形式が揃っているか。欠けたら exit 1 |
| `render_previews.py` | **ヘッドレス**でプレビュー撮影（`blender -b`・MCP/GUI不要）。可視化は PRESETS で出し分け |
| `_introspect.py` | .blendのコレクション構成/可視化状態をダンプ（PRESET調整時の確認用） |
| `normalize_and_thumbs.py` | 透過プレビューを184合成＋正方形サムネ3枚を再生成 |
| `gumroad.js` | `covers`/`desc`/`thumb`/`verify` <female\|male\|set> |
| `booth.js` | `all`/`title`/`images`/`files`/`save`/`verify` <product> |

## 使い方
```powershell
# 0) Brave を出品者プロファイルで起動（必須）
pwsh -File C:\Users\abesh\tools\browser-auto\brave-debug.ps1 -Profile "PC"
```
```bash
# 0.5) モデルを変更したときだけ: 4形式を書き出して zip 化 → config.json の版を更新
BLENDER="/c/Program Files/Blender Foundation/Blender 5.0/blender.exe"
"$BLENDER" -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/listing/export_dist.py -- male v1.2.0
python scripts/listing/make_zips.py male v1.2.0

# 1) プレビュー撮影（ヘッドレス＝ファイルを開かない・MCP不要）＋ 背景184合成＋サムネ
BLENDER="/c/Program Files/Blender Foundation/Blender 5.0/blender.exe"
"$BLENDER" -b 3DAnatomyFemale.blend                 -P scripts/listing/render_previews.py -- female
"$BLENDER" -b 3DAnatomyman_Japanese_fbx/Man_All.blend -P scripts/listing/render_previews.py -- male
python scripts/listing/normalize_and_thumbs.py

# 2) Gumroad（例: 男性）
cd scripts/listing
node gumroad.js covers male   # ★旧Product coversを全削除（メインがグレーになる元凶）
node gumroad.js thumb  male
node gumroad.js verify male   # 公開ページ確認

# 3) BOOTH（例: セット）
node booth.js all set
node booth.js verify set

# 4) 監査（「4形式入ってる?」はこれで答える。推測しない）
node audit_dist.js          # local + BOOTH + Gumroad。欠けたら exit 1
node audit_dist.js local    # ブラウザ不要
```

## 必ず覚える3つの罠
1. **Gumroad「Product covers」**: 説明欄とは別アセット。残っていると公開メインを上書きする（旧launchの残骸）。`gumroad.js covers` で全削除→説明欄先頭が昇格。Female/Setは0枚。
2. **BOOTHのD&Dアップロード**: ドロップゾーンを**クリックすると一時inputが生成→filechooser発火**。生CDP `DOM.setFileInputFiles` でパス直指定すれば50MB制限なくzipを上げられる（手動不要）。
3. **検証**: 「完了」は**公開ページのメイン画像を目視**してから報告（説明欄だけ見て誤判定した事故あり）。容量はBOOTH 10GB上限・1ファイル1.2GB。

依存: `playwright-core`（`C:\Users\abesh\tools\browser-auto` 経由）、`Pillow`/`numpy`（python）。
