# ==========================================
# Time Entry Portfolio Lab
# Event Filter Validation v1
#
# Save path:
# src/filter_validation/event_filter_validation_v1.py
#
# Purpose:
# - Reuse existing 28-strategy Python backtest rules from:
#   src/portfolio_backtest_v1_2_add_aussie_logic.py
# - Compare Event Filter OFF / current all-day event stop / position-overlap event stop
# - Prepare event-by-event ON/OFF validation
#
# Important:
# - ATR filter is intentionally NOT included in this file.
# - This file is for Event Filter validation only.
# ==========================================

from google.colab import drive
import pandas as pd
import numpy as np
import glob
import os
import urllib.request
from calendar import monthrange

# ==========================================
# 0. CONFIG
# ==========================================

drive.mount('/content/drive')

ORIGINAL_SOURCE_URL = 'https://raw.githubusercontent.com/TR-KJ/time-entry-portfolio-lab/main/src/portfolio_backtest_v1_2_add_aussie_logic.py'
LOCAL_ORIGINAL_SOURCE_PATH = '/content/portfolio_backtest_v1_2_add_aussie_logic.py'

# Compare modes
# - off: event filter disabled. Individual/seasonal stops remain active.
# - date_all_day: current style. Any matching event date stops all entries for that strategy.
# - position_overlap: stop only if planned holding period overlaps event window.
EVENT_FILTER_MODES = [
    'off',
    'date_all_day',
    'position_overlap'
]

# Main run mode
RUN_EVENT_BY_EVENT_TEST = True

# Event-by-event sensitivity test uses date_all_day by default.
EVENT_BY_EVENT_MODE = 'date_all_day'

# Enable/disable events for normal full-filter run.
DEFAULT_EVENT_ENABLED = {
    'US_CPI': True,
    'US_NFP': True,
    'FOMC': True,
    'FOMC_PREV': True,
    'BOJ': True,
    'BOE': True,
    'ECB': True,
    'RBA': True,
    'AU_CPI': True,
    'US_CPI_WEEK_WED': True,
}

# Event time model for position_overlap mode.
# Notes:
# - Existing date lists are treated as source event dates.
# - FOMC JST is modeled as the next JST calendar day early morning.
# - US CPI / NFP switch roughly between 21:30 and 22:30 JST depending on US DST.
# - These are validation assumptions. Adjust later if exact historical release time table is prepared.
EVENT_TIME_RULES = {
    'FOMC': {'kind': 'us_early_next_day', 'dst_hour': 3, 'std_hour': 4, 'minute': 0, 'shift_days': 1},
    'FOMC_PREV': {'kind': 'all_day_prev_guard', 'hour': 0, 'minute': 0, 'shift_days': 0},
    'US_CPI': {'kind': 'us_data', 'dst_hour': 21, 'std_hour': 22, 'minute': 30, 'shift_days': 0},
    'US_CPI_WEEK_WED': {'kind': 'us_data', 'dst_hour': 21, 'std_hour': 22, 'minute': 30, 'shift_days': 0},
    'US_NFP': {'kind': 'us_data', 'dst_hour': 21, 'std_hour': 22, 'minute': 30, 'shift_days': 0},
    'BOJ': {'kind': 'jst_fixed', 'hour': 12, 'minute': 0, 'shift_days': 0},
    'BOE': {'kind': 'uk_policy', 'dst_hour': 20, 'std_hour': 21, 'minute': 0, 'shift_days': 0},
    'ECB': {'kind': 'eu_policy', 'dst_hour': 21, 'std_hour': 22, 'minute': 15, 'shift_days': 0},
    'RBA': {'kind': 'jst_fixed', 'hour': 13, 'minute': 30, 'shift_days': 0},
    'AU_CPI': {'kind': 'jst_fixed', 'hour': 10, 'minute': 30, 'shift_days': 0},
}

# Event block window around announcement time.
# Entry is rejected if planned position holding period overlaps [event_time - pre, event_time + post].
EVENT_WINDOWS_MINUTES = {
    'FOMC': {'pre': 180, 'post': 180},
    'FOMC_PREV': {'pre': 0, 'post': 24 * 60},
    'US_CPI': {'pre': 120, 'post': 120},
    'US_CPI_WEEK_WED': {'pre': 120, 'post': 120},
    'US_NFP': {'pre': 120, 'post': 120},
    'BOJ': {'pre': 180, 'post': 180},
    'BOE': {'pre': 120, 'post': 120},
    'ECB': {'pre': 120, 'post': 120},
    'RBA': {'pre': 120, 'post': 120},
    'AU_CPI': {'pre': 120, 'post': 120},
}

OUTPUT_DIR = '/content'

# ==========================================
# 1. Bootstrap existing source without executing its data-load/backtest section
# ==========================================

def load_original_source():
    try:
        with urllib.request.urlopen(ORIGINAL_SOURCE_URL, timeout=20) as response:
            text = response.read().decode('utf-8')
        print('✅ Loaded original source from GitHub raw URL')
        return text
    except Exception as e:
        print(f'⚠️ GitHub raw load failed: {e}')

    if os.path.exists(LOCAL_ORIGINAL_SOURCE_PATH):
        with open(LOCAL_ORIGINAL_SOURCE_PATH, 'r', encoding='utf-8') as f:
            text = f.read()
        print('✅ Loaded original source from local path')
        return text

    raise FileNotFoundError('Original source could not be loaded. Check ORIGINAL_SOURCE_URL or LOCAL_ORIGINAL_SOURCE_PATH.')


def bootstrap_original_definitions():
    source = load_original_source()

    marker = '# 6. データロード'
    pos = source.find(marker)

    if pos < 0:
        marker = '# ==========================================\n# 6.'
        pos = source.find(marker)

    if pos < 0:
        raise ValueError('Could not find section marker before original data-load block.')

    prefix = source[:pos]

    # Avoid duplicate drive.mount from original source.
    prefix = prefix.replace("from google.colab import drive\n", '')
    prefix = prefix.replace("drive.mount('/content/drive')\n", '')

    exec(prefix, globals())
    print('✅ Original constants/functions bootstrapped')


bootstrap_original_definitions()

# ==========================================
# 2. Utility helpers
# ==========================================

def as_set(name):
    value = globals().get(name, [])
    return set(value)


def date_in(name, date_str):
    return date_str in as_set(name)


def is_us_dst_rough(dt):
    # Rough DST approximation for validation:
    # US DST mostly from March to early November.
    # Exact historical DST table can be added later if needed.
    return dt.month >= 3 and dt.month <= 10


def is_eu_uk_dst_rough(dt):
    # Rough Europe/UK DST approximation for validation.
    return dt.month >= 4 and dt.month <= 10


def event_datetime_jst(event_name, event_source_date):
    rule = EVENT_TIME_RULES.get(event_name)

    if rule is None:
        return None

    base = pd.Timestamp(event_source_date)
    shift_days = rule.get('shift_days', 0)
    base = base + pd.Timedelta(days=shift_days)

    kind = rule.get('kind')

    if kind in ['us_early_next_day', 'us_data']:
        hour = rule['dst_hour'] if is_us_dst_rough(base) else rule['std_hour']
        minute = rule['minute']
        return base + pd.Timedelta(hours=hour, minutes=minute)

    if kind in ['uk_policy', 'eu_policy']:
        hour = rule['dst_hour'] if is_eu_uk_dst_rough(base) else rule['std_hour']
        minute = rule['minute']
        return base + pd.Timedelta(hours=hour, minutes=minute)

    if kind == 'jst_fixed':
        return base + pd.Timedelta(hours=rule['hour'], minutes=rule['minute'])

    if kind == 'all_day_prev_guard':
        return base

    return base + pd.Timedelta(hours=rule.get('hour', 0), minutes=rule.get('minute', 0))


def overlaps(left_start, left_end, right_start, right_end):
    return left_start <= right_end and left_end >= right_start


def event_window_overlaps_position(event_name, event_source_date, entry_dt, exit_dt):
    event_dt = event_datetime_jst(event_name, event_source_date)

    if event_dt is None:
        return False

    window = EVENT_WINDOWS_MINUTES.get(event_name, {'pre': 0, 'post': 0})
    window_start = event_dt - pd.Timedelta(minutes=window['pre'])
    window_end = event_dt + pd.Timedelta(minutes=window['post'])

    return overlaps(entry_dt, exit_dt, window_start, window_end)


def make_fomc_prev_dates():
    result = set()

    for ds in as_set('FOMC_DATES'):
        prev = (pd.Timestamp(ds) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        result.add(prev)

    # Existing source may already define FOMC_PREV_OR_TODAY.
    result = result | as_set('FOMC_PREV_OR_TODAY')

    return result


FOMC_PREV_DATES = make_fomc_prev_dates()

# ==========================================
# 3. Strategy event mapping
# ==========================================

def strategy_event_names(strategy):
    if strategy == '1_EJ_Log1':
        return ['US_CPI_WEEK_WED']

    if strategy in ['2_EJ_NightBlitz_20', '3_EJ_NightBlitz_21']:
        return ['FOMC', 'US_NFP', 'US_CPI', 'BOJ', 'ECB']

    if strategy in ['5_GJ_Port_Log2', '6_GJ_Old_Mon', '7_GJ_Mon_Blitz']:
        return ['FOMC', 'US_NFP', 'US_CPI', 'BOJ', 'BOE']

    if strategy in ['8_AJ_Core1', '9_AJ_Core2', '10_AJ_SatA', '11_AJ_SatB']:
        return ['FOMC', 'US_NFP', 'US_CPI', 'BOJ', 'RBA', 'AU_CPI']

    if strategy in ['12_UJ_Short_Core', '13_UJ_Fix_MidWeek', '14_UJ_Sat_3rd', '15_UJ_Sat_Aug']:
        return ['FOMC', 'US_NFP', 'US_CPI', 'BOJ']

    if strategy == '16_UJ_T10A':
        return ['BOJ']

    if strategy in ['17_EA_1B_Wed_Short', '18_EA_2_MonWed_Short', '19_EA_3_WedThu_Long', '20_EA_1A_MonTue_Short']:
        return ['FOMC', 'US_NFP', 'US_CPI', 'ECB', 'RBA', 'AU_CPI']

    if strategy in ['21_GA_B_3', '22_GA_C_2', '23_GA_F_2', '24_GA_D_1']:
        return ['FOMC', 'US_NFP', 'US_CPI', 'BOE', 'RBA', 'AU_CPI']

    if strategy == '25_AU_China_Demand':
        return ['RBA', 'AU_CPI', 'FOMC', 'FOMC_PREV']

    if strategy == '26_AJ_China_Demand':
        return ['BOJ', 'RBA', 'AU_CPI']

    if strategy == '27_EA_China_Demand':
        return ['RBA', 'AU_CPI', 'FOMC', 'FOMC_PREV', 'ECB']

    if strategy == '28_GA_China_Demand':
        return ['RBA', 'AU_CPI', 'FOMC', 'FOMC_PREV', 'BOE']

    return []


def event_dates_for_name(event_name):
    if event_name == 'US_CPI':
        return as_set('US_CPI_DATES')

    if event_name == 'US_CPI_WEEK_WED':
        if 'cpi_wednesdays' in globals():
            return set(globals()['cpi_wednesdays'])
        return as_set('US_CPI_DATES')

    if event_name == 'US_NFP':
        return as_set('US_NFP_DATES')

    if event_name == 'FOMC':
        return as_set('FOMC_DATES')

    if event_name == 'FOMC_PREV':
        return FOMC_PREV_DATES

    if event_name == 'BOJ':
        return as_set('BOJ_DATES')

    if event_name == 'BOE':
        return as_set('BOE_DATES')

    if event_name == 'ECB':
        return as_set('ECB_DATES')

    if event_name == 'RBA':
        return as_set('RBA_DATES')

    if event_name == 'AU_CPI':
        return as_set('AU_CPI_DATES')

    return set()


def matching_events_for_strategy(strategy, date_str, event_enabled):
    matches = []

    for event_name in strategy_event_names(strategy):
        if not event_enabled.get(event_name, True):
            continue

        dates = event_dates_for_name(event_name)

        if date_str in dates:
            matches.append({'Event': event_name, 'EventSourceDate': date_str})

    return matches

# ==========================================
# 4. Individual / seasonal stop filters
# ==========================================

def individual_stop_reason(strategy, dt):
    # Keep these active in Event OFF mode.
    if is_year_end(dt):
        return 'YEAR_END_STOP'

    if strategy == '1_EJ_Log1':
        if dt.month == 2:
            return 'EJ_LOG1_FEB_STOP'
        if dt.day == 1:
            return 'EJ_LOG1_DAY1_STOP'

    if strategy == '4_GJ_Port_Log1':
        if dt.month == 12:
            return 'GJ_PORT_LOG1_DEC_STOP'
        if dt.day in [1, 2, 29, 30, 31]:
            return 'GJ_PORT_LOG1_DAY_STOP'

    if strategy == '5_GJ_Port_Log2':
        if dt.day in [18, 19, 27]:
            return 'GJ_PORT_LOG2_DAY_STOP'

    if strategy == '6_GJ_Old_Mon':
        if dt.month in [1, 2]:
            return 'GJ_OLD_MON_MONTH_STOP'

    if strategy == '9_AJ_Core2':
        if dt.month in [6, 9]:
            return 'AJ_CORE2_MONTH_STOP'
        if dt.day in [1, 20]:
            return 'AJ_CORE2_DAY_STOP'
        if dt.day >= 26:
            return 'AJ_CORE2_AFTER_26_STOP'

    if strategy == '17_EA_1B_Wed_Short':
        if dt.month == 10:
            return 'EA_OCT_STOP'
        if dt.month == 8:
            return 'EA_1B_AUG_STOP'
        if is_month_end_3_biz_days(dt):
            return 'EA_MONTH_END_3_BIZ_DAYS'

    if strategy == '18_EA_2_MonWed_Short':
        if dt.month == 10:
            return 'EA_OCT_STOP'
        if dt.month in [1, 8]:
            return 'EA_2_MONTH_STOP'
        if is_month_end_3_biz_days(dt):
            return 'EA_MONTH_END_3_BIZ_DAYS'

    if strategy == '19_EA_3_WedThu_Long':
        if dt.month == 10:
            return 'EA_OCT_STOP'
        if is_month_end_3_biz_days(dt):
            return 'EA_MONTH_END_3_BIZ_DAYS'

    if strategy == '20_EA_1A_MonTue_Short':
        if dt.month == 10:
            return 'EA_OCT_STOP'
        if dt.month == 8:
            return 'EA_1A_AUG_STOP'
        if is_month_end_3_biz_days(dt):
            return 'EA_MONTH_END_3_BIZ_DAYS'

    if strategy == '25_AU_China_Demand':
        if dt.month in [8, 10]:
            return 'AU_CHINA_MONTH_STOP'

    if strategy == '26_AJ_China_Demand':
        if dt.month in [2, 8, 10]:
            return 'AJ_CHINA_MONTH_STOP'

    if strategy == '27_EA_China_Demand':
        if dt.month in [8, 10]:
            return 'EA_CHINA_MONTH_STOP'

    if strategy == '28_GA_China_Demand':
        if dt.month in [8, 10]:
            return 'GA_CHINA_MONTH_STOP'

    return None


def event_reject_reason(strategy, date_str, dt, entry_dt, exit_dt, event_filter_mode, event_enabled):
    individual_reason = individual_stop_reason(strategy, dt)

    if individual_reason is not None:
        return individual_reason

    if event_filter_mode == 'off':
        return None

    matches = matching_events_for_strategy(strategy, date_str, event_enabled)

    if not matches:
        return None

    if event_filter_mode == 'date_all_day':
        return matches[0]['Event']

    if event_filter_mode == 'position_overlap':
        for item in matches:
            event_name = item['Event']
            event_source_date = item['EventSourceDate']

            if event_window_overlaps_position(event_name, event_source_date, entry_dt, exit_dt):
                return event_name

        return None

    raise ValueError(f'Unknown event_filter_mode: {event_filter_mode}')

# ==========================================
# 5. Validation engine
# ==========================================

all_trades = []
all_rejects = []


def add_reject(scenario, strategy, pair_str, dt, entry_dt, exit_dt, reason, event_filter_mode):
    all_rejects.append({
        'Scenario': scenario,
        'Strategy': strategy,
        'Pair': pair_str,
        'Date': dt.strftime('%Y-%m-%d'),
        'EntryTime': entry_dt,
        'ExitTime': exit_dt,
        'RejectReason': reason,
        'EventFilterMode': event_filter_mode,
    })


def run_strategy_event_validation(
    scenario,
    event_filter_mode,
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

        # ------------------------------------------
        # UJ / custom active date rules
        # ------------------------------------------
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

        reject_reason = event_reject_reason(
            strat_name,
            date_str,
            dt,
            en_dt,
            ex_dt,
            event_filter_mode,
            event_enabled
        )

        if reject_reason is not None:
            add_reject(scenario, strat_name, pair_str, dt, en_dt, ex_dt, reject_reason, event_filter_mode)
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

        if current_tp == 999:
            tp_val = 999
        else:
            tp_val = current_tp * pip_size

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
            'EventFilterMode': event_filter_mode,
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

# ==========================================
# 6. Strategy runner set
# ==========================================

def run_all_28_strategies(scenario, event_filter_mode, event_enabled):
    global all_trades

    print(f'\n▶ Running scenario: {scenario} / mode={event_filter_mode}')

    # Data variables are loaded in main() and are global for compatibility with original style.

    # --- EJ ---
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EJ', '1_EJ_Log1', t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej, True, PIP_SIZE_JPY, SPREADS_PIPS['EJ'], [0, 2], 13, 55, 4, 55, 1, 70, 250)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EJ', '2_EJ_NightBlitz_20', t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej, True, PIP_SIZE_JPY, SPREADS_PIPS['EJ'], [0, 2], 20, 56, 4, 45, 1, 45, 70)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EJ', '3_EJ_NightBlitz_21', t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej, True, PIP_SIZE_JPY, SPREADS_PIPS['EJ'], [0, 2], 21, 56, 5, 27, 1, 75, 70)

    # --- GJ ---
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GJ', '4_GJ_Port_Log1', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, True, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [1, 2], 0, 0, 8, 55, 0, 130, 90)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GJ', '5_GJ_Port_Log2', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, False, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [1, 3, 4], 9, 55, 23, 55, 0, 90, 999)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GJ', '6_GJ_Old_Mon', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, True, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [0], 15, 45, 22, 50, 0, 50, 210)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GJ', '7_GJ_Mon_Blitz', t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj, True, PIP_SIZE_JPY, SPREADS_PIPS['GJ'], [0], 18, 2, 23, 2, 0, 130, 250)

    # --- AJ ---
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'AJ', '8_AJ_Core1', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, True, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [0], 8, 1, 22, 46, 0, 70, 110)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'AJ', '9_AJ_Core2', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, False, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [3], 17, 14, 1, 14, 1, 30, 80)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'AJ', '10_AJ_SatA', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, False, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [4], 10, 58, 13, 51, 0, 50, 25)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'AJ', '11_AJ_SatB', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, False, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [4], 18, 57, 1, 43, 1, 55, 95)

    # --- UJ ---
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'UJ', '12_UJ_Short_Core', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, False, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 9, 55, 14, 56, 0, 20, 50, True, 'short_core_calendar_end')
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'UJ', '13_UJ_Fix_MidWeek', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, True, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 18, 4, 22, 3, 0, 95, 95, True, '25_onwards_wed_thu')
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'UJ', '14_UJ_Sat_3rd', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, False, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 20, 1, 3, 8, 1, 45, 70, True, '3rd')
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'UJ', '15_UJ_Sat_Aug', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, False, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 19, 0, 23, 30, 0, 20, 35, True, 'aug_1_10')
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'UJ', '16_UJ_T10A', t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj, True, PIP_SIZE_JPY, SPREADS_PIPS['UJ'], [], 2, 58, 9, 50, 0, 45, 110, True, '10th_not_wed')

    # --- EA Rev.4 ---
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EA', '17_EA_1B_Wed_Short', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [2], 9, 59, 20, 58, 0, 70, 175)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EA', '18_EA_2_MonWed_Short', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [0, 1, 2], 9, 59, 5, 26, 1, 90, 180)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EA', '19_EA_3_WedThu_Long', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, True, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [2, 3], 20, 56, 10, 0, 1, 90, 999)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EA', '20_EA_1A_MonTue_Short', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [0, 1], 10, 1, 16, 0, 0, 50, 125)

    # --- GA ---
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GA', '21_GA_B_3', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, True, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [0], 21, 2, 10, 0, 1, 220, 100)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GA', '22_GA_C_2', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, True, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [3], 16, 56, 1, 15, 1, 70, 80)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GA', '23_GA_F_2', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, False, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [4], 19, 42, 22, 45, 0, 90, 200)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GA', '24_GA_D_1', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, True, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [4], 22, 44, 3, 8, 1, 90, 200)

    # --- China Demand ---
    au_china_rule = lambda dt: is_weekday(dt) and (is_9_to_15(dt) or is_25_to_month_end(dt))
    aj_china_rule = lambda dt: is_weekday(dt) and is_9_to_15(dt)
    ea_china_rule = lambda dt: is_weekday(dt) and is_9_to_15(dt)
    ga_china_rule = lambda dt: is_weekday(dt) and is_9_to_15(dt)

    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'AU', '25_AU_China_Demand', t_au, o_au, h_au, l_au, idx_au, dates_au, True, PIP_SIZE_NONJPY, SPREADS_PIPS['AU'], [], 10, 0, 15, 50, 0, 40, 40, False, None, au_china_rule)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'AJ', '26_AJ_China_Demand', t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj, True, PIP_SIZE_JPY, SPREADS_PIPS['AJ'], [], 10, 0, 15, 50, 0, 45, 80, False, None, aj_china_rule)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'EA', '27_EA_China_Demand', t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea, False, PIP_SIZE_NONJPY, SPREADS_PIPS['EA'], [], 10, 0, 15, 50, 0, 60, 60, False, None, ea_china_rule)
    run_strategy_event_validation(scenario, event_filter_mode, event_enabled, 'GA', '28_GA_China_Demand', t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga, False, PIP_SIZE_NONJPY, SPREADS_PIPS['GA'], [], 10, 0, 16, 10, 0, 75, 70, False, None, ga_china_rule)

# ==========================================
# 7. Summary helpers
# ==========================================

def calc_summary_local(df, label):
    if df.empty:
        return {
            'Label': label,
            'Trades': 0,
            'WinRate': np.nan,
            'PF': np.nan,
            'TotalPips': 0,
            'MaxDD': 0,
            'RoMD': np.nan,
            'AvgPips': np.nan,
        }

    df = df.sort_values('CloseTime').copy()
    df['CumPips'] = df['Pips'].cumsum()
    df['MaxCumPips'] = df['CumPips'].cummax()
    df['Drawdown'] = df['MaxCumPips'] - df['CumPips']

    wins = df[df['Pips'] > 0]['Pips'].sum()
    losses = df[df['Pips'] < 0]['Pips'].sum()
    pf = wins / abs(losses) if losses < 0 else np.nan
    total_pips = df['Pips'].sum()
    max_dd = df['Drawdown'].max()
    romd = total_pips / max_dd if max_dd > 0 else np.nan
    win_rate = len(df[df['Pips'] > 0]) / len(df) * 100
    avg_pips = df['Pips'].mean()

    return {
        'Label': label,
        'Trades': len(df),
        'WinRate': round(win_rate, 2),
        'PF': round(pf, 3) if not pd.isna(pf) else np.nan,
        'TotalPips': round(total_pips, 1),
        'MaxDD': round(max_dd, 1),
        'RoMD': round(romd, 2) if not pd.isna(romd) else np.nan,
        'AvgPips': round(avg_pips, 2),
    }


def make_comparison_summaries(df_trades, df_rejects):
    scenario_rows = []

    for scenario, df_s in df_trades.groupby('Scenario'):
        row = calc_summary_local(df_s, scenario)
        row['Rejects'] = len(df_rejects[df_rejects['Scenario'] == scenario]) if not df_rejects.empty else 0
        scenario_rows.append(row)

    df_scenario = pd.DataFrame(scenario_rows).sort_values('Label')

    strategy_rows = []

    for (scenario, strategy), df_ss in df_trades.groupby(['Scenario', 'Strategy']):
        row = calc_summary_local(df_ss, f'{scenario} | {strategy}')
        row['Scenario'] = scenario
        row['Strategy'] = strategy
        row['Rejects'] = len(df_rejects[(df_rejects['Scenario'] == scenario) & (df_rejects['Strategy'] == strategy)]) if not df_rejects.empty else 0
        strategy_rows.append(row)

    df_strategy = pd.DataFrame(strategy_rows)

    if not df_strategy.empty:
        df_strategy = df_strategy[['Scenario', 'Strategy', 'Trades', 'Rejects', 'WinRate', 'PF', 'TotalPips', 'MaxDD', 'RoMD', 'AvgPips']]
        df_strategy = df_strategy.sort_values(['Strategy', 'Scenario'])

    reject_summary = pd.DataFrame()

    if not df_rejects.empty:
        reject_summary = (
            df_rejects
            .groupby(['Scenario', 'RejectReason'])
            .size()
            .reset_index(name='RejectCount')
            .sort_values(['Scenario', 'RejectCount'], ascending=[True, False])
        )

    return df_scenario, df_strategy, reject_summary

# ==========================================
# 8. Main
# ==========================================

def load_all_data():
    global t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej
    global t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj
    global t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj
    global t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj
    global t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea
    global t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga
    global t_au, o_au, h_au, l_au, idx_au, dates_au

    print('全通貨ペアデータロード中...')

    _, t_ej, o_ej, h_ej, l_ej, idx_ej, dates_ej = load_data('eurjpy_m1')
    _, t_gj, o_gj, h_gj, l_gj, idx_gj, dates_gj = load_data('gbpjpy_m1')
    _, t_aj, o_aj, h_aj, l_aj, idx_aj, dates_aj = load_data('audjpy_m1')
    _, t_uj, o_uj, h_uj, l_uj, idx_uj, dates_uj = load_data('usdjpy_m1')
    _, t_ea, o_ea, h_ea, l_ea, idx_ea, dates_ea = load_data('euraud_m1')
    _, t_ga, o_ga, h_ga, l_ga, idx_ga, dates_ga = load_data('gbpaud_m1')
    _, t_au, o_au, h_au, l_au, idx_au, dates_au = load_data('audusd_m1')


def run_main_comparison():
    for mode in EVENT_FILTER_MODES:
        scenario = f'EVENT_{mode.upper()}'
        run_all_28_strategies(scenario, mode, DEFAULT_EVENT_ENABLED.copy())


def run_event_by_event_comparison():
    if not RUN_EVENT_BY_EVENT_TEST:
        return

    for event_name in DEFAULT_EVENT_ENABLED.keys():
        if event_name == 'FOMC_PREV':
            # FOMC_PREV is tested together with FOMC in most cases.
            continue

        event_enabled = DEFAULT_EVENT_ENABLED.copy()
        event_enabled[event_name] = False

        if event_name == 'FOMC':
            event_enabled['FOMC_PREV'] = False

        scenario = f'EVENT_BY_EVENT_{EVENT_BY_EVENT_MODE}_{event_name}_OFF'
        run_all_28_strategies(scenario, EVENT_BY_EVENT_MODE, event_enabled)


def save_outputs():
    df_trades = pd.DataFrame(all_trades)
    df_rejects = pd.DataFrame(all_rejects)

    if df_trades.empty:
        print('トレードが生成されませんでした。')
        return

    df_scenario, df_strategy, reject_summary = make_comparison_summaries(df_trades, df_rejects)

    trade_log_path = f'{OUTPUT_DIR}/EventFilter_TradeLogs_v1.csv'
    rejects_path = f'{OUTPUT_DIR}/EventFilter_Rejects_v1.csv'
    scenario_summary_path = f'{OUTPUT_DIR}/EventFilter_Comparison_Summary_v1.csv'
    strategy_summary_path = f'{OUTPUT_DIR}/EventFilter_Strategy_Summary_v1.csv'
    reject_summary_path = f'{OUTPUT_DIR}/EventFilter_Reject_Summary_v1.csv'

    df_trades.to_csv(trade_log_path, index=False)
    df_rejects.to_csv(rejects_path, index=False)
    df_scenario.to_csv(scenario_summary_path, index=False)
    df_strategy.to_csv(strategy_summary_path, index=False)
    reject_summary.to_csv(reject_summary_path, index=False)

    print('\n' + '=' * 80)
    print('🏆 Event Filter Scenario Summary')
    print('=' * 80)
    print(df_scenario.to_string(index=False))

    print('\n' + '=' * 80)
    print('🚫 Event Reject Summary')
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
    print(f'Scenario Summary : {scenario_summary_path}')
    print(f'Strategy Summary : {strategy_summary_path}')
    print(f'Reject Summary   : {reject_summary_path}')


load_all_data()
run_main_comparison()
run_event_by_event_comparison()
save_outputs()
