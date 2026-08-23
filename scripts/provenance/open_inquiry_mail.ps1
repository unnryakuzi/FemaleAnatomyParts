# DBCLS への照会メールを「送信ボタンの手前」まで用意する。
#   1) 本文をクリップボードへコピー
#   2) 宛先・件名を埋めたメール作成画面を既定のメールソフトで開く
# 本文は mailto に載せない（長文＋日本語でURLエンコード長が上限を超えるため）。

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$body = Join-Path $root 'ライセンス照会_DBCLS_本文.txt'

if (-not (Test-Path $body)) { throw "本文が見つかりません: $body" }

$text = Get-Content -Path $body -Raw -Encoding UTF8
Set-Clipboard -Value $text
Write-Host "本文をクリップボードにコピーしました（$($text.Length) 文字）"

$to      = 'bodyparts@dbcls.rois.ac.jp'
$subject = [uri]::EscapeDataString('BodyParts3D のライセンス適用範囲についてのご確認')
Start-Process "mailto:$to`?subject=$subject"

Write-Host ""
Write-Host "メール作成画面を開きました。"
Write-Host "  宛先 : $to"
Write-Host "  件名 : BodyParts3D のライセンス適用範囲についてのご確認"
Write-Host "  本文 : 本文欄で Ctrl+V を押して貼り付けてください"
Write-Host ""
Write-Host "貼り付け後、先頭行が「ライフサイエンス統合データベースセンター」で"
Write-Host "始まっていることを確認してから送信してください。"
