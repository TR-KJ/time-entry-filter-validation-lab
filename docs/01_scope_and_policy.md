# 01_scope_and_policy.md

# 検証スコープと運用方針

## 目的

このリポジトリは、`time-entry-portfolio-lab` の28ロジック統合EAについて、以下のフィルター検証結果を保存するための検証用リポジトリである。

```text
1. イベントフィルター検証
2. ATRフィルター検証
3. 採用候補・不採用候補の整理
4. 本体EAへ反映する変更案の記録
```

---

## 対象Repository

```text
https://github.com/TR-KJ/time-entry-portfolio-lab.git
```

---

## 対象EA

```text
time_entry_step8_3_1_config_managed_28strategies_forward_test_ready_skiplog_compile_fixed.mq5
```

---

## 参照docs

本検証では、以下を正本として扱う。

```text
docs/01_strategy_master_list.md
docs/03_forward_test_input_defaults.md
docs/05_forward_test_record_format.md
```

必要に応じて以下も参照する。

```text
docs/04_mt5_forward_test_setup_checklist.md
docs/06_forward_test_operation_guide.md
```

---

## 検証対象

### 1. イベントフィルター

確認する内容：

```text
イベント停止が必要な日を正しく止めているか
止めすぎていないか
戦略別イベント対象が妥当か
イベント別の影響範囲が妥当か
```

対象イベント：

```text
US CPI
NFP
FOMC
BOJ
BOE
ECB
RBA
AUD CPI
```

---

### 2. ATRフィルター

現行設定：

```text
InpUseGlobalAtrP70Filter = true
InpAtrTimeframe = PERIOD_H1
InpAtrPeriod = 14
InpAtrP70LookbackBars = 500
InpAtrPercentile = 70.0
InpAtrUseClosedBar = true
InpPrintAtrFilterLogs = false
```

確認する内容：

```text
ATR P70が厳しすぎないか
ATR Filter OFFと比較して有効か
P60 / P65 / P70 / P75 の差
Lookback 250 / 500 / 750 の差
戦略別・通貨別に適性が違うか
```

---

## 検証順序

原則として、以下の順番で進める。

```text
Phase 1：イベントフィルター検証
Phase 2：ATRフィルター検証
Phase 3：イベント + ATR 統合比較
Phase 4：本体EAへの反映候補整理
```

---

## 運用方針

本番フォワード中のEA設定は、検証結果が出るまで頻繁に変更しない。

原則：

```text
フォワードEA：現行設定で継続
検証repo：別ラインで比較検証
採用判断：週末または区切り時点でまとめて行う
EA変更：GitHub docsに記録してから反映
```

---

## 現行フォワード設定

```text
LotMode = Fixed Lot
FixedLot = 0.01
ATR Filter = ON
Event Filter = ON
EmergencyStop = false
TestMode = false
MockJST = false
TestTimes = false
```

---

## 採用判断の基準

採用候補にする条件：

```text
PFが改善する
Max DDが改善する
Entry数が減りすぎない
特定戦略だけに悪影響が集中しない
フォワードログとバックテスト結果の整合性がある
```

不採用候補にする条件：

```text
Entry数が大きく減る
PFが悪化する
Max DDが改善しない
特定通貨ペアの機会損失が大きい
ロジックの意図と合わない
```

---

## 記録ルール

検証結果は、以下の観点で記録する。

```text
検証条件
対象期間
対象Strategy
Entry数
Reject数
Win Rate
PF
Max DD
採用判断
理由
```

---

## 注意点

このリポジトリは検証用であり、本体EAを直接変更する場所ではない。

本体EAへ反映する場合は、必ず以下を記録する。

```text
変更前
変更後
変更理由
検証結果
反映日
対象EAバージョン
```

---

## 次にやること

```text
1. イベントフィルター現行ルール整理
2. 戦略別Event Filter一覧作成
3. イベント別停止対象一覧作成
4. Event Filter ON / OFF 比較条件作成
5. ATR比較条件作成
```

## 検証方針の補足

現行EAのフォワードテストは、EAが仕様どおりに動作するかを確認することを目的とする。

フィルターの採用判断は、フォワード成績ではなく、Python / Google Colab による過去データ検証を主軸に行う。

フォワードテストでは以下を確認する。

```text
Entry時刻
Direction
Lot
SL / TP
Time Exit
Event Reject
ATR Reject
想定外Entry / 想定外停止
```

Python検証では以下を比較する。

Event Filter ON / OFF
Event別除外効果
ATR Filter OFF
ATR P60 / P65 / P70 / P75
ATR Lookback 250 / 500 / 750
Strategy別・Pair別の影響
