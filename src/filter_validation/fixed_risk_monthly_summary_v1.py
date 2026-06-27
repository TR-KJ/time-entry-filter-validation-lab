# ==========================================
# Time Entry Portfolio Lab
# Fixed Risk Monthly Summary v1
#
# Save path:
# src/filter_validation/fixed_risk_monthly_summary_v1.py
#
# Purpose:
# - Create monthly performance summary from fixed-risk weekly compound trade log.
# - Evaluate monthly roughness for:
#   ATR OFF / ATR P60 / ATR P70 current
#   Risk 1.0% / 1.5% / 2.0%
#
# Input:
# - /content/FixedRiskWeeklyCompound_RiskCompare_Trades_v1_1.csv
#
# Required previous step:
# - Run fixed_risk_weekly_compound_validation_v1_1.py first.
#
# Output:
# - /content/FixedRiskMonthly_Summary_v1.csv
# - /content/FixedRiskMonthly_Detail_v1.csv
# - /content/FixedRiskMonthly_WorstMonths_v1.csv
# ==========================================

import pandas as pd
import numpy as np
import os

# ==========================================
# 0. CONFIG
# ==========================================

INPUT_TRADES = '/content/FixedRiskWeeklyCompound_RiskCompare_Trades_v1_1.csv'
OUTPUT_DIR = '/content'

WORST_MONTHS_TOP_N = 15

# ==========================================
# 1. Load data
# ==========================================

def load_trades():
    if not os.path.exists(INPUT_TRADES):
        raise FileNotFoundError(
            f'Input not found: {INPUT_TRADES}\n'
            'Run fixed_risk_weekly_compound_validation_v1_1.py first.'
        )

    df = pd.read_csv(INPUT_TRADES)

    required_cols = [
        'SimulationLabel',
        'RiskPctLabel',
        'RiskPctPerTrade',
        'EventScenario',
        'AtrCondition',
        'CloseTime',
        'R',
        'PnLAmount',
        'EquityBefore',
        'EquityAfter',
    ]

    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        raise KeyError(f'Missing required columns: {missing}')

    df['CloseTime'] = pd.to_datetime(df['CloseTime'])
    df['R'] = pd.to_numeric(df['R'], errors='coerce')
    df['PnLAmount'] = pd.to_numeric(df['PnLAmount'], errors='coerce')
    df['EquityBefore'] = pd.to_numeric(df['EquityBefore'], errors='coerce')
    df['EquityAfter'] = pd.to_numeric(df['EquityAfter'], errors='coerce')
    df['RiskPctPerTrade'] = pd.to_numeric(df['RiskPctPerTrade'], errors='coerce')

    df = df.dropna(subset=['CloseTime', 'R', 'PnLAmount', 'EquityBefore', 'EquityAfter']).copy()

    df['Month'] = df['CloseTime'].dt.to_period('M').astype(str)

    print('✅ Loaded fixed-risk trades')
    print(f'Rows: {len(df):,}')
    print('Simulations:', len(df['SimulationLabel'].unique()))

    return df

# ==========================================
# 2. Metrics
# ==========================================

def calc_drawdown_from_monthly_equity(df_monthly):
    if df_monthly.empty:
        return 0, 0

    equity = df_monthly['MonthEndEquity']
    peak = equity.cummax()
    dd_amount = peak - equity
    dd_pct = dd_amount / peak.replace(0, np.nan)

    return float(dd_amount.max()), float(dd_pct.max())


def longest_negative_streak(values):
    longest = 0
    current = 0

    for v in values:
        if v < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    return longest


# ==========================================
# 3. Monthly detail
# ==========================================

def make_monthly_detail(df):
    rows = []

    group_cols = [
        'SimulationLabel',
        'RiskPctLabel',
        'RiskPctPerTrade',
        'EventScenario',
        'AtrCondition',
        'Month',
    ]

    for keys, df_m in df.groupby(group_cols):
        (
            sim_label,
            risk_pct_label,
            risk_pct,
            event_scenario,
            atr_condition,
            month,
        ) = keys

        df_m = df_m.sort_values('CloseTime').copy()

        month_start_equity = df_m['EquityBefore'].iloc[0]
        month_end_equity = df_m['EquityAfter'].iloc[-1]
        monthly_return = month_end_equity / month_start_equity - 1

        rows.append({
            'SimulationLabel': sim_label,
            'RiskPctLabel': risk_pct_label,
            'RiskPctPerTrade': risk_pct,
            'EventScenario': event_scenario,
            'AtrCondition': atr_condition,
            'Month': month,
            'Trades': len(df_m),
            'MonthStartEquity': round(month_start_equity, 2),
            'MonthEndEquity': round(month_end_equity, 2),
            'MonthlyReturnPct': round(monthly_return * 100, 3),
            'MonthR': round(df_m['R'].sum(), 3),
            'MonthPnL': round(df_m['PnLAmount'].sum(), 2),
        })

    df_monthly = pd.DataFrame(rows)

    if not df_monthly.empty:
        df_monthly = df_monthly.sort_values(['RiskPctPerTrade', 'SimulationLabel', 'Month'])

    return df_monthly


# ==========================================
# 4. Summary
# ==========================================

def make_monthly_summary(df_monthly):
    rows = []

    group_cols = [
        'SimulationLabel',
        'RiskPctLabel',
        'RiskPctPerTrade',
        'EventScenario',
        'AtrCondition',
    ]

    for keys, df_s in df_monthly.groupby(group_cols):
        (
            sim_label,
            risk_pct_label,
            risk_pct,
            event_scenario,
            atr_condition,
        ) = keys

        df_s = df_s.sort_values('Month').copy()

        months = len(df_s)
        negative_months = len(df_s[df_s['MonthlyReturnPct'] < 0])
        positive_months = len(df_s[df_s['MonthlyReturnPct'] > 0])
        flat_months = months - negative_months - positive_months

        negative_month_rate = negative_months / months * 100 if months > 0 else np.nan

        worst_month = df_s['MonthlyReturnPct'].min()
        best_month = df_s['MonthlyReturnPct'].max()
        avg_month = df_s['MonthlyReturnPct'].mean()
        median_month = df_s['MonthlyReturnPct'].median()

        max_dd_amount, max_dd_pct = calc_drawdown_from_monthly_equity(df_s)
        longest_neg = longest_negative_streak(df_s['MonthlyReturnPct'].values)

        rows.append({
            'SimulationLabel': sim_label,
            'RiskPctLabel': risk_pct_label,
            'RiskPctPerTrade': risk_pct,
            'EventScenario': event_scenario,
            'AtrCondition': atr_condition,
            'Months': months,
            'PositiveMonths': positive_months,
            'NegativeMonths': negative_months,
            'FlatMonths': flat_months,
            'NegativeMonthRatePct': round(negative_month_rate, 2),
            'BestMonthPct': round(best_month, 2),
            'WorstMonthPct': round(worst_month, 2),
            'AvgMonthPct': round(avg_month, 2),
            'MedianMonthPct': round(median_month, 2),
            'MonthlyMaxDDAmount': round(max_dd_amount, 2),
            'MonthlyMaxDDPct': round(max_dd_pct * 100, 2),
            'LongestNegativeMonthStreak': longest_neg,
            'AvgTradesPerMonth': round(df_s['Trades'].mean(), 2),
            'TotalTrades': int(df_s['Trades'].sum()),
            'StartMonth': df_s['Month'].min(),
            'EndMonth': df_s['Month'].max(),
        })

    df_summary = pd.DataFrame(rows)

    if not df_summary.empty:
        df_summary = df_summary.sort_values(['RiskPctPerTrade', 'EventScenario', 'AtrCondition'])

    return df_summary


def make_worst_months(df_monthly):
    rows = []

    for sim_label, df_s in df_monthly.groupby('SimulationLabel'):
        df_worst = df_s.sort_values('MonthlyReturnPct').head(WORST_MONTHS_TOP_N).copy()
        rows.append(df_worst)

    if not rows:
        return pd.DataFrame()

    df_worst_all = pd.concat(rows, ignore_index=True)
    df_worst_all = df_worst_all.sort_values(['SimulationLabel', 'MonthlyReturnPct'])

    return df_worst_all

# ==========================================
# 5. Main
# ==========================================

df = load_trades()
df_monthly = make_monthly_detail(df)
df_summary = make_monthly_summary(df_monthly)
df_worst = make_worst_months(df_monthly)

monthly_detail_path = f'{OUTPUT_DIR}/FixedRiskMonthly_Detail_v1.csv'
monthly_summary_path = f'{OUTPUT_DIR}/FixedRiskMonthly_Summary_v1.csv'
worst_months_path = f'{OUTPUT_DIR}/FixedRiskMonthly_WorstMonths_v1.csv'

df_monthly.to_csv(monthly_detail_path, index=False)
df_summary.to_csv(monthly_summary_path, index=False)
df_worst.to_csv(worst_months_path, index=False)

print('\n' + '=' * 80)
print('🏆 Fixed Risk Monthly Summary')
print('=' * 80)
print(df_summary.to_string(index=False))

print('\n' + '=' * 80)
print('✅ CSV保存完了')
print('=' * 80)
print(f'Monthly Summary: {monthly_summary_path}')
print(f'Monthly Detail : {monthly_detail_path}')
print(f'Worst Months   : {worst_months_path}')
