# ==========================================
# Time Entry Portfolio Lab
# Fixed Risk Weekly Compound Validation v1
#
# Save path:
# src/filter_validation/fixed_risk_weekly_compound_validation_v1.py
#
# Purpose:
# - Compare ATR OFF / ATR P60 / ATR P70 current using fixed-risk-per-trade model.
# - Risk amount is fixed within each week.
# - Risk amount is recalculated at the start of each week from current equity.
#
# Input:
# - /content/ATRFilter_Allowed_Trades_v1_1.csv
#
# Required previous step:
# - Run atr_filter_validation_v1_1.py first.
#
# Main scenarios:
# - Candidate C Event + ATR OFF
# - Candidate C Event + ATR P60 / Lookback 500
# - Candidate C Event + ATR P70 / Lookback 500 current
#
# Notes:
# - R multiple is calculated as Pips / SL.
# - If SL is missing or <= 0, that trade is excluded from fixed-risk simulation.
# - Default initial equity and risk % are configurable below.
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
RISK_PCT_PER_TRADE = 0.0025  # 0.25% per trade, fixed during each week

TARGET_EVENT_SCENARIOS = [
    'CANDIDATE_C_HYBRID_POLICY',
]

TARGET_ATR_CONDITIONS = [
    'ATR_OFF',
    'ATR_P60_LB500',
    'ATR_P70_LB500_CURRENT',
]

# Week starts on Monday.
WEEK_FREQ = 'W-MON'

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


# ==========================================
# 3. Simulation
# ==========================================

def simulate_fixed_risk_weekly(df, label):
    df = df.sort_values('CloseTime').copy()
    df['Week'] = df['CloseTime'].dt.to_period('W-MON').astype(str)

    equity = INITIAL_EQUITY
    current_week = None
    weekly_risk_amount = None

    trade_rows = []
    equity_points = []

    for _, row in df.iterrows():
        week = row['Week']

        if week != current_week:
            current_week = week
            weekly_risk_amount = equity * RISK_PCT_PER_TRADE

        r_multiple = row['R']
        pnl_amount = r_multiple * weekly_risk_amount
        equity_before = equity
        equity_after = equity + pnl_amount
        equity = equity_after

        out = row.to_dict()
        out['SimulationLabel'] = label
        out['Week'] = week
        out['RiskPctPerTrade'] = RISK_PCT_PER_TRADE
        out['WeeklyRiskAmount'] = weekly_risk_amount
        out['EquityBefore'] = equity_before
        out['PnLAmount'] = pnl_amount
        out['EquityAfter'] = equity_after
        trade_rows.append(out)
        equity_points.append(equity_after)

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

    summary = {
        'SimulationLabel': label,
        'Trades': trades,
        'WinRate': round(win_rate, 2),
        'PF_R': round(pf_r, 3) if not pd.isna(pf_r) else np.nan,
        'TotalR': round(df_sim['R'].sum(), 2),
        'AvgR': round(df_sim['R'].mean(), 4),
        'InitialEquity': round(INITIAL_EQUITY, 2),
        'FinalEquity': round(final_equity, 2),
        'TotalReturnPct': round(total_return * 100, 2),
        'MaxDDAmount': round(max_dd_amount, 2),
        'MaxDDPct': round(max_dd_pct * 100, 2),
        'CAGR_Pct': round(cagr * 100, 2) if not pd.isna(cagr) else np.nan,
        'RiskPctPerTrade': RISK_PCT_PER_TRADE,
        'Start': start_time,
        'End': end_time,
    }

    return df_sim, summary


def run_all_simulations(df):
    sim_trades = []
    summaries = []

    group_cols = ['EventScenario', 'AtrCondition']

    for (event_scenario, atr_condition), df_g in df.groupby(group_cols):
        label = f'{event_scenario} | {atr_condition}'
        print(f'▶ Simulating: {label}')

        df_sim, summary = simulate_fixed_risk_weekly(df_g, label)

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
            'Trades',
            'WinRate',
            'PF_R',
            'TotalR',
            'AvgR',
            'InitialEquity',
            'FinalEquity',
            'TotalReturnPct',
            'MaxDDAmount',
            'MaxDDPct',
            'CAGR_Pct',
            'RiskPctPerTrade',
            'Start',
            'End',
        ]
    ].sort_values(['EventScenario', 'AtrCondition'])

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
        df_weekly = df_weekly.sort_values(['SimulationLabel', 'Week'])

    return df_weekly


# ==========================================
# 5. Main
# ==========================================

df = load_allowed_trades()
df_sim_all, df_summary = run_all_simulations(df)
df_weekly = make_weekly_summary(df_sim_all)

summary_path = f'{OUTPUT_DIR}/FixedRiskWeeklyCompound_Summary_v1.csv'
trades_path = f'{OUTPUT_DIR}/FixedRiskWeeklyCompound_Trades_v1.csv'
weekly_path = f'{OUTPUT_DIR}/FixedRiskWeeklyCompound_Weekly_v1.csv'

df_summary.to_csv(summary_path, index=False)
df_sim_all.to_csv(trades_path, index=False)
df_weekly.to_csv(weekly_path, index=False)

print('\n' + '=' * 80)
print('🏆 Fixed Risk Weekly Compound Summary')
print('=' * 80)
print(df_summary.to_string(index=False))

print('\n' + '=' * 80)
print('✅ CSV保存完了')
print('=' * 80)
print(f'Summary: {summary_path}')
print(f'Trades : {trades_path}')
print(f'Weekly : {weekly_path}')
