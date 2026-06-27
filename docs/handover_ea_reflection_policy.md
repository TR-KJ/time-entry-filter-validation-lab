# EA反映方針メモ

## 目的

`time-entry-filter-validation-lab` で実施した Event Filter / ATR Filter / Fixed Risk 検証結果をもとに、今後 `time-entry-portfolio-lab` の本体EAへ反映する候補方針を整理する。

---

## 対象Repository

### 検証Repository

```text
https://github.com/TR-KJ/time-entry-filter-validation-lab.git
```

### 本体EA Repository

```text
https://github.com/TR-KJ/time-entry-portfolio-lab.git
```

---

## Repositoryの役割分担

### time-entry-filter-validation-lab

検証用Repository。

主な保存内容：

```text
Event Filter検証結果
ATR Filter検証結果
Fixed Risk / Weekly Compound検証結果
月次・週次の荒れ方確認
採用候補・不採用候補の判断理由
本体EAへ渡す反映方針メモ
```

保存先例：

```text
docs/event_filter_phase1_result.md
docs/event_filter_phase2_candidate_result.md
docs/atr_filter_phase1_result.md
docs/fixed_risk_weekly_monthly_result.md
handover/ea_reflection_policy.md
```

---

### time-entry-portfolio-lab

本体EA・正本docs用Repository。

主な保存内容：

```text
正式なStrategy Master
Forward Test Input Defaults
Forward Test Record Format
EA実装コード
本体EAへ反映する正式仕様
Forward Phase定義
変更履歴
```

保存先例：

```text
docs/07_ea_reflection_policy.md
docs/08_forward_phase2_policy.md
CHANGELOG.md
src/EA/
```

---

## 現在のEA状態

現行フォワードEAは、まだ今回の検証結果を反映していない。

```text
FixedLot = 0.01
ATR Filter = ON
Event Filter = ON
```

現行フォワードの位置づけ：

```text
Forward Phase 1-A
目的：EAが期待どおりに動作するか確認するフェーズ
評価対象：利益・PF・DDではなく、EA動作確認
```

確認対象：

```text
Entry時刻
Direction
Lot
SL / TP
Time Exit
Event Reject
ATR Reject
想定外Entry
想定外停止
```

---

## 検証結果から見た本命候補

### Event Filter

本命候補：

```text
Candidate C：Strategy別ハイブリッド
```

概要：

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

### ATR Filter

本命候補：

```text
ATR Filter OFF
```

理由：

```text
ATR P70 / Lookback500 はEntryを止めすぎる
ATR OFFがTotal Pips / RoMD / 複利成長で最有力
ATR P60は保守候補だが、機会損失が大きい
ATR P70現行は採用優先度が低い
```

---

### Risk Model

本命候補：

```text
Weekly Fixed Risk 1.5%
```

次点候補：

```text
Weekly Fixed Risk 1.0%
```

中間候補：

```text
Weekly Fixed Risk 1.25%
```

攻め候補：

```text
Weekly Fixed Risk 1.75%
```

---

## 現時点の本命構成

```text
Event Filter：
Candidate C Strategy別ハイブリッド

ATR Filter：
OFF

Risk：
Weekly Fixed Risk 1.5%
```

次点構成：

```text
Event Filter：
Candidate C Strategy別ハイブリッド

ATR Filter：
OFF

Risk：
Weekly Fixed Risk 1.0%
```

---

# 1. Event Candidate C のEA実装方針

## 必要な停止方式

EA側では、イベント停止方式を少なくとも2種類に分ける。

```text
date_all_day
position_overlap
```

---

## date_all_day

イベント日に該当する場合、そのStrategyのEntryを終日停止する方式。

```text
イベント日一致
→ その日のEntryを停止
```

対象候補：

```text
US_NFP
US_CPI
BOJ
10_AJ_SatA
11_AJ_SatB
```

---

## position_overlap

イベント発表前後の停止ウィンドウと、予定ポジション保有時間が重なる場合のみ停止する方式。

```text
Entry予定時刻 〜 Exit予定時刻
と
イベント発表前後の停止ウィンドウ
が重なる場合のみ停止
```

対象候補：

```text
FOMC
RBA
ECB
BOE
AUD CPI
一部EA系 / GA系 / China Demand系
```

---

## position_overlapに必要な情報

EA側で以下を扱う必要がある。

```text
Strategy ID
Pair
Direction
Entry JST
Exit JST
対象イベント
イベント停止方式
イベント発表時刻 JST
停止ウィンドウ開始
停止ウィンドウ終了
```

---

## イベント発表時刻の扱い

現時点では、Python検証上は仮置き時刻を使用した。

```text
FOMC：日本時間 翌日 3:00 / 4:00想定
US CPI / NFP：21:30 / 22:30想定
BOJ：12:00仮置き
BOE：20:00 / 21:00想定
ECB：21:15 / 22:15想定
RBA：13:30仮置き
AUD CPI：10:30仮置き
```

本体EA反映前に、必要に応じて精度を上げる。

---

## Event Candidate C 実装前の確認事項

```text
1. Strategy/Eventごとの date_all_day / position_overlap 対応表を作る
2. イベント発表時刻テーブルを作る
3. 停止ウィンドウ幅を決める
4. FOMC前日扱いを決める
5. AUD CPIが実質効いていない件を後で確認する
6. EVENTログの種類を分ける
```

---

## 推奨ログ

EA側では、停止理由が後で分かるようにログを分けたい。

```text
EVENT DATE STOP
EVENT OVERLAP STOP
EVENT TARGET OFF
EVENT NO MATCH
```

例：

```text
EVENT DATE STOP | Strategy=10_AJ_SatA | Event=US_CPI | Date=2026-xx-xx
EVENT OVERLAP STOP | Strategy=27_EA_China_Demand | Event=FOMC | Entry=10:00 | Exit=15:50 | EventTime=03:00
```

---

# 2. ATR Filter OFF のEA input変更方針

## 現行設定

```text
InpUseGlobalAtrP70Filter = true
InpAtrTimeframe = PERIOD_H1
InpAtrPeriod = 14
InpAtrP70LookbackBars = 500
InpAtrPercentile = 70.0
InpAtrUseClosedBar = true
```

---

## 変更案

ATR FilterをOFFにする場合、基本的には以下のみ変更する。

```text
InpUseGlobalAtrP70Filter = false
```

---

## 残す設定

将来的にATR Filterを再度ONにする可能性があるため、以下のinputは削除しない。

```text
InpAtrTimeframe = PERIOD_H1
InpAtrPeriod = 14
InpAtrP70LookbackBars = 500
InpAtrPercentile = 70.0
InpAtrUseClosedBar = true
```

---

## ログ設定

ATR OFF時は、基本的にATR Rejectログは不要。

推奨：

```text
InpPrintAtrFilterLogs = false
```

ただし、ATR OFFが正しく効いているか確認する初回のみ、一時的にログONも可。

```text
InpUseGlobalAtrP70Filter = false
InpPrintAtrFilterLogs = true
```

---

## ATR変更理由

```text
現行ATR P70 / Lookback500 はEntryを止めすぎる
Total Pips / RoMD / 固定損失額・週次複利モデルでATR OFFが最有力
P60は保守候補だが、機会損失が大きい
P70現行は採用優先度が低い
```

---

# 3. Weekly Fixed Risk 1.5% のEA実装方針

## 現行状態

現在のEAは以下。

```text
FixedLot = 0.01
LotMode = Fixed Lot
```

---

## 目標運用モデル

```text
LotMode = Weekly Fixed Risk
RiskPctPerTrade = 1.5%
```

意味：

```text
週初資金を基準に、その週の1トレードあたりの許容損失額を固定する
```

---

## 週次固定損失額の考え方

例：

```text
週初資金 = 1,000,000円
RiskPctPerTrade = 1.5%
1トレード損失額 = 15,000円
```

その週の全トレードで、損失額15,000円を基準にロット計算する。

翌週になったら、その時点の資金で再計算する。

---

## EA側に必要なinput候補

```text
InpLotMode = FixedLot / WeeklyFixedRisk
InpFixedLot = 0.01
InpRiskPctPerTrade = 1.5
InpWeeklyRiskResetDay = Monday
InpWeeklyRiskResetTimeJST = 00:00
InpMinLot = 0.01
InpMaxLot = 任意
InpLotStep = Broker Symbol Info
```

---

## ロット計算に必要な情報

```text
Account Equity
SL pips
Symbol tick value
Symbol tick size
Contract size
Lot step
Min lot
Max lot
```

---

## 注意点

Weekly Fixed RiskをEAに実装する場合、以下は必ず確認する。

```text
JPYペア / 非JPYペアでロット計算が正しいか
OANDA MT5のtick valueが正しく取得できるか
最小ロット0.01未満になった場合の処理
最大ロット制限
複数Strategy同日稼働時の合計リスク
週途中で大きく増減した場合でも、週内は固定損失額で良いか
```

---

# 4. Forward Phase名

## 現行Phase

```text
Forward Phase 1-A
```

内容：

```text
目的：EA動作確認
LotMode：FixedLot
FixedLot：0.01
ATR Filter：ON
Event Filter：ON
評価対象：利益ではなくEA動作
```

---

## 次Phase候補：動作確認優先

Weekly Fixed Risk実装前に、Event Candidate C / ATR OFFだけを確認する場合。

```text
Forward Phase 2-A
```

内容：

```text
目的：Event Candidate C + ATR OFF のEA動作確認
LotMode：FixedLot
FixedLot：0.01
Event Filter：Candidate C
ATR Filter：OFF
```

---

## 次Phase候補：実運用モデル反映

Weekly Fixed Risk 1.5%まで実装して確認する場合。

```text
Forward Phase 3-A
```

内容：

```text
目的：実運用モデルに近いフォワード
LotMode：Weekly Fixed Risk
RiskPctPerTrade：1.5%
Event Filter：Candidate C
ATR Filter：OFF
```

---

## 次点候補

1.0%で保守的に確認する場合。

```text
Forward Phase 3-B
```

内容：

```text
目的：保守リスクでの実運用モデル確認
LotMode：Weekly Fixed Risk
RiskPctPerTrade：1.0%
Event Filter：Candidate C
ATR Filter：OFF
```

---

## 中間候補

1.25%で中間リスクを確認する場合。

```text
Forward Phase 3-C
```

内容：

```text
目的：1.0%と1.5%の中間リスク確認
LotMode：Weekly Fixed Risk
RiskPctPerTrade：1.25%
Event Filter：Candidate C
ATR Filter：OFF
```

---

# 5. 反映順序

いきなり本体EAへ全て反映しない。

推奨順序：

```text
Step 1：
検証repoに結果を保存

Step 2：
本体repoにEA反映方針MDを保存

Step 3：
ATR OFF input変更だけで動作確認するか判断

Step 4：
Event Candidate Cの実装仕様を作成

Step 5：
Weekly Fixed Riskのロット計算仕様を作成

Step 6：
EA実装

Step 7：
Strategy Tester / TestMode / MockJSTで確認

Step 8：
Forward Phase 2-A または 3-Aへ移行
```

---

# 6. 本体EAへ反映する場合の変更候補

## ATR

```text
変更前：
InpUseGlobalAtrP70Filter = true

変更後：
InpUseGlobalAtrP70Filter = false
```

---

## Event

```text
変更前：
イベント対象日はStrategyごとに終日停止

変更後：
Strategy/Eventごとに date_all_day / position_overlap を分ける
```

---

## Lot / Risk

```text
変更前：
FixedLot = 0.01

変更後候補：
LotMode = WeeklyFixedRisk
RiskPctPerTrade = 1.5%
```

---

# 7. 現時点の結論

現時点の本命候補：

```text
Event Filter：
Candidate C Strategy別ハイブリッド

ATR Filter：
OFF

Risk：
Weekly Fixed Risk 1.5%
```

次点：

```text
Event Filter：
Candidate C Strategy別ハイブリッド

ATR Filter：
OFF

Risk：
Weekly Fixed Risk 1.0%
```

ただし、現行EAはまだ以下の状態。

```text
FixedLot = 0.01
ATR Filter = ON
Event Filter = ON
```

よって、次は本体EAへ反映する前に、以下を整理する。

```text
Event Candidate C実装仕様
ATR OFF input変更点
Weekly Fixed Riskロット計算仕様
Forward Phase名
```
