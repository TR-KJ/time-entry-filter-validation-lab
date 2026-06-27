# ATR Filter Phase 1 検証結果メモ

## 検証テーマ

28ロジック統合EAにおけるATRフィルターの妥当性確認。

Event Filter Phase 2で最有力候補となった以下を前提に、ATR条件を比較した。

```text
Event Filter：
Candidate C Strategy別ハイブリッド
```

---

## 対象Repository

```text
https://github.com/TR-KJ/time-entry-filter-validation-lab.git
```

参考元Repository：

```text
https://github.com/TR-KJ/time-entry-portfolio-lab.git
```

---

## 使用コード

```text
src/filter_validation/atr_filter_validation_v1_1.py
```

---

## 検証対象

Event Filter V2のTrade Logを元に、ATR条件ごとにEntry許可 / ATR Rejectを判定した。

入力ファイル：

```text
/content/EventFilter_V2_TradeLogs.csv
```

出力ファイル：

```text
/content/ATRFilter_Comparison_Summary_v1_1.csv
/content/ATRFilter_Strategy_Summary_v1_1.csv
/content/ATRFilter_Pair_Summary_v1_1.csv
/content/ATRFilter_Allowed_Trades_v1_1.csv
/content/ATRFilter_Rejects_v1_1.csv
```

---

## 比較条件

```text
ATR_OFF
ATR_P60_LB500
ATR_P65_LB500
ATR_P70_LB500_CURRENT
ATR_P75_LB500
ATR_P70_LB250
ATR_P70_LB750
```

現行EAに近い条件：

```text
ATR_P70_LB500_CURRENT
```

---

## ATR判定仕様

```text
ATR Timeframe：H1
ATR Period：14
ATR Use Closed Bar：true
Lookback：250 / 500 / 750
Percentile：60 / 65 / 70 / 75
```

判定：

```text
Current ATR >= Percentile Threshold → Entry許可
Current ATR < Percentile Threshold → ATR Reject
```

---

## 全体結果：Candidate C Event前提

| ATR Condition | Trades | ATR Rejects | Win Rate | PF | Total Pips | Max DD | RoMD | Avg Pips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ATR OFF | 15,425 | 0 | 54.55% | 1.370 | 87,937.4 | 2,109.4 | 41.69 | 5.70 |
| ATR P60 / LB500 | 5,391 | 10,034 | 55.56% | 1.445 | 38,682.8 | 1,471.1 | 26.30 | 7.18 |
| ATR P65 / LB500 | 4,682 | 10,743 | 55.62% | 1.444 | 33,855.2 | 1,446.3 | 23.41 | 7.23 |
| ATR P70 / LB250 | 4,036 | 11,389 | 55.53% | 1.426 | 27,675.3 | 1,449.0 | 19.10 | 6.86 |
| ATR P70 / LB500 CURRENT | 4,040 | 11,385 | 54.95% | 1.393 | 26,992.0 | 1,618.2 | 16.68 | 6.68 |
| ATR P70 / LB750 | 4,055 | 11,370 | 55.73% | 1.443 | 30,506.7 | 1,322.0 | 23.08 | 7.52 |
| ATR P75 / LB500 | 3,401 | 12,024 | 55.10% | 1.371 | 21,697.1 | 1,516.2 | 14.31 | 6.38 |

---

## 現行ATR P70 / Lookback500 の評価

現行に近い条件：

```text
ATR P70 / Lookback 500
```

結果：

```text
Trades: 15,425 → 4,040
ATR Rejects: 11,385
Total Pips: 87,937.4 → 26,992.0
RoMD: 41.69 → 16.68
PF: 1.370 → 1.393
```

所感：

```text
PFは少し改善するが、Trade数・Total Pips・RoMDの低下が大きい。
現行ATR P70 / Lookback500 は厳しすぎる可能性が高い。
```

---

## ATR OFF の評価

ATR OFFは以下が最大。

```text
Trades
Total Pips
RoMD
```

結果：

```text
Trades: 15,425
Total Pips: 87,937.4
RoMD: 41.69
PF: 1.370
```

所感：

```text
PFはATR ONより低いが、十分高い。
トレード機会を大きく残せる。
損失額固定型・週次複利運用では有力候補。
```

---

## ATR P60 / Lookback500 の評価

ATRを使う場合の最有力候補。

結果：

```text
Trades: 5,391
PF: 1.445
Total Pips: 38,682.8
Max DD: 1,471.1
RoMD: 26.30
```

所感：

```text
ATR条件の中ではバランスが良い。
ただしATR OFFと比べると、Trade数・Total Pips・RoMDは大きく低下する。
```

---

## ATR P70 / Lookback750 の評価

P70系では比較的マシ。

結果：

```text
Trades: 4,055
PF: 1.443
Total Pips: 30,506.7
Max DD: 1,322.0
RoMD: 23.08
```

所感：

```text
現行P70 / LB500よりは良い。
ただしATR OFFやP60には劣る。
採用優先度は高くない。
```

---

## ATR P75 / Lookback500 の評価

結果：

```text
Trades: 3,401
PF: 1.371
Total Pips: 21,697.1
RoMD: 14.31
```

所感：

```text
厳しすぎる。
現時点では採用候補から外してよさそう。
```

---

## Pair別の所感

### ATRが比較的効いて見えるペア

```text
AJ
AU
UJ
```

ただし、ATR OFFのRoMDやTotal Pipsが強いケースも多い。

### ATRで機会損失が大きいペア

```text
EJ
GJ
EA
GA
```

所感：

```text
全通貨一律P70は厳しすぎる可能性が高い。
Pair別・Strategy別ATRにする場合は別途検証が必要。
```

---

## Strategy別の所感

ATR P70 / Lookback500で大きく利益機会を削っているStrategyがある。

代表例：

```text
1_EJ_Log1
5_GJ_Port_Log2
19_EA_3_WedThu_Long
6_GJ_Old_Mon
2_EJ_NightBlitz_20
3_EJ_NightBlitz_21
```

所感：

```text
ATRは負けだけでなく、勝ちトレードも大きく削っている可能性がある。
特に強いStrategyの利益機会まで削っている点に注意。
```

---

## 現時点の一次結論

```text
現行ATR P70 / Lookback500：
厳しすぎる可能性が高い

ATR P75：
採用候補から外してよさそう

ATR P70 / Lookback250：
改善薄い。採用優先度低い

ATR P70 / Lookback750：
P70系では比較的マシだが、採用優先度は高くない

ATR P60 / Lookback500：
ATRを使うなら最有力の緩和候補

ATR OFF：
現時点の本命候補
```

---

## 現時点の本命組み合わせ

```text
Event Filter：
Candidate C Strategy別ハイブリッド

ATR Filter：
OFF、または P60 / Lookback500を再検証
```

---

## 注意点

この結果はpipsベースの評価である。

実運用前提は以下。

```text
損失額固定型
週ごとの複利計算
```

そのため、最終判断では以下を追加で確認する。

```text
R換算
固定損失額ベースの損益
週次複利資産曲線
最大DD率
連敗時の資産変動
週次収益の安定性
```

---

## 次にやること

```text
1. 固定損失額・週次複利モデルで再評価
2. ATR OFF / P60 / P70現行を比較
3. pipsベースと複利ベースの結論が一致するか確認
4. ATRを完全OFFにするか、P60へ緩和するか判断
```
