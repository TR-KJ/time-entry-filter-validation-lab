# ==========================================
# Time Entry Portfolio Lab
# ATR Filter Validation v1.1
#
# Save path:
# src/filter_validation/atr_filter_validation_v1_1.py
#
# Purpose:
# - Validate ATR filter settings using Event Filter V2 trade logs.
# - Compare ATR OFF / P60 / P65 / P70 / P75 / Lookback 250 / 500 / 750.
# - Compare Event Candidate A and Candidate C from Event Filter V2.
#
# Fixes from v1:
# - Handles EventFilter_V2_TradeLogs.csv column name "Scenario".
# - Adds compatibility alias "EventScenario" when missing.
# - Uses pandas resample('h') instead of deprecated resample('H').
#
# Important:
# - This script expects EventFilter V2 trade log to exist:
#   /content/EventFilter_V2_TradeLogs.csv
# - Run event_filter_validation_v2.py first.
# - This script uses M1 data from:
#   /content/drive/MyDrive/MT5 data/
# ==========================================

from google.colab import drive
import pandas as pd
import numpy as np
import glob
import os

# ==========================================
# 0. CONFIG
# ==========================================

drive.mount('/content/drive')

EVENT_V2_TRADE_LOG_PATH = '/content/EventFilter_V2_TradeLogs.csv'
OUTPUT_DIR = '/content'

MT5_DATA_DIR = '/content/drive/MyDrive/MT5 data'

# Event scenarios to validate.
# These names should match Scenario values in EventFilter_V2_TradeLogs.csv.
EVENT_SCENARIOS_TO_TEST = [
    'CANDIDATE_A_DATE_ALL_DAY_CURRENT',
    'CANDIDATE_C_HYBRID_POLICY',
]

# ATR conditions.
ATR_CONDITIONS = [
    {
        'Condition': 'ATR_OFF',
        'UseAtr': False,
        'Percentile': None,
        'Lookback': None,
    },
    {
        'Condition': 'ATR_P60_LB500',
        'UseAtr': True,
        'Percentile': 60.0,
        'Lookback': 500,
    },
    {
        'Condition': 'ATR_P65_LB500',
        'UseAtr': True,
        'Percentile': 65.0,
        'Lookback': 500,
    },
    {
        'Condition': 'ATR_P70_LB500_CURRENT',
        'UseAtr': True,
        'Percentile': 70.0,
        'Lookback': 500,
    },
    {
        'Condition': 'ATR_P75_LB500',
        'UseAtr': True,
        'Percentile': 75.0,
        'Lookback': 500,
    },
    {
        'Condition': 'ATR_P70_LB250',
        'UseAtr': True,
        'Percentile': 70.0,
        'Lookback': 250,
    },
    {
        'Condition': 'ATR_P70_LB750',
        'UseAtr': True,
        'Percentile': 70.0,
        'Lookback': 750,
    },
]

ATR_PERIOD = 14
ATR_TIMEFRAME = 'h'
ATR_USE_CLOSED_BAR = True

PAIR_TO_DATA_KEY = {
    'EJ': 'eurjpy_m1',
    'GJ': 'gbpjpy_m1',
    'AJ': 'audjpy_m1',
    'UJ': 'usdjpy_m1',
    'EA': 'euraud_m1',
    'GA': 'gbpaud_m1',
    'AU': 'audusd_m1',
}

PAIR_DISPLAY = {
    'EJ': 'EURJPY',
    'GJ': 'GBPJPY',
    'AJ': 'AUDJPY',
    'UJ': 'USDJPY',
    'EA': 'EURAUD',
    'GA': 'GBPAUD',
    'AU': 'AUDUSD',
}

# ==========================================
# 1. Load Event V2 trade log
# ==========================================

def load_event_v2_trade_log():
    if not os.path.exists(EVENT_V2_TRADE_LOG_PATH):
        raise FileNotFoundError(
            f'Event V2 trade log not found: {EVENT_V2_TRADE_LOG_PATH}\n'
            'Run event_filter_validation_v2.py first.'
        )

    df = pd.read_csv(EVENT_V2_TRADE_LOG_PATH)

    # Compatibility:
    # EventFilter V2 uses "Scenario".
    # ATR v1 expected "EventScenario".
    if 'EventScenario' not in df.columns:
        if 'Scenario' in df.columns:
            df['EventScenario'] = df['Scenario']
        else:
            raise KeyError(
                'Neither EventScenario nor Scenario column exists in Event V2 trade log.'
            )

    if 'Scenario' not in df.columns:
        df['Scenario'] = df['EventScenario']

    required_cols = [
        'EventScenario',
        'Strategy',
        'Pair',
        'EntryTime',
        'CloseTime',
        'Pips',
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise KeyError(f'Missing required columns in Event V2 trade log: {missing_cols}')

    df['EntryTime'] = pd.to_datetime(df['EntryTime'])
    df['CloseTime'] = pd.to_datetime(df['CloseTime'])
    df['Pips'] = pd.to_numeric(df['Pips'], errors='coerce')

    df = df.dropna(subset=['EntryTime', 'CloseTime', 'Pips']).copy()

    print('✅ Event V2 trade log loaded')
    print(f'Rows: {len(df):,}')
    print('Columns:', list(df.columns))
    print('Event scenarios:', sorted(df['EventScenario'].unique()))

    return df


# ==========================================
# 2. Load M1 data and build H1 ATR
# ==========================================

def load_m1_data(pair_key):
    files = glob.glob(f'{MT5_DATA_DIR}/*{pair_key}*.csv')

    if not files:
        print(f'⚠️ Data file not found for {pair_key}')
        return None

    df_list = []

    for f in files:
        tmp = pd.read_csv(
            f,
            names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'TickVol', 'Vol', 'Spread'],
            header=0,
            sep='\t'
        )
        df_list.append(tmp)

    df = pd.concat(df_list)
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])

    # Same timezone handling as existing backtest code.
    df['Datetime'] = (
        df['Datetime']
        .dt.tz_localize('Europe/Helsinki')
        .dt.tz_convert('Asia/Tokyo')
        .dt.tz_localize(None)
    )

    df = df.drop_duplicates(subset=['Datetime'])
    df = df.sort_values('Datetime')
    df = df.reset_index(drop=True)

    df = df[['Datetime', 'Open', 'High', 'Low', 'Close']].copy()
    df = df.set_index('Datetime')

    print(f'✅ Loaded M1 {pair_key}: {len(df):,} bars / {df.index.min()} 〜 {df.index.max()}')

    return df


def build_h1_ohlc(df_m1):
    df_h1 = (
        df_m1
        .resample(ATR_TIMEFRAME)
        .agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
        })
        .dropna()
        .copy()
    )

    return df_h1


def calc_atr(df_h1, period):
    high = df_h1['High']
    low = df_h1['Low']
    close = df_h1['Close']

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()

    df_atr = df_h1.copy()
    df_atr['ATR'] = atr

    return df_atr


def prepare_atr_data():
    atr_data = {}

    for pair, data_key in PAIR_TO_DATA_KEY.items():
        df_m1 = load_m1_data(data_key)

        if df_m1 is None:
            continue

        df_h1 = build_h1_ohlc(df_m1)
        df_atr = calc_atr(df_h1, ATR_PERIOD)

        atr_data[pair] = df_atr

        print(f'✅ Built ATR {pair}: {len(df_atr):,} H1 bars')

    return atr_data


# ==========================================
# 3. ATR percentile evaluation
# ==========================================

def get_closed_h1_time(entry_time):
    entry_time = pd.Timestamp(entry_time)

    floored = entry_time.floor('h')

    if ATR_USE_CLOSED_BAR:
        return floored - pd.Timedelta(hours=1)

    return floored


def get_atr_eval(pair, entry_time, percentile, lookback, atr_data):
    if pair not in atr_data:
        return {
            'AtrAvailable': False,
            'AtrPass': False,
            'CurrentATR': np.nan,
            'ThresholdATR': np.nan,
            'AtrBarTime': pd.NaT,
            'RejectReason': 'ATR_DATA_MISSING',
        }

    df_atr = atr_data[pair]
    bar_time = get_closed_h1_time(entry_time)

    if bar_time not in df_atr.index:
        return {
            'AtrAvailable': False,
            'AtrPass': False,
            'CurrentATR': np.nan,
            'ThresholdATR': np.nan,
            'AtrBarTime': bar_time,
            'RejectReason': 'ATR_BAR_MISSING',
        }

    pos = df_atr.index.get_loc(bar_time)

    if isinstance(pos, slice):
        pos = pos.start

    if pos < lookback:
        return {
            'AtrAvailable': False,
            'AtrPass': False,
            'CurrentATR': np.nan,
            'ThresholdATR': np.nan,
            'AtrBarTime': bar_time,
            'RejectReason': 'ATR_LOOKBACK_INSUFFICIENT',
        }

    current_atr = df_atr.iloc[pos]['ATR']

    if pd.isna(current_atr):
        return {
            'AtrAvailable': False,
            'AtrPass': False,
            'CurrentATR': np.nan,
            'ThresholdATR': np.nan,
            'AtrBarTime': bar_time,
            'RejectReason': 'CURRENT_ATR_NA',
        }

    lookback_atr = df_atr.iloc[pos - lookback:pos]['ATR'].dropna()

    if len(lookback_atr) < lookback * 0.8:
        return {
            'AtrAvailable': False,
            'AtrPass': False,
            'CurrentATR': float(current_atr),
            'ThresholdATR': np.nan,
            'AtrBarTime': bar_time,
            'RejectReason': 'ATR_LOOKBACK_NA_TOO_MANY',
        }

    threshold = np.percentile(lookback_atr.values, percentile)
    atr_pass = current_atr >= threshold

    return {
        'AtrAvailable': True,
        'AtrPass': bool(atr_pass),
        'CurrentATR': float(current_atr),
        'ThresholdATR': float(threshold),
        'AtrBarTime': bar_time,
        'RejectReason': None if atr_pass else 'ATR_REJECT',
    }


# ==========================================
# 4. Summary helpers
# ==========================================

def calc_summary(df, label):
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


def make_summary_tables(df_allowed, df_rejects):
    comparison_rows = []

    group_cols = ['EventScenario', 'AtrCondition']

    for (event_scenario, atr_condition), df_g in df_allowed.groupby(group_cols):
        label = f'{event_scenario} | {atr_condition}'
        row = calc_summary(df_g, label)
        row['EventScenario'] = event_scenario
        row['AtrCondition'] = atr_condition
        row['AllowedTrades'] = len(df_g)

        if df_rejects.empty:
            row['AtrRejects'] = 0
        else:
            row['AtrRejects'] = len(
                df_rejects[
                    (df_rejects['EventScenario'] == event_scenario) &
                    (df_rejects['AtrCondition'] == atr_condition)
                ]
            )

        comparison_rows.append(row)

    df_comparison = pd.DataFrame(comparison_rows)

    if not df_comparison.empty:
        df_comparison = df_comparison[
            [
                'EventScenario',
                'AtrCondition',
                'Trades',
                'AllowedTrades',
                'AtrRejects',
                'WinRate',
                'PF',
                'TotalPips',
                'MaxDD',
                'RoMD',
                'AvgPips',
            ]
        ].sort_values(['EventScenario', 'AtrCondition'])

    strategy_rows = []

    for (event_scenario, atr_condition, strategy), df_g in df_allowed.groupby(['EventScenario', 'AtrCondition', 'Strategy']):
        label = f'{event_scenario} | {atr_condition} | {strategy}'
        row = calc_summary(df_g, label)
        row['EventScenario'] = event_scenario
        row['AtrCondition'] = atr_condition
        row['Strategy'] = strategy

        if df_rejects.empty:
            row['AtrRejects'] = 0
        else:
            row['AtrRejects'] = len(
                df_rejects[
                    (df_rejects['EventScenario'] == event_scenario) &
                    (df_rejects['AtrCondition'] == atr_condition) &
                    (df_rejects['Strategy'] == strategy)
                ]
            )

        strategy_rows.append(row)

    df_strategy = pd.DataFrame(strategy_rows)

    if not df_strategy.empty:
        df_strategy = df_strategy[
            [
                'EventScenario',
                'AtrCondition',
                'Strategy',
                'Trades',
                'AtrRejects',
                'WinRate',
                'PF',
                'TotalPips',
                'MaxDD',
                'RoMD',
                'AvgPips',
            ]
        ].sort_values(['Strategy', 'EventScenario', 'AtrCondition'])

    pair_rows = []

    for (event_scenario, atr_condition, pair), df_g in df_allowed.groupby(['EventScenario', 'AtrCondition', 'Pair']):
        label = f'{event_scenario} | {atr_condition} | {pair}'
        row = calc_summary(df_g, label)
        row['EventScenario'] = event_scenario
        row['AtrCondition'] = atr_condition
        row['Pair'] = pair

        if df_rejects.empty:
            row['AtrRejects'] = 0
        else:
            row['AtrRejects'] = len(
                df_rejects[
                    (df_rejects['EventScenario'] == event_scenario) &
                    (df_rejects['AtrCondition'] == atr_condition) &
                    (df_rejects['Pair'] == pair)
                ]
            )

        pair_rows.append(row)

    df_pair = pd.DataFrame(pair_rows)

    if not df_pair.empty:
        df_pair = df_pair[
            [
                'EventScenario',
                'AtrCondition',
                'Pair',
                'Trades',
                'AtrRejects',
                'WinRate',
                'PF',
                'TotalPips',
                'MaxDD',
                'RoMD',
                'AvgPips',
            ]
        ].sort_values(['Pair', 'EventScenario', 'AtrCondition'])

    return df_comparison, df_strategy, df_pair


# ==========================================
# 5. Main ATR validation
# ==========================================

def run_atr_validation():
    df_event = load_event_v2_trade_log()

    df_event = df_event[df_event['EventScenario'].isin(EVENT_SCENARIOS_TO_TEST)].copy()

    if df_event.empty:
        raise ValueError(
            'No rows remain after filtering EVENT_SCENARIOS_TO_TEST. '
            f'Available scenarios: {sorted(load_event_v2_trade_log()["EventScenario"].unique())}'
        )

    atr_data = prepare_atr_data()

    allowed_rows = []
    reject_rows = []

    for condition in ATR_CONDITIONS:
        condition_name = condition['Condition']
        use_atr = condition['UseAtr']
        percentile = condition['Percentile']
        lookback = condition['Lookback']

        print('\n' + '=' * 80)
        print(f'▶ ATR Condition: {condition_name}')
        print('=' * 80)

        for _, row in df_event.iterrows():
            base_row = row.to_dict()
            base_row['AtrCondition'] = condition_name
            base_row['UseAtr'] = use_atr
            base_row['AtrPercentile'] = percentile
            base_row['AtrLookback'] = lookback

            if not use_atr:
                base_row['AtrPass'] = True
                base_row['CurrentATR'] = np.nan
                base_row['ThresholdATR'] = np.nan
                base_row['AtrBarTime'] = pd.NaT
                allowed_rows.append(base_row)
                continue

            eval_result = get_atr_eval(
                pair=row['Pair'],
                entry_time=row['EntryTime'],
                percentile=percentile,
                lookback=lookback,
                atr_data=atr_data
            )

            base_row['AtrAvailable'] = eval_result['AtrAvailable']
            base_row['AtrPass'] = eval_result['AtrPass']
            base_row['CurrentATR'] = eval_result['CurrentATR']
            base_row['ThresholdATR'] = eval_result['ThresholdATR']
            base_row['AtrBarTime'] = eval_result['AtrBarTime']
            base_row['AtrRejectReason'] = eval_result['RejectReason']

            if eval_result['AtrPass']:
                allowed_rows.append(base_row)
            else:
                reject_rows.append(base_row)

        print(f'Allowed rows so far: {len(allowed_rows):,}')
        print(f'Reject rows so far : {len(reject_rows):,}')

    df_allowed = pd.DataFrame(allowed_rows)
    df_rejects = pd.DataFrame(reject_rows)

    df_comparison, df_strategy, df_pair = make_summary_tables(df_allowed, df_rejects)

    return df_comparison, df_strategy, df_pair, df_allowed, df_rejects


# ==========================================
# 6. Run and save
# ==========================================

df_comparison, df_strategy, df_pair, df_allowed, df_rejects = run_atr_validation()

comparison_path = f'{OUTPUT_DIR}/ATRFilter_Comparison_Summary_v1_1.csv'
strategy_path = f'{OUTPUT_DIR}/ATRFilter_Strategy_Summary_v1_1.csv'
pair_path = f'{OUTPUT_DIR}/ATRFilter_Pair_Summary_v1_1.csv'
allowed_path = f'{OUTPUT_DIR}/ATRFilter_Allowed_Trades_v1_1.csv'
rejects_path = f'{OUTPUT_DIR}/ATRFilter_Rejects_v1_1.csv'

df_comparison.to_csv(comparison_path, index=False)
df_strategy.to_csv(strategy_path, index=False)
df_pair.to_csv(pair_path, index=False)
df_allowed.to_csv(allowed_path, index=False)
df_rejects.to_csv(rejects_path, index=False)

print('\n' + '=' * 80)
print('🏆 ATR Filter Comparison Summary v1.1')
print('=' * 80)
print(df_comparison.to_string(index=False))

print('\n' + '=' * 80)
print('✅ CSV保存完了')
print('=' * 80)
print(f'Comparison Summary : {comparison_path}')
print(f'Strategy Summary   : {strategy_path}')
print(f'Pair Summary       : {pair_path}')
print(f'Allowed Trades     : {allowed_path}')
print(f'Rejects            : {rejects_path}')
