# ==========================================
# Time Entry Portfolio Lab
# Event Filter Validation v2
#
# Save path:
# src/filter_validation/event_filter_validation_v2.py
#
# Purpose:
# - Compare Candidate A / B / C after Phase 1 event-filter review.
# - Candidate A: current date_all_day event stop.
# - Candidate B: global position_overlap event stop.
# - Candidate C: strategy/event hybrid event stop.
#
# Important:
# - ATR filter is intentionally NOT included in this file.
# - This file reuses functions from event_filter_validation_v1.py.
# - Run this in Google Colab.
# ==========================================

from google.colab import drive
import pandas as pd
import numpy as np
import urllib.request
import os

# ==========================================
# 0. CONFIG
# ==========================================

drive.mount('/content/drive')

V1_SOURCE_URLS = [
    'https://raw.githubusercontent.com/TR-KJ/time-entry-filter-validation-lab/main/src/filter_validation/event_filter_validation_v1.py',
    'https://raw.githubusercontent.com/TR-KJ/time-entry-portfolio-lab/main/src/filter_validation/event_filter_validation_v1.py',
]

LOCAL_V1_SOURCE_PATH = '/content/event_filter_validation_v1.py'

OUTPUT_DIR = '/content'

# Candidate C policy
# Available values:
# - date_all_day
# - position_overlap
# - off
HYBRID_EVENT_POLICY = {
    # Core US / JPY risk events: keep conservative all-day stop.
    'US_NFP': 'date_all_day',
    'US_CPI': 'date_all_day',
    'US_CPI_WEEK_WED': 'date_all_day',
    'BOJ': 'date_all_day',

    # FOMC: avoid complete OFF, but allow entries that do not overlap the announcement window.
    'FOMC': 'position_overlap',
    'FOMC_PREV': 'position_overlap',

    # Events that improved or looked over-filtered in Phase 1: test overlap rather than full OFF.
    'RBA': 'position_overlap',
    'ECB': 'position_overlap',
    'BOE': 'position_overlap',

    # Keep in test framework, but final judgment later because Phase 1 showed no difference.
    'AU_CPI': 'position_overlap',
}

# Strategy-specific override.
# Phase 1 showed AJ SatA / SatB worsened when events were loosened via overlap.
STRATEGY_EVENT_POLICY_OVERRIDE = {
    '10_AJ_SatA': {
        'FOMC': 'date_all_day',
        'US_NFP': 'date_all_day',
        'US_CPI': 'date_all_day',
        'BOJ': 'date_all_day',
        'RBA': 'date_all_day',
        'AU_CPI': 'date_all_day',
    },
    '11_AJ_SatB': {
        'FOMC': 'date_all_day',
        'US_NFP': 'date_all_day',
        'US_CPI': 'date_all_day',
        'BOJ': 'date_all_day',
        'RBA': 'date_all_day',
        'AU_CPI': 'date_all_day',
    },
}

# ==========================================
# 1. Bootstrap v1 without running v1 main block
# ==========================================

def load_v1_source():
    for url in V1_SOURCE_URLS:
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                text = response.read().decode('utf-8')
            print(f'✅ Loaded v1 source from: {url}')
            return text
        except Exception as e:
            print(f'⚠️ Could not load v1 source from {url}: {e}')

    if os.path.exists(LOCAL_V1_SOURCE_PATH):
        with open(LOCAL_V1_SOURCE_PATH, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f'✅ Loaded v1 source from local path: {LOCAL_V1_SOURCE_PATH}')
        return text

    raise FileNotFoundError('event_filter_validation_v1.py could not be loaded.')


def bootstrap_v1_definitions():
    source = load_v1_source()

    # Strip v1 auto-run block.
    markers = [
        '\nload_all_data()\nrun_main_comparison()\nrun_event_by_event_comparison()\nsave_outputs()\n',
        '\nload_all_data()\n',
    ]

    cut_pos = -1

    for marker in markers:
        pos = source.find(marker)

        if pos >= 0:
            cut_pos = pos
            break

    if cut_pos >= 0:
        source = source[:cut_pos]

    # Avoid duplicate drive mount in v1.
    source = source.replace("from google.colab import drive\n", '')
    source = source.replace("drive.mount('/content/drive')\n", '')

    exec(source, globals())
    print('✅ v1 functions bootstrapped')


bootstrap_v1_definitions()

# ==========================================
# 2. Hybrid event filter logic
# ==========================================

def effective_event_policy(strategy, event_name):
    strategy_override = STRATEGY_EVENT_POLICY_OVERRIDE.get(strategy, {})

    if event_name in strategy_override:
        return strategy_override[event_name]

    return HYBRID_EVENT_POLICY.get(event_name, 'date_all_day')


def hybrid_event_reject_reason(strategy, date_str, dt, entry_dt, exit_dt, event_enabled):
    individual_reason = individual_stop_reason(strategy, dt)

    if individual_reason is not None:
        return individual_reason

    matches = matching_events_for_strategy(strategy, date_str, event_enabled)

    if not matches:
        return None

    for item in matches:
        event_name = item['Event']
        event_source_date = item['EventSourceDate']
        policy = effective_event_policy(strategy, event_name)

        if policy == 'off':
            continue

        if policy == 'date_all_day':
            return event_name

        if policy == 'position_overlap':
            if event_window_overlaps_position(event_name, event_source_date, entry_dt, exit_dt):
                return event_name
            continue

        raise ValueError(f'Unknown hybrid policy: {policy}')

    return None


def run_strategy_hybrid_validation(
    scenario,
    event_enabled,
    pair_str,
    strat_name,
    t,
    o,
    h,
    l,
    idx_map,
    unique_dates,
    is_long,
    pip_size,
    spread_pips,
    wd_target,
    en_h,
    en_m,
    ex_h,
    ex_m,
    days_offset,
    sl,
    tp,
    is_uj_special=False,
    uj_mode=None,
    custom_date_rule=None
):
    global all_trades

    if t is None:
        return

    spread_price = spread_pips * pip_size

    for dt_np in unique_dates:
        dt = pd.Timestamp(dt_np)
        date_str = dt.strftime('%Y-%m-%d')
        wd = dt.weekday()

        current_en_h = en_h
        current_en_m = en_m
        current_sl = sl
        current_tp = tp

        if is_uj_special:
            if uj_mode == 'short_core_calendar_end':
                if dt.day < 20:
                    continue
                if dt.day in [21, 22]:
                    continue
                if dt.month == 8:
                    continue
                if wd == 2:
                    continue
                if is_calendar_month_end(dt):
                    continue

                if dt.day in [20, 25, 30]:
                    current_en_h = 9
                    current_en_m = 55
                    current_sl = 20
                    current_tp = 50
                else:
                    current_en_h = 8
                    current_en_m = 4
                    current_sl = 50
                    current_tp = 999

            elif uj_mode == '25_onwards_wed_thu':
                if dt.day < 25:
                    continue
                if wd not in [2, 3]:
                    continue

            elif uj_mode == '3rd':
                if dt.day != 3:
                    continue

            elif uj_mode == 'aug_1_10':
                if dt.month != 8:
                    continue
                if dt.day > 10:
                    continue

            elif uj_mode == '10th_not_wed':
                if dt.day != 10:
                    continue
                if wd == 2:
                    continue

            else:
                continue

        else:
            if custom_date_rule is not None:
                if not custom_date_rule(dt):
                    continue
            else:
                if wd not in wd_target:
                    continue

        en_dt = dt + pd.Timedelta(hours=current_en_h, minutes=current_en_m)
        ex_dt = dt + pd.Timedelta(days=days_offset, hours=ex_h, minutes=ex_m)

        reject_reason = hybrid_event_reject_reason(
            strat_name,
            date_str,
            dt,
            en_dt,
            ex_dt,
            event_enabled
        )

        if reject_reason is not None:
            add_reject(scenario, strat_name, pair_str, dt, en_dt, ex_dt, reject_reason, 'hybrid')
            continue

        if en_dt not in idx_map:
            continue

        s_idx = idx_map[en_dt]
        e_idx = None

        for offset in range(5):
            c_dt = ex_dt + pd.Timedelta(minutes=offset)

            if c_dt in idx_map:
                e_idx = idx_map[c_dt]
                break

        if e_idx is None:
            continue

        if s_idx >= e_idx:
            continue

        if is_long:
            ep = o[s_idx] + spread_price
        else:
            ep = o[s_idx] - spread_price

        sl_val = current_sl * pip_size
        tp_val = 999 if current_tp == 999 else current_tp * pip_size

        if is_long:
            sl_price = ep - sl_val
            tp_price = ep + tp_val
        else:
            sl_price = ep + sl_val
            tp_price = ep - tp_val

        pips = 0
        closed = False
        close_time = ex_dt
        exit_reason = 'TimeExit'

        for i in range(s_idx, e_idx + 1):
            curr_h = h[i]
            curr_l = l[i]

            if is_long:
                if curr_l <= sl_price:
                    pips = -current_sl
                    closed = True
                    close_time = t[i]
                    exit_reason = 'SL'
                    break

                if current_tp != 999 and curr_h >= tp_price:
                    pips = current_tp
                    closed = True
                    close_time = t[i]
                    exit_reason = 'TP'
                    break

            else:
                if curr_h >= sl_price:
                    pips = -current_sl
                    closed = True
                    close_time = t[i]
                    exit_reason = 'SL'
                    break

                if current_tp != 999 and curr_l <= tp_price:
                    pips = current_tp
                    closed = True
                    close_time = t[i]
                    exit_reason = 'TP'
                    break

        if not closed:
            if is_long:
                pips = (o[e_idx] - ep) / pip_size
            else:
                pips = (ep - o[e_idx]) / pip_size

        all_trades.append({
            'Scenario': scenario,
            'EventFilterMode': 'hybrid',
            'Strategy': strat_name,
            'Pair': pair_str,
            'Direction': 'Long' if is_long else 'Short',
            'EntryTime': en_dt,
            'CloseTime': pd.Timestamp(close_time),
            'Pips': round(float(pips), 3),
            'ExitReason': exit_reason,
            'EntryHour': current_en_h,
            'EntryMinute': current_en_m,
            'SL': current_sl,
            'TP': current_tp,
            'PipSize': pip_size,
            'SpreadPips': spread_pips,
            'SpreadPrice': spread_price
        })


def run_all_28_strategies_hybrid(scenario, event_enabled):
    print(f'\n▶ Running scenario: {scenario} / mode=hybrid')

    # Use v1-compatible 28 strategy definitions.
    strategy_calls = [
        ('EJ', '1_EJ_Log1', t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej, True, PIP_SIZE_JPY, SPREADS_PIPS['EJ'], [0, 2], 13, 55, 4, 55, 1, 70, 250, False, None, None),
        ('EJ', '2_EJ_NightBlitz_20', t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej, True, PIP_SIZE_JPY, SPREADS_PIPS['EJ'], [0, 2], 20, 56, 4, 45, 1, 45, 70, False, None, None),
        ('EJ', '3_EJ_NightBlitz_21', t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej, True, PIP_SIZE_JPY, SPREADS_PIPS['EJ'], [0, 2], 21, 56, 5, 27, 1, 75, 70, False, None, None),
        ('GJ', '4_GJ_Port_Log1', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, True, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [1, 2], 0, 0, 8, 55, 0, 130, 90, False, None, None),
        ('GJ', '5_GJ_Port_Log2', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, False, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [1, 3, 4], 9, 55, 23, 55, 0, 90, 999, False, None, None),
        ('GJ', '6_GJ_Old_Mon', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, True, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [0], 15, 45, 22, 50, 0, 50, 210, False, None, None),
        ('GJ', '7_GJ_Mon_Blitz', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, True, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [0], 18, 2, 23, 2, 0, 130, 250, False, None, None),
        ('AJ', '8_AJ_Core1', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, True, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [0], 8, 1, 22, 46, 0, 70, 110, False, None, None),
        ('AJ', '9_AJ_Core2', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, False, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [3], 17, 14, 1, 14, 1, 30, 80, False, None, None),
        ('AJ', '10_AJ_SatA', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, False, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [4], 10, 58, 13, 51, 0, 50, 25, False, None, None),
        ('AJ', '11_AJ_SatB', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, False, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [4], 18, 57, 1, 43, 1, 55, 95, False, None, None),
        ('UJ', '12_UJ_Short_Core', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, False, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 9, 55, 14, 56, 0, 20, 50, True, 'short_core_calendar_end', None),
        ('UJ', '13_UJ_Fix_MidWeek', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, True, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 18, 4, 22, 3, 0, 95, 95, True, '25_onwards_wed_thu', None),
        ('UJ', '14_UJ_Sat_3rd', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, False, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 20, 1, 3, 8, 1, 45, 70, True, '3rd', None),
        ('UJ', '15_UJ_Sat_Aug', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, False, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 19, 0, 23, 30, 0, 20, 35, True, 'aug_1_10', None),
        ('UJ', '16_UJ_T10A', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, True, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 2, 58, 9, 50, 0, 45, 110, True, '10th_not_wed', None),
        ('EA', '17_EA_1B_Wed_Short', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [2], 9, 59, 20, 58, 0, 70, 175, False, None, None),
        ('EA', '18_EA_2_MonWed_Short', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [0, 1, 2], 9, 59, 5, 26, 1, 90, 180, False, None, None),
        ('EA', '19_EA_3_WedThu_Long', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, True, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [2, 3], 20, 56, 10, 0, 1, 90, 999, False, None, None),
        ('EA', '20_EA_1A_MonTue_Short', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [0, 1], 10, 1, 16, 0, 0, 50, 125, False, None, None),
        ('GA', '21_GA_B_3', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, True, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [0], 21, 2, 10, 0, 1, 220, 100, False, None, None),
        ('GA', '22_GA_C_2', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, True, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [3], 16, 56, 1, 15, 1, 70, 80, False, None, None),
        ('GA', '23_GA_F_2', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, False, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [4], 19, 42, 22, 45, 0, 90, 200, False, None, None),
        ('GA', '24_GA_D_1', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, True, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [4], 22, 44, 3, 8, 1, 90, 200, False, None, None),
        ('AU', '25_AU_China_Demand', t_au, o_au, h_au, l_au, idx_au, dates_au, True, PIP_SIZE_NONJPY, SPREADS_PIPS['AU'], [], 10, 0, 15, 50, 0, 40, 40, False, None, lambda dt: is_weekday(dt) and (is_9_to_15(dt) or is_25_to_month_end(dt))),
        ('AJ', '26_AJ_China_Demand', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, True, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [], 10, 0, 15, 50, 0, 45, 80, False, None, lambda dt: is_weekday(dt) and is_9_to_15(dt)),
        ('EA', '27_EA_China_Demand', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [], 10, 0, 15, 50, 0, 60, 60, False, None, lambda dt: is_weekday(dt) and is_9_to_15(dt)),
        ('GA', '28_GA_China_Demand', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, False, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [], 10, 0, 16, 10, 0, 75, 70, False, None, lambda dt: is_weekday(dt) and is_9_to_15(dt)),
    ]

    for args in strategy_calls:
        run_strategy_hybrid_validation(scenario, event_enabled, *args)


# ==========================================
# 3. Main comparison
# ==========================================

def run_candidate_comparison_v2():
    # Candidate A: current all-day stop
    run_all_28_strategies('CANDIDATE_A_DATE_ALL_DAY_CURRENT', 'date_all_day', DEFAULT_EVENT_ENABLED.copy())

    # Candidate B: global overlap stop
    run_all_28_strategies('CANDIDATE_B_POSITION_OVERLAP_GLOBAL', 'position_overlap', DEFAULT_EVENT_ENABLED.copy())

    # Candidate C: hybrid policy
    run_all_28_strategies_hybrid('CANDIDATE_C_HYBRID_POLICY', DEFAULT_EVENT_ENABLED.copy())


def save_outputs_v2():
    df_trades = pd.DataFrame(all_trades)
    df_rejects = pd.DataFrame(all_rejects)

    if df_trades.empty:
        print('トレードが生成されませんでした。')
        return

    df_scenario, df_strategy, reject_summary = make_comparison_summaries(df_trades, df_rejects)

    trade_log_path = f'{OUTPUT_DIR}/EventFilter_V2_TradeLogs.csv'
    rejects_path = f'{OUTPUT_DIR}/EventFilter_V2_Rejects.csv'
    scenario_summary_path = f'{OUTPUT_DIR}/EventFilter_V2_Candidate_Summary.csv'
    strategy_summary_path = f'{OUTPUT_DIR}/EventFilter_V2_Strategy_Summary.csv'
    reject_summary_path = f'{OUTPUT_DIR}/EventFilter_V2_Reject_Summary.csv'

    df_trades.to_csv(trade_log_path, index=False)
    df_rejects.to_csv(rejects_path, index=False)
    df_scenario.to_csv(scenario_summary_path, index=False)
    df_strategy.to_csv(strategy_summary_path, index=False)
    reject_summary.to_csv(reject_summary_path, index=False)

    print('\n' + '=' * 80)
    print('🏆 Event Filter V2 Candidate Summary')
    print('=' * 80)
    print(df_scenario.to_string(index=False))

    print('\n' + '=' * 80)
    print('🚫 Event Filter V2 Reject Summary')
    print('=' * 80)

    if reject_summary.empty:
        print('No rejects')
    else:
        print(reject_summary.to_string(index=False))

    print('\n' + '=' * 80)
    print('✅ CSV保存完了')
    print('=' * 80)
    print(f'Trade Logs       : {trade_log_path}')
    print(f'Reject Logs      : {rejects_path}')
    print(f'Candidate Summary: {scenario_summary_path}')
    print(f'Strategy Summary : {strategy_summary_path}')
    print(f'Reject Summary   : {reject_summary_path}')


load_all_data()
run_candidate_comparison_v2()
save_outputs_v2()
