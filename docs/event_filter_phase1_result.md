# Event Filter Phase 1 検証結果メモ

## 検証テーマ

28ロジック統合EAにおけるイベントフィルターの妥当性確認。

主に以下を比較した。

```text
1. Event Filter OFF
2. 現行方式：イベント日を終日停止
3. 改善案：発表時間帯にポジション保有が重なる場合のみ停止
4. イベント別OFF比較
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
src/filter_validation/event_filter_validation_v1.py
```

元コード：

```text
src/portfolio_backtest_v1_2_add_aussie_logic.py
```

---

## 検証対象

28ロジック統合ポートフォリオ。

対象イベント：

```text
US CPI
US NFP
FOMC
BOJ
BOE
ECB
RBA
AUD CPI
US CPI Wednesday
```

---

## 運用前提

本検証は、最終的に以下の実運用モデルで評価する。

```text
損失額固定型
週ごとの複利計算
```

そのため、単純なpips合計だけでなく、以下も重視する。

```text
PF
Max DD
RoMD
連敗・ドローダウン局面
戦略別の偏り
週次複利運用時の安定性
```

---

## 指標停止に関する基本方針

データ上は、特定イベントを停止しない方が成績が良く見える場合がある。

例：

```text
AUD CPI
RBA
ECB
BOE
```

ただし、指標発表時にポジションを保有することは、アノマリーやエッジというより、イベント結果依存のギャンブル要素が強くなる可能性がある。

そのため、最終判断では以下を分けて考える。

```text
データ上の成績改善
実運用上の安全性
イベント発表時のギャップ・急変リスク
EA運用として許容できるか
```

方針：

```text
テストでは緩和案も検証する
ただし採用判断では、指標時ポジション保有リスクを別途考慮する
完全OFFは慎重に扱う
発表時間帯直撃のみ停止する方式を有力候補として検証する
```

---

## 比較条件

### 1. Event OFF

```text
イベントフィルターを無効化
ただし、年末年始・月別停止・個別停止などは維持
```

### 2. date_all_day

```text
現行方式
イベント日であれば、そのStrategyのEntryを終日停止
```

### 3. position_overlap

```text
改善案
予定ポジション保有時間が、イベント発表前後の停止ウィンドウと重なる場合のみ停止
```

例：

```text
FOMCが日本時間 6/18 3:00ごろに発表される場合、
6/18のEntryをすべて停止するのではなく、
その発表時間帯にポジションを保有している予定のStrategyのみ停止する。
```

---

## 全体結果

| Scenario | Trades | Rejects | Win Rate | PF | Total Pips | Max DD | RoMD | Avg Pips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Event OFF | 17,836 | 3,219 | 53.70% | 1.321 | 93,497.0 | 2,084.5 | 44.85 | 5.24 |
| date_all_day | 15,294 | 5,764 | 54.47% | 1.366 | 86,427.6 | 2,201.7 | 39.25 | 5.65 |
| position_overlap | 15,662 | 5,396 | 54.32% | 1.360 | 86,728.7 | 2,169.8 | 39.97 | 5.54 |

---

## 全体所感

### Event OFF

トレード数と総pipsは最大。

```text
Trades: 17,836
Total Pips: 93,497.0
RoMD: 44.85
```

ただしPFは最も低い。

```text
PF: 1.321
```

評価：

```text
完全OFFは機会は増えるが、トレードの質は低下する。
現時点では採用しない。
```

---

### date_all_day

PFと平均pipsは改善。

```text
PF: 1.366
Avg Pips: 5.65
```

ただし、Event OFF比でトレード数と総pipsが大きく減る。

```text
Trades: -2,542
Total Pips: -7,069.4
```

評価：

```text
安全寄りだが、やや止めすぎの可能性あり。
```

---

### position_overlap

現行date_all_dayよりトレード数が増え、Total PipsとMax DDも少し改善。

```text
Trades: +368
Total Pips: +301.1
Max DD: -31.9
RoMD: +0.72
```

PFはわずかに低下。

```text
PF: 1.366 → 1.360
```

評価：

```text
現行終日停止よりも実運用向きの可能性あり。
発表時間帯に直撃するポジションだけ停止する方式として有力候補。
```

---

## イベント別OFF比較

date_all_dayを基準に、各イベントをOFFにした場合の変化を確認。

| Event OFF | Trades増加 | PF変化 | Total Pips変化 | Max DD変化 | RoMD変化 | 一次判断 |
|---|---:|---:|---:|---:|---:|---|
| RBA OFF | +195 | +0.005 | +2,862.4 | -329.9 | +8.45 | 緩和候補 |
| ECB OFF | +103 | ±0.000 | +774.5 | -51.6 | +1.31 | 緩和候補 |
| BOE OFF | +189 | -0.001 | +1,974.1 | +10.0 | +0.72 | 緩和候補 |
| US_CPI_WEEK_WED OFF | +123 | -0.005 | -220.6 | -55.3 | +0.91 | 要確認 |
| AU_CPI OFF | ±0 | ±0 | ±0 | ±0 | ±0 | 要確認 |
| FOMC OFF | +502 | -0.005 | +1,603.7 | +135.2 | -1.58 | 完全OFFは慎重 |
| US_NFP OFF | +661 | -0.019 | -329.1 | +101.3 | -1.86 | 維持寄り |
| US_CPI OFF | +479 | -0.016 | +57.9 | +173.3 | -2.84 | 維持寄り |
| BOJ OFF | +192 | -0.008 | -254.4 | +184.6 | -3.14 | 維持寄り |

---

## イベント別の一次判断

### 現行維持寄り

```text
US_NFP
US_CPI
BOJ
```

理由：

```text
OFFにするとPFやMax DDが悪化しやすい。
重要指標として、実運用上も停止意義が高い。
```

---

### 緩和候補

```text
RBA
ECB
BOE
```

理由：

```text
OFFにすると成績が改善する傾向が見られた。
ただし、指標時ポジション保有リスクがあるため、完全OFFではなく position_overlap 方式も比較する。
```

---

### 要確認

```text
FOMC
US_CPI_WEEK_WED
AUD CPI
```

理由：

```text
FOMCは完全OFFにすると総pipsは増えるが、Max DDやRoMDが悪化。
US_CPI_WEEK_WEDは効果が微妙。
AUD CPIは今回の検証では差分が出ていないため、イベント日・対象Strategy・日付一致を再確認する。
```

---

## 戦略別の注目点

### position_overlapで改善候補

```text
17_EA_1B_Wed_Short
13_UJ_Fix_MidWeek
27_EA_China_Demand
28_GA_China_Demand
20_EA_1A_MonTue_Short
```

所感：

```text
これらは、現行の終日停止よりも position_overlap 方式の方が良さそう。
```

---

### date_all_day維持候補

```text
10_AJ_SatA
11_AJ_SatB
```

所感：

```text
position_overlapでトレードを戻すと成績が悪化。
現行の終日停止を維持する候補。
```

---

## 現時点の結論

```text
Event Filter完全OFFは採用しない
現行date_all_dayは安全寄りだが止めすぎの可能性あり
position_overlapは現行よりやや有力
最有力はStrategy別ハイブリッド方式
```

---

## 次の検証候補

次は以下の3条件を比較する。

```text
Candidate A：現行 date_all_day
Candidate B：全体 position_overlap
Candidate C：Strategy別ハイブリッド
```

---

## Strategy別ハイブリッド案

初期案：

```text
US_NFP / US_CPI / BOJ：
原則 date_all_day 維持

FOMC：
position_overlap候補

RBA：
position_overlap または緩和候補

ECB：
position_overlap または緩和候補

BOE：
position_overlap または緩和候補

AJ_SatA / AJ_SatB：
date_all_day 維持候補

EA系 / GA系 / China Demand系：
position_overlap候補
```

---

## 注意点

今回の `position_overlap` の発表時刻は仮置き。

```text
FOMC：日本時間 翌日 3:00 / 4:00想定
US CPI / NFP：21:30 / 22:30想定
BOJ：12:00仮置き
BOE：20:00 / 21:00想定
ECB：21:15 / 22:15想定
RBA：13:30仮置き
AUD CPI：10:30仮置き
```

正確なイベント時刻テーブルを用意できれば、後続検証で精度を上げる。

---

## 次にやること

```text
1. event_filter_validation_v2.py を作成
2. Candidate A / B / C を比較
3. Strategy別ハイブリッド案を定量評価
4. 指標時ポジション保有リスクを考慮して採用候補を整理
5. 採用候補を本体EAへ反映するか判断
```

---

## 後続で確認する項目

### AUD CPIの差分なしについて

Phase 1検証では、`AUD CPI OFF` にしても以下の差分が出なかった。

```text
Trades: ±0
PF: ±0
Total Pips: ±0
Max DD: ±0
RoMD: ±0
```

現時点では、AUD CPIの停止効果がないと断定しない。

考えられる理由：

1. AUD CPI日と対象StrategyのEntry予定日が重なっていない
2. AUD CPI日リストと検証期間・対象日が噛み合っていない
3. 対象Strategy側の個別停止・曜日条件で先に除外されている
4. Event Filter上は定義されているが、実質的に発動機会が少ない

対応方針：

今すぐ深掘りはしない
Phase 2以降、必要に応じてAUD CPI単体のRejectログを確認する
最終採用判断前には、AUD CPIが本当に効いていないのか確認する

正確なイベント時刻テーブルについて

position_overlap 方式では、イベント発表時刻の仮置きを使用している。

現時点の仮置き：

FOMC：日本時間 翌日 3:00 / 4:00想定
US CPI / NFP：21:30 / 22:30想定
BOJ：12:00仮置き
BOE：20:00 / 21:00想定
ECB：21:15 / 22:15想定
RBA：13:30仮置き
AUD CPI：10:30仮置き

現段階では、以下の方向性を見ることを優先する。

終日停止が良いか
発表時間帯直撃停止が良いか
Strategy別ハイブリッド方式が有効か

そのため、正確なイベント時刻テーブル作成は後続タスクとする。

ただし、本体EAへ反映する前には、可能な範囲で以下を確認する。

FOMCの日本時間発表時刻
米CPI / NFPの夏時間・冬時間
BOE / ECB / RBA / AUD CPIの発表時刻
イベントごとの停止ウィンドウ幅

対応方針：

今すぐ正確な時刻テーブル作成には進まない
v2検証では仮置き時刻のままCandidate A/B/Cを比較する
採用候補が固まった段階で、必要に応じて時刻テーブルを精密化する

実運用上の注意

データ上、特定イベントを停止しない方が良い結果になる場合でも、指標発表時にポジションを保有することはイベント結果依存のリスクがある。

特に以下は、単純な成績改善だけで判断しない。

RBA
AUD CPI
BOE
ECB
FOMC
US CPI
NFP
BOJ

最終判断では、以下を分けて見る。

データ上の優位性
指標時ポジション保有リスク
ギャップ・急変リスク
EAとして継続運用しやすいか
損失額固定型・週次複利運用で許容できるか
