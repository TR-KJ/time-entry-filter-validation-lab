# ==========================================
# Time Entry Portfolio Lab
# Fixed Risk Weekly Compound Validation v1.2
#
# Save path:
# src/filter_validation/fixed_risk_weekly_compound_validation_v1_2.py
#
# Purpose:
# - Compare Weekly Fixed Risk model with risk settings:
#   1.00% / 1.25% / 1.50% / 1.75%
# - Main candidate:
#   Event Candidate C + ATR OFF
# - Comparison conditions:
#   Event Candidate C + ATR OFF
#   Event Candidate C + ATR P60 / Lookback 500
#   Event Candidate C + ATR P70 / Lookback 500 current
#
# Current live forward EA state note:
# - FixedLot = 0.01
# - ATR Filter = ON
# - Event Filter = ON
#
# This script does NOT modify EA settings.
# It is only for Python / Google Colab validation.
#
# Input:
# - /content/ATRFilter_Allowed_Trades_v1_1.csv
#
# Required previous step:
# - Run atr_filter_validation_v1_1.py first.
#
# Output:
# - /content/FixedRiskWeeklyCompound_RiskCompare_Summary_v1_2.csv
# - /content/FixedRiskWeeklyCompound_RiskCompare_Trades_v1_2.csv
# - /content/FixedRiskWeeklyCompound_RiskCompare_Weekly_v1_2.csv
# ==========================================

import pandas as pd
import numpy as np
import os

# ==========================================
# 0. CONFIG
# ==========================================

INPUT_ALLOWED_TRADES = '/content/ATRFilter_Allowed_Trades_v1_1.csv'
OUTPUT_DIR = '/content'

INITIAL_EQUITY = 1_000_000

# Test multiple fixed-risk percentages.
RISK_PCT_LIST = [
    0.0100,  # 1.00%
    0.0125,  # 1.25%
    0.0150,  # 1.50%
    0.0175,  # 1.75%
]

TARGET_EVENT_SCENARIOS = [
    'CANDIDATE_C_HYBRID_POLICY',
]

TARGET_ATR_CONDITIONS = [
    'ATR_OFF',
    'ATR_P60_LB500',
    'ATR_P70_LB500_CURRENT',
]

# ==========================================
# 1. Load data
# ==========================================

def load_allowed_trades():
    if not os.path.exists(INPUT_ALLOWED_TRADES):
        raise FileNotFoundError(
            f'Input not found: {INPUT_ALLOWED_TRADES}\n'
            'Run atr_filter_validation_v1_1.py first.'
        )

    df = pd.read_csv(INPUT_ALLOWED_TRADES)

    required_cols = [
        'EventScenario',
        'AtrCondition',
        'Strategy',
        'Pair',
        'EntryTime',
        'CloseTime',
        'Pips',
        'SL',
    ]

    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        raise KeyError(f'Missing required columns: {missing}')

    df['EntryTime'] = pd.to_datetime(df['EntryTime'])
    df['CloseTime'] = pd.to_datetime(df['CloseTime'])
    df['Pips'] = pd.to_numeric(df['Pips'], errors='coerce')
    df['SL'] = pd.to_numeric(df['SL'], errors='coerce')

    df = df.dropna(subset=['EntryTime', 'CloseTime', 'Pips', 'SL']).copy()
    df = df[df['SL'] > 0].copy()

    df = df[df['EventScenario'].isin(TARGET_EVENT_SCENARIOS)].copy()
    df = df[df['AtrCondition'].isin(TARGET_ATR_CONDITIONS)].copy()

    if df.empty:
        raise ValueError('No rows after filtering target scenarios/ATR conditions.')

    df['R'] = df['Pips'] / df['SL']

    print('✅ Loaded allowed trades')
    print(f'Rows: {len(df):,}')
    print('Event scenarios:', sorted(df['EventScenario'].unique()))
    print('ATR conditions:', sorted(df['AtrCondition'].unique()))

    return df


# ==========================================
# 2. Metrics helpers
# ==========================================

def calc_equity_drawdown(equity_series):
    if len(equity_series) == 0:
        return 0, 0

    equity = pd.Series(equity_series)
    peak = equity.cummax()
    dd_amount = peak - equity
    dd_pct = dd_amount / peak.replace(0, np.nan)

    max_dd_amount = dd_amount.max()
    max_dd_pct = dd_pct.max()

    return float(max_dd_amount), float(max_dd_pct)


def calc_pf_from_r(df):
    gains = df[df['R'] > 0]['R'].sum()
    losses = df[df['R'] < 0]['R'].sum()

    if losses < 0:
        return gains / abs(losses)

    return np.nan


def calc_cagr(initial_equity, final_equity, start_time, end_time):
    days = (pd.Timestamp(end_time) - pd.Timestamp(start_time)).days

    if days <= 0:
        return np.nan

    years = days / 365.25

    if initial_equity <= 0 or final_equity <= 0:
        return np.nan

    return (final_equity / initial_equity) ** (1 / years) - 1


def calc_longest_loss_streak(df):
    longest = 0
    current = 0

    for r in df['R']:
        if r < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    return longest


# ==========================================
# 3. Simulation
# ==========================================

def simulate_fixed_risk_weekly(df, label, risk_pct_per_trade):
    df = df.sort_values('CloseTime').copy()
    df['Week'] = df['CloseTime'].dt.to_period('W-MON').astype(str)

    equity = INITIAL_EQUITY
    current_week = None
    weekly_risk_amount = None

    trade_rows = []

    for _, row in df.iterrows():
        week = row['Week']

        if week != current_week:
            current_week = week
            weekly_risk_amount = equity * risk_pct_per_trade

        r_multiple = row['R']
        pnl_amount = r_multiple * weekly_risk_amount
        equity_before = equity
        equity_after = equity + pnl_amount
        equity = equity_after

        out = row.to_dict()
        out['SimulationLabel'] = label
        out['RiskPctPerTrade'] = risk_pct_per_trade
        out['RiskPctLabel'] = f'{risk_pct_per_trade * 100:.2f}%'
        out['Week'] = week
        out['WeeklyRiskAmount'] = weekly_risk_amount
        out['EquityBefore'] = equity_before
        out['PnLAmount'] = pnl_amount
        out['EquityAfter'] = equity_after
        trade_rows.append(out)

    df_sim = pd.DataFrame(trade_rows)

    max_dd_amount, max_dd_pct = calc_equity_drawdown(df_sim['EquityAfter'].values)

    final_equity = df_sim['EquityAfter'].iloc[-1] if not df_sim.empty else INITIAL_EQUITY
    total_return = final_equity / INITIAL_EQUITY - 1

    start_time = df_sim['CloseTime'].min()
    end_time = df_sim['CloseTime'].max()
    cagr = calc_cagr(INITIAL_EQUITY, final_equity, start_time, end_time)

    wins = len(df_sim[df_sim['R'] > 0])
    trades = len(df_sim)
    win_rate = wins / trades * 100 if trades > 0 else np.nan

    pf_r = calc_pf_from_r(df_sim)
    longest_loss_streak = calc_longest_loss_streak(df_sim)

    summary = {
        'SimulationLabel': label,
        'RiskPctLabel': f'{risk_pct_per_trade * 100:.2f}%',
        'RiskPctPerTrade': risk_pct_per_trade,
        'Trades': trades,
        'WinRate': round(win_rate, 2),
        'PF_R': round(pf_r, 3) if not pd.isna(pf_r) else np.nan,
        'TotalR': round(df_sim['R'].sum(), 2),
        'AvgR': round(df_sim['R'].mean(), 4),
        'LongestLossStreak': longest_loss_streak,
        'InitialEquity': round(INITIAL_EQUITY, 2),
        'FinalEquity': round(final_equity, 2),
        'TotalReturnPct': round(total_return * 100, 2),
        'MaxDDAmount': round(max_dd_amount, 2),
        'MaxDDPct': round(max_dd_pct * 100, 2),
        'CAGR_Pct': round(cagr * 100, 2) if not pd.isna(cagr) else np.nan,
        'Start': start_time,
        'End': end_time,
    }

    return df_sim, summary


def run_all_simulations(df):
    sim_trades = []
    summaries = []

    group_cols = ['EventScenario', 'AtrCondition']

    for risk_pct in RISK_PCT_LIST:
        for (event_scenario, atr_condition), df_g in df.groupby(group_cols):
            label = f'{event_scenario} | {atr_condition} | Risk {risk_pct * 100:.2f}%'
            print(f'▶ Simulating: {label}')

            df_sim, summary = simulate_fixed_risk_weekly(df_g, label, risk_pct)

            summary['EventScenario'] = event_scenario
            summary['AtrCondition'] = atr_condition

            sim_trades.append(df_sim)
            summaries.append(summary)

    df_sim_all = pd.concat(sim_trades, ignore_index=True)
    df_summary = pd.DataFrame(summaries)

    df_summary = df_summary[
        [
            'EventScenario',
            'AtrCondition',
            'RiskPctLabel',
            'RiskPctPerTrade',
            'Trades',
            'WinRate',
            'PF_R',
            'TotalR',
            'AvgR',
            'LongestLossStreak',
            'InitialEquity',
            'FinalEquity',
            'TotalReturnPct',
            'MaxDDAmount',
            'MaxDDPct',
            'CAGR_Pct',
            'Start',
            'End',
        ]
    ].sort_values(['RiskPctPerTrade', 'EventScenario', 'AtrCondition'])

    return df_sim_all, df_summary


# ==========================================
# 4. Weekly summary
# ==========================================

def make_weekly_summary(df_sim_all):
    rows = []

    for (label, week), df_w in df_sim_all.groupby(['SimulationLabel', 'Week']):
        start_equity = df_w['EquityBefore'].iloc[0]
        end_equity = df_w['EquityAfter'].iloc[-1]
        weekly_return = end_equity / start_equity - 1

        rows.append({
            'SimulationLabel': label,
            'RiskPctLabel': df_w['RiskPctLabel'].iloc[0],
            'RiskPctPerTrade': df_w['RiskPctPerTrade'].iloc[0],
            'EventScenario': df_w['EventScenario'].iloc[0],
            'AtrCondition': df_w['AtrCondition'].iloc[0],
            'Week': week,
            'Trades': len(df_w),
            'WeekStartEquity': round(start_equity, 2),
            'WeekEndEquity': round(end_equity, 2),
            'WeeklyReturnPct': round(weekly_return * 100, 3),
            'WeekR': round(df_w['R'].sum(), 3),
            'WeekPnL': round(df_w['PnLAmount'].sum(), 2),
        })

    df_weekly = pd.DataFrame(rows)

    if not df_weekly.empty:
        df_weekly = df_weekly.sort_values(['RiskPctPerTrade', 'SimulationLabel', 'Week'])

    return df_weekly


# ==========================================
# 5. Monthly summary
# ==========================================

def make_monthly_summary_from_trades(df_sim_all):
    df = df_sim_all.copy()
    df['Month'] = pd.to_datetime(df['CloseTime']).dt.to_period('M').astype(str)

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

    if df_monthly.empty:
        return df_monthly, pd.DataFrame()

    df_monthly = df_monthly.sort_values(['RiskPctPerTrade', 'SimulationLabel', 'Month'])

    summary_rows = []

    group_cols_summary = [
        'SimulationLabel',
        'RiskPctLabel',
        'RiskPctPerTrade',
        'EventScenario',
        'AtrCondition',
    ]

    for keys, df_s in df_monthly.groupby(group_cols_summary):
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
        negative_month_rate = negative_months / months * 100 if months > 0 else np.nan

        equity = df_s['MonthEndEquity']
        peak = equity.cummax()
        dd_amount = peak - equity
        dd_pct = dd_amount / peak.replace(0, np.nan)

        longest_negative_month_streak = 0
        current_negative_month_streak = 0

        for v in df_s['MonthlyReturnPct']:
            if v < 0:
                current_negative_month_streak += 1
                longest_negative_month_streak = max(longest_negative_month_streak, current_negative_month_streak)
            else:
                current_negative_month_streak = 0

        summary_rows.append({
            'SimulationLabel': sim_label,
            'RiskPctLabel': risk_pct_label,
            'RiskPctPerTrade': risk_pct,
            'EventScenario': event_scenario,
            'AtrCondition': atr_condition,
            'Months': months,
            'PositiveMonths': positive_months,
            'NegativeMonths': negative_months,
            'NegativeMonthRatePct': round(negative_month_rate, 2),
            'BestMonthPct': round(df_s['MonthlyReturnPct'].max(), 2),
            'WorstMonthPct': round(df_s['MonthlyReturnPct'].min(), 2),
            'AvgMonthPct': round(df_s['MonthlyReturnPct'].mean(), 2),
            'MedianMonthPct': round(df_s['MonthlyReturnPct'].median(), 2),
            'MonthlyMaxDDAmount': round(dd_amount.max(), 2),
            'MonthlyMaxDDPct': round(dd_pct.max() * 100, 2),
            'LongestNegativeMonthStreak': longest_negative_month_streak,
            'AvgTradesPerMonth': round(df_s['Trades'].mean(), 2),
            'TotalTrades': int(df_s['Trades'].sum()),
            'StartMonth': df_s['Month'].min(),
            'EndMonth': df_s['Month'].max(),
        })

    df_monthly_summary = pd.DataFrame(summary_rows)
    df_monthly_summary = df_monthly_summary.sort_values(['RiskPctPerTrade', 'EventScenario', 'AtrCondition'])

    return df_monthly, df_monthly_summary


# ==========================================
# 6. Main
# ==========================================

df = load_allowed_trades()
df_sim_all, df_summary = run_all_simulations(df)
df_weekly = make_weekly_summary(df_sim_all)
df_monthly, df_monthly_summary = make_monthly_summary_from_trades(df_sim_all)

summary_path = f'{OUTPUT_DIR}/FixedRiskWeeklyCompound_RiskCompare_Summary_v1_2.csv'
trades_path = f'{OUTPUT_DIR}/FixedRiskWeeklyCompound_RiskCompare_Trades_v1_2.csv'
weekly_path = f'{OUTPUT_DIR}/FixedRiskWeeklyCompound_RiskCompare_Weekly_v1_2.csv'
monthly_detail_path = f'{OUTPUT_DIR}/FixedRiskMonthly_RiskCompare_Detail_v1_2.csv'
monthly_summary_path = f'{OUTPUT_DIR}/FixedRiskMonthly_RiskCompare_Summary_v1_2.csv'

df_summary.to_csv(summary_path, index=False)
df_sim_all.to_csv(trades_path, index=False)
df_weekly.to_csv(weekly_path, index=False)
df_monthly.to_csv(monthly_detail_path, index=False)
df_monthly_summary.to_csv(monthly_summary_path, index=False)

print('\n' + '=' * 80)
print('🏆 Fixed Risk Weekly Compound Risk Compare Summary v1.2')
print('=' * 80)
print(df_summary.to_string(index=False))

print('\n' + '=' * 80)
print('📅 Fixed Risk Monthly Risk Compare Summary v1.2')
print('=' * 80)
print(df_monthly_summary.to_string(index=False))

print('\n' + '=' * 80)
print('✅ CSV保存完了')
print('=' * 80)
print(f'Weekly Summary : {summary_path}')
print(f'Trades         : {trades_path}')
print(f'Weekly Detail  : {weekly_path}')
print(f'Monthly Detail : {monthly_detail_path}')
print(f'Monthly Summary: {monthly_summary_path}')
