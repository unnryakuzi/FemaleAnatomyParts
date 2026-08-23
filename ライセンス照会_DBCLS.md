# ライセンス照会：DBCLS（BodyParts3D）

**状態: 送信済み（2026-08-23 11:42 JST）・回答待ち**

| | |
|---|---|
| 宛先 | `bodyparts@dbcls.rois.ac.jp` （BodyParts3D 専用窓口） |
| 件名 | `BodyParts3D のライセンス適用範囲についてのご確認` |
| 本文 | `ライセンス照会_DBCLS_本文.txt`（そのまま貼り付け可・見出し行なし） |
| 代替窓口 | NBDC問い合わせフォーム https://form2.jst.go.jp/s/contact_nbdc ／ Tel 03-5214-8491 / Fax 03-5214-8470 |
| 送信日 | **2026-08-23 11:42 JST**（送信確認済み: threadId `1a02c71f9ce8185a` / messageId `1a02c7f8e3ce8e7e` / label SENT） |
| 回答日 | ― |

宛先アドレスの根拠: https://dbarchive.biosciencedbc.jp/jp/bodyparts3d/desc.html の
「E-mail」欄は画像で掲載されている（`/images/dbarchive_images/mail_address/bodyparts3d_address.png`）。
画像を取得して6倍に拡大し1文字ずつ確認した（`refs/BodyParts3D_v4.0/bp3d_address_big.png`）。

## 送信手順（Gmail下書きを作成済み）

**Gmail に下書きを作成済み。開いて送信ボタンを押すだけ。**

- 下書きURL: https://mail.google.com/mail/u/0/#drafts?compose=1a02c71f9ce8185a
- draftId `r-7415676627553636565`（2026-08-23 再作成）
- 宛先・件名・本文すべて記入済み

### 注意点（実測で判明）
- **`mailto:` は使えない**。この環境には既定のメールソフトが登録されておらず、
  アプリ選択ダイアログが出るだけ。`scripts/provenance/open_inquiry_mail.ps1` は
  クリップボードへのコピー用途としてのみ残してある
- **Gmail API の `body`（プレーンテキスト）で下書きを作るとURLが
  `https://www.google.com/url?q=...&source=gmail&ust=...` に書き換えられ、
  本文の見た目に露出する**。`htmlBody` で
  `<div style="white-space:pre-wrap">` に入れて渡すと、表示テキストは素のURLのまま、
  リダイレクトは href 側だけになる（Gmail送信の通常挙動）。本下書きは後者で作成済み

---

## 照会の目的

BodyParts3D を素材とした派生3Dモデルを有償配布している。
**購入者による転売・再配布を止められる形にしたい**が、そのためには
継承（ShareAlike）条件が付かないことを確定させる必要がある。
現状はライセンス表記が3箇所で食い違っており、確定できない。

## 確認済みの事実（照会の前提）

| 場所 | 表記 | 備考 |
|---|---|---|
| https://dbarchive.biosciencedbc.jp/jp/bodyparts3d/lic.html | **表示 4.0 国際**（継承なし） | 最終更新 2025/02/27 |
| 同 更新履歴 https://dbarchive.biosciencedbc.jp/en/bodyparts3d/update.html | `2025/02/27 "License" is updated.` | データ本体は 2013/06/19 以降更新なし |
| 配布ZIP内の全OBJ 2234ファイルのヘッダ | Attribution-Share Alike 2.1 Japan | 参照先URLは上記lic.htmlを指す |
| https://lifesciencedb.jp/bp3d/info/license/index.html | 表示-継承2.1 日本 | Anatomography側。©2010 表記のまま |
| NBDC標準利用許諾 https://dbarchive.biosciencedbc.jp/contents/deposit/stdlicense.html | **表示-継承 4.0 国際** | ★BodyParts3Dはこれより緩い設定＝個別判断と読める |

★の点が重要。一括で新版へ移行しただけなら着地点は「表示-継承 4.0」のはずで、
BodyParts3D が「表示 4.0」になっているのは意図的に継承を外した設定と考えられる。
この根拠を本文の「背景」末尾に入れてある。

## 当方の出自監査の結果（照会には書かないが、判断の前提）

- 製品メッシュ931個が always3d 配布FBXと頂点数・面数まで完全一致（always3dはジオメトリを足していない）
- 骨は BP3D v4.0 と 0.08〜0.10mm で一致
- ただし製品が載っているのは**アーカイブが配布していない高解像度版**
  → 質問3がこれを確認するもの。**本件の可否はこの回答で決まる**
- 詳細: `refs/provenance_audit_summary.md`

---

## 回答記録

（受領後にここへ全文を貼る）

---

## 回答が来ない場合の対応（2026-08-23 策定）

**大前提: 無回答は許諾ではない。** 沈黙を承諾とみなして切り替えてはいけない。

### 段階1 — 待つ（〜2週間 / 目安 2026-09-06 まで）
公的機関なので即答は期待しない。この間はライセンス表記を一切変更しない。

### 段階2 — 別窓口で1回だけ催促（2週間経過後）
同じ内容を、送信済みメールへの follow-up として送るか、別経路を使う。

| 経路 | 宛先 |
|---|---|
| メール（同スレッドに追記） | `bodyparts@dbcls.rois.ac.jp` |
| NBDC問い合わせフォーム | https://form2.jst.go.jp/s/contact_nbdc |
| 電話 | 03-5214-8491 |
| FAX | 03-5214-8470 |

催促は1回まで。返信先が機能していない可能性もあるので、**メールで無反応ならフォーム**を使う。

### 段階3 — 補助的な情報収集（並行可）
always3d に「高解像度版をどこから入手したか」を尋ねる。
**権利は得られないが事実は分かる**（`ライセンス照会_always3d.md`）。

### 段階4 — 回答が得られないまま判断する場合

無回答のまま独自ライセンスへ切り替えるのは**推奨しない**（CCは一度与えた許諾を
撤回できず、頒布済みの分を回収できない＝リスクが一方向）。取り得る選択肢:

| # | 方針 | 品質への影響 | 法的な確実性 |
|---|---|---|---|
| A | **v4.0 `_99` から作り直す** | 総頂点 16,195,795 → **約 2,003,978（8.1分の1）** | ◎ 争いの余地なし |
| B | 現状維持（CC BY-SA のまま） | なし | ◎ ただし目的未達 |
| C | BY 4.0 を根拠に切り替える | なし | △ 高解像度版の扱いが未確認のまま |

**A は「品質低下」と切り捨てるべきではない。** 2.0M頂点は
ゲーム/リアルタイム用途ではむしろ扱いやすく、
「独自ライセンスの軽量版」と「CC BY-SA の高精細版」を別商品として併売する構成も取れる。
現行16.2M頂点は多くの用途で重すぎるため、作り直しが商品力の低下に直結するとは限らない。

**C を選ぶ場合**は、少なくとも以下を証跡として残すこと:
`refs/BodyParts3D_v4.0/PROVENANCE.txt`（取得時のライセンス表記・公式更新履歴）、
本ファイルの照会記録（送信済みで回答が得られなかった事実）、
`refs/provenance_audit_summary.md`（always3d の寄与がゼロであること）。
