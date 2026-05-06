# 乳房形状の解剖学（3Dモデリング用）

## 基本的な形状特性

### 全体形状
- **涙滴型（Teardrop / Pear shape）** が自然な乳房の基本形
- 下極が上極より丸みが強く、ボリュームが多い
- 左右対称の楕円体・球形ではNOT OK

### 向き
- 肋骨のカーブにより、乳房は自然に外側へ約45度向く
- 乳頭は胸の中央より**外側（lateral）**に位置する

---

## 上極・下極の違い

| 部位 | 特徴 |
|------|------|
| **上極（Upper pole）** | 比較的平坦・胸壁に沿った形状。正面から見ると斜めのスロープ |
| **下極（Lower pole）** | 丸みが強く、重力でやや垂れ下がる（ptosis）。半円形（扁球体） |
| **乳頭位置** | 最大突出点の高さ（ニップルZ位置）。乳房垂直中央より**わずかに下** |

---

## 断面形状の特徴

### 矢状断面（サイドビュー）
```
上部（鎖骨側）
  \  ← 平坦・胸壁に沿う（上極）
   \
    ●  ← ニップル（最大突出点）
   /
  /   ← 丸みのある下極（ptosis）
 |    ← 乳房下溝（Inframammary Fold）でほぼ90度の折れ目
```

### 正面断面（フロントビュー）
```
     /~~~\      ← 上部はなだらか
    |     |
   /       \    ← 乳頭付近が最も幅広
   \       /
    \___/ ← 下部は丸くすぼまる（ただし上より幅広）
```

---

## 乳房下溝（Inframammary Fold）
- 乳房の下端で胸壁と接する折れ目
- 角度は約90度（明確な境界）
- 第4〜5肋骨レベル（このモデルではZ≈1.29-1.31付近）
- 下からの見た目：乳房が胸壁に向かって急激に戻る

---

## Blenderモデリング向け寸法目安（1.8mの体型）

| 項目 | 目安値 |
|------|-------|
| 乳頭X位置（内側端から） | X ≈ 0.068〜0.080 m |
| 乳頭Z位置 | Z ≈ 1.330〜1.345 m |
| 乳頭Y（胸壁からの突出） | B cup: 5〜6cm、C cup: 6〜8cm |
| 乳房幅（片側） | 9〜12 cm |
| 乳房高さ | 10〜12 cm |
| 内側端（ステルナム側） | X ≈ 0.018〜0.025 m |
| 外側端（腋窩側） | X ≈ 0.105〜0.120 m |

---

## 3Dモデリング実装のポイント

### 上極の作り方
- 乳頭より上（Z > nipple_Z）は前方突出を**40〜70%削減**
- 大胸筋鎖骨部の表面に沿うようなスロープ

### 下極の作り方
- 乳頭より下（Z < nipple_Z）は突出を維持または微増
- 重力下垂（ptosis）のため最下端はわずかに後退して乳房下溝へ

### 内側縁（Medial edge）
- 胸骨に近い内側は比較的まっすぐ・垂直
- 突出は外側より少ない

### 外側縁（Lateral/Axillary tail）
- 腋窩方向になだらかに延びる
- 前鋸筋と自然につながる

### 避けるべき形状
- 完全な球体・楕円体（floating ball appearance）
- 上下対称な形状
- 胸壁から浮いた（disconnected）外観
- 内側端が胸骨中央線に接触するほど近い配置

---

## 参照リンク
- [Wikipedia: Breast anatomy](https://en.wikipedia.org/wiki/Breast)
- [Plastic Surgery Key: Measurement System and Ideal Breast Shape](https://plasticsurgerykey.com/a-measurement-system-and-ideal-breast-shape/)
- [Proko: How to Draw Breasts](https://www.proko.com/course-lesson/how-to-draw-breasts-form-and-motion/)
- [Springer: 3D Statistical Shape Model of Female Breast](https://link.springer.com/article/10.1007/s00371-022-02431-3)
