# Event Filter Phase 2 Candidate 比較結果メモ

## 検証テーマ

Event Filter Phase 1 の結果を受けて、以下の3候補を比較した。

```text
Candidate A：現行 date_all_day
Candidate B：全体 position_overlap
Candidate C：Strategy別ハイブリッド
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
src/filter_validation/event_filter_validation_v2.py
```

---

## 用語整理

### date_all_day

イベント日であれば、そのStrategyのEntryを終日停止する方式。

```text
イベント日に該当
→ その日のEntryを停止
```

### position_overlap

イベント発表前後の停止ウィンドウと、予定ポジション保有時間が重なる場合のみ停止する方式。

```text
Entry予定〜Exit予定
と
イベント発表前後の停止ウィンドウ
が重なる場合のみ停止
```

### 現行維持

現在EA/docsで定義されているルールを維持すること。

```text
対象イベント
対象Strategy
個別停止
月停止
曜日条件
Entry / Exit時刻
```

などを含む。

### date_all_day維持と現行維持の違い

```text
date_all_day維持：
イベント停止方式の話

現行維持：
EA全体の現行ルールを変えない話
```

今後は、以下のように表現する。

```text
イベント停止方式：date_all_day維持
ルール全体：現行維持
```

---

## 比較条件

### Candidate A：現行 date_all_day

```text
現行のイベント日終日停止方式
```

### Candidate B：全体 position_overlap

```text
全Strategy・全Eventを発表時間帯直撃停止方式にする
```

### Candidate C：Strategy別ハイブリッド

```text
イベント・Strategyごとに date_all_day / position_overlap を分ける
```

---

## Candidate C 初期ルール

```text
US_NFP / US_CPI / BOJ：
date_all_day 維持

FOMC：
position_overlap

RBA / ECB / BOE：
position_overlap

AUD CPI：
position_overlapで残すが、後で再確認

10_AJ_SatA / 11_AJ_SatB：
date_all_day 維持
```

---

## 全体結果

| Candidate | Trades | Rejects | Win Rate | PF | Total Pips | Max DD | RoMD | Avg Pips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Candidate A：現行 date_all_day | 15,294 | 5,764 | 54.47% | 1.366 | 86,427.6 | 2,201.7 | 39.25 | 5.65 |
| Candidate B：全体 position_overlap | 15,662 | 5,396 | 54.32% | 1.360 | 86,728.7 | 2,169.8 | 39.97 | 5.54 |
| Candidate C：Strategy別ハイブリッド | 15,425 | 5,633 | 54.55% | 1.370 | 87,937.4 | 2,109.4 | 41.69 | 5.70 |

---

## Candidate C の評価

Candidate C は、Candidate A に対して以下の改善が出た。

```text
Trades: +131
Rejects: -131
Win Rate: +0.08%
PF: +0.004
Total Pips: +1,509.8
Max DD: -92.3
RoMD: +2.44
Avg Pips: +0.05
```

Candidate B に対しても、トレード数は少ないが質が改善した。

```text
Trades: -237
Rejects: +237
Win Rate: +0.23%
PF: +0.010
Total Pips: +1,208.7
Max DD: -60.4
RoMD: +1.72
Avg Pips: +0.16
```

所感：

```text
Candidate C は、現行Aより改善し、
全体position_overlapのBよりも質が高い。
```

---

## Strategy別の注目点

### Candidate Cで現行維持に戻して良かったStrategy

```text
10_AJ_SatA
11_AJ_SatB
2_EJ_NightBlitz_20
3_EJ_NightBlitz_21
7_GJ_Mon_Blitz
```

これらは、全体position_overlapにすると悪化しやすく、date_all_day維持が良さそう。

---

### Candidate Cでposition_overlapが有効だったStrategy

```text
17_EA_1B_Wed_Short
28_GA_China_Demand
27_EA_China_Demand
13_UJ_Fix_MidWeek
15_UJ_Sat_Aug
20_EA_1A_MonTue_Short
```

これらは、現行の終日停止よりも、発表時間帯直撃停止の方が良い可能性がある。

---

## 現時点の一次結論

```text
Event Filter完全OFF：
不採用

全体position_overlap：
不採用寄り

現行date_all_day：
安全だが改善余地あり

Strategy別ハイブリッド：
最有力候補
```

---

## 採用候補

現時点では、Event Filterの本命候補は以下。

```text
Candidate C：Strategy別ハイブリッド
```

理由：

```text
PF改善
Total Pips改善
Max DD改善
RoMD改善
Avg Pips改善
Trade数も現行より少し増加
```

---

## 注意点

Candidate C は有力だが、すぐに本体EAへ反映しない。

理由：

```text
1. position_overlap のイベント時刻が仮置き
2. 実運用は損失額固定型・週次複利で評価する
3. 指標時ポジション保有リスクは、pips成績だけでは判断しない
4. ATR Filterとの組み合わせ確認がまだ
```

---

## 後続確認項目

### AUD CPI

Phase 1では、AUD CPI OFFで差分が出なかった。

```text
Trades: ±0
PF: ±0
Total Pips: ±0
Max DD: ±0
RoMD: ±0
```

後で以下を確認する。

```text
AUD CPI日と対象StrategyのEntry予定日が重なっているか
AUD CPI日リストが正しいか
個別停止や曜日条件で先に除外されていないか
```

### イベント時刻テーブル

position_overlapの発表時刻は仮置き。

```text
FOMC：日本時間 翌日 3:00 / 4:00想定
US CPI / NFP：21:30 / 22:30想定
BOJ：12:00仮置き
BOE：20:00 / 21:00想定
ECB：21:15 / 22:15想定
RBA：13:30仮置き
AUD CPI：10:30仮置き
```

本体EAへ反映する前に、必要に応じて精度を上げる。

---

## 次にやること

Event Filterは、現時点では Candidate C を本命候補として記録する。

次はATR Filter検証へ進む。

```text
1. ATR Filter OFF
2. ATR P60 / P65 / P70 / P75
3. Lookback 250 / 500 / 750
4. Strategy別・Pair別の影響確認
5. Candidate C Event Filterとの組み合わせ確認
```

---

## ATR検証へ進む前の前提

ATR検証では、まず以下を比較する。

```text
ATR Filter OFF
ATR P60 / Lookback 500
ATR P65 / Lookback 500
ATR P70 / Lookback 500
ATR P75 / Lookback 500
ATR P70 / Lookback 250
ATR P70 / Lookback 750
```

Event Filterについては、まず以下の2条件で見る。

```text
Event A：現行 date_all_day
Event C：Strategy別ハイブリッド
```

最終的には、以下の組み合わせを比較する。

```text
現行Event + 現行ATR
Candidate C Event + 現行ATR
Candidate C Event + ATR緩和案
Candidate C Event + ATR OFF
```
