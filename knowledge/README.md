# 筋肉解剖学 知識ベース

Claudeが解剖学的正確性を判断するための参照資料。

## ファイル構成

| ファイル | 内容 |
|---|---|
| [muscles_torso.md](muscles_torso.md) | 体幹（胸・腹・背中浅層） |
| [muscles_arms.md](muscles_arms.md) | 肩・上腕・前腕 |
| [muscles_legs.md](muscles_legs.md) | 大腿・下腿・臀部 |
| [muscles_back_deep.md](muscles_back_deep.md) | 背中深層（脊柱起立筋群） |
| [comparison_checklist.md](comparison_checklist.md) | モデル検証チェックリスト |
| [pennation_angles.md](pennation_angles.md) | 羽状角・繊維走行まとめ |
| [visual_target_and_criteria.md](visual_target_and_criteria.md) | ビジュアルターゲットと判定基準（エコルシェ方針） |
| [male_to_female_differences.md](male_to_female_differences.md) | **男性→女性変換ガイド**（3DAnatomyMan使用時の差異と対処） |
| [best_practices_male_to_female.md](best_practices_male_to_female.md) | **ベストプラクティス**（実測スケール係数・ワークフロー・Distortion設定） |

## 部位別サブフォルダ（修正作業用）

| フォルダ | 内容 |
|---|---|
| [deltoid/](deltoid/README.md) | 三角筋の接続・境界・修正チェックリスト |

## 参照画像
- `Sample/` フォルダ内のリファレンス画像と照合すること

## 使用方法
1. 部位ごとのファイルで「起始・停止・繊維方向」を確認
2. `comparison_checklist.md` に従ってモデルと比較
3. リファレンス画像と同一アングルのスクリーンショットで視覚的に確認

## 判定基準
- **OK**: 繊維走行がリファレンス画像と±15°以内
- **要修正**: それ以上の乖離、または形状・ボリュームが解剖学的に不自然
