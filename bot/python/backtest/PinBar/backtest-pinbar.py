import os
import sys
import json
import pandas as pd

from datetime import datetime

# Ajouter les chemins
sys.path.append('./')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from libraries.StrategyManager import StrategyManager
from libraries.utils import Utils
from libraries.trading_utils import TradingUtils

# Charger la liste des cryptos
with open('tokens.json', 'r') as f:
    cryptos = json.load(f)

# Calculer l'EMA
def calculate_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

# Stratégie Heikin Ashi
def heikin_ashi_strategy(data,ema_fast,ema_slow):
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df['HA_Open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    df.iat[0, df.columns.get_loc('HA_Open')] = df.iat[0, df.columns.get_loc('open')]

    df['HA_High'] = df[['HA_Open', 'HA_Close', 'high']].max(axis=1)
    df['HA_Low'] = df[['HA_Open', 'HA_Close', 'low']].min(axis=1)
    
    # Calcul des EMA
    df['EMA_Fast'] = calculate_ema(df['HA_Close'], ema_fast)  # Vous pouvez ajuster la période de l'EMA rapide
    df['EMA_Slow'] = calculate_ema(df['HA_Close'], ema_slow)  # Vous pouvez ajuster la période de l'EMA lente

    # Calcul du MACD
    ema12 = calculate_ema(df['HA_Close'], 12)
    ema26 = calculate_ema(df['HA_Close'], 26)
    df['MACD_Line'] = ema12 - ema26
    df['Signal_Line'] = calculate_ema(df['MACD_Line'], 9)
    
    return df


def enhanced_dataframe_strategy(data, sma_slow, ema_medium, ema_fast):
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    df['SMA_Slow'] = trading.sma(df['close'], sma_slow)
    df['EMA_Medium'] = trading.ema(df['close'], ema_medium)
    df['EMA_Fast'] = trading.ema(df['close'], ema_fast)

    df['BullishPinbar'] = ((df['close'] > df['open']) & ((df['open'] - df['low']) > 0.66 * (df['high'] - df['low']))) | ((df['close'] < df['open']) & ((df['close'] - df['low']) > 0.66 * (df['high'] - df['low'])))
    df['BearishPinbar'] = ((df['close'] > df['open']) & ((df['high'] - df['close']) > 0.66 * (df['high'] - df['low']))) | ((df['close'] < df['open']) & ((df['high'] - df['open']) > 0.66 * (df['high'] - df['low'])))

    # Specify Trend Conditions
    df['fanUpTrend'] = (df['EMA_Fast'] > df['EMA_Medium']) & (df['EMA_Medium'] > df['SMA_Slow'])
    df['fanDnTrend'] = (df['EMA_Fast'] < df['EMA_Medium']) & (df['EMA_Medium'] < df['SMA_Slow'])

    # Specify Piercing Conditions  
    df['bullPierce'] = ((df['low'] < df['EMA_Fast']) & (df['open'] > df['EMA_Fast']) & (df['close'] > df['EMA_Fast'])) | ((df['low'] < df['EMA_Medium']) & (df['open'] > df['EMA_Medium']) & (df['close'] > df['EMA_Medium'])) | ((df['low'] < df['SMA_Slow']) & (df['open'] > df['SMA_Slow']) & (df['close'] > df['SMA_Slow']))
    df['bearPierce'] = ((df['high'] > df['EMA_Fast']) & (df['open'] < df['EMA_Fast']) & (df['close'] < df['EMA_Fast'])) | ((df['high'] > df['EMA_Medium']) & (df['open'] < df['EMA_Medium']) & (df['close'] < df['EMA_Medium'])) | ((df['high'] > df['SMA_Slow']) & (df['open'] < df['SMA_Slow']) & (df['close'] < df['SMA_Slow']))

    # Specify Entry Conditions
    df['long_entry'] = df['fanUpTrend'] & df['BullishPinbar'] & df['bullPierce']
    df['short_entry'] = df['fanDnTrend'] & df['BearishPinbar'] & df['bearPierce']

    return df

# Simuler les trades et mesurer les performances
def backtest_strategy(data,
                        initial_balance,
                        risk, leverage,
                        sma_slow,
                        ema_medium,
                        ema_fast,
                        symbol,
                        timeframe):
    

    #df = heikin_ashi_strategy(data,ema_fast,sma_slow)
    df = enhanced_dataframe_strategy(data, sma_slow, ema_medium, ema_fast)
    utils.save_trades_to_csv(df, symbol, timeframe, "/home/cridel/projects/trading/bot/python/backtest/PinBar/dataframe/")

    balance = initial_balance
    position = None
    entry_date = None
    trade_log = []
    start_date = None

    # Paramètres utilisateur
    usr_risk = 3  # pourcentage de risque de l'équité
    atr_mult = 0.5  # Stop Loss x ATR
    slPoints = 1  # Stop Loss Trail Points (Pips)
    slOffset = 1  # Stop Loss Trail Offset (Pips)
    sma_slow = 50  # Période SMA lente
    ema_medm = 18  # Période EMA moyenne
    ema_fast = 6  # Période EMA rapide
    atr_valu = 14  # Période ATR    

    for i in range(len(df)):
        if i == 0:
            start_date = datetime.fromtimestamp(df['timestamp'].iloc[i] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            continue  # Skip the first row
        
        golong = df['long_entry'].iloc[i]
        goshort = df['short_entry'].iloc[i]
        
        if position == "long":
            exit_price = df['close'].iloc[i]
            high_price = df['high'].iloc[i]
            low_price = df['low'].iloc[i]

            tp_price = entry_price * (1 + (0.02 * 2))
            sl_price = entry_price * (1 - 0.05)
            
            if goshort or high_price >= tp_price or low_price <= sl_price:

                if(high_price >= tp_price):
                    exit_price = tp_price
                if(low_price <= sl_price):
                    exit_price = sl_price

                position_size_usd = position_size
                position_size_asset = position_size / entry_price
                profit_loss = position_size * (exit_price / entry_price - 1)
                balance += profit_loss

                strategy.add_trade_log('long', 
                                       entry_date, 
                                       df['timestamp'].iloc[i], 
                                       entry_price, 
                                       exit_price, 
                                       position_size_usd, 
                                       position_size_asset, 
                                       balance, profit_loss,
                                       tp_price,
                                       sl_price)
                position = None
        
        elif position == "short":
            exit_price = df['close'].iloc[i]
            tp_price = entry_price * (1 - 1.5 * (risk / 100))
            sl_price = entry_price * (1 + (risk / 100))
            
            if golong or exit_price <= tp_price or exit_price >= sl_price:
                position_size_usd = position_size
                position_size_asset = position_size / entry_price
                profit_loss = position_size * (1 - exit_price / entry_price)
                balance += profit_loss
                strategy.add_trade_log('short', 
                                       entry_date, 
                                       df['timestamp'].iloc[i], 
                                       entry_price, 
                                       exit_price, 
                                       position_size_usd, 
                                       position_size_asset, 
                                       balance, 
                                       profit_loss,
                                       tp_price,
                                       sl_price)
                position = None
        
        if position is None:
            position_size = balance * (risk / 100) * leverage
            if golong:
                position = "long"
                entry_date = df['timestamp'].iloc[i]
                entry_price = df['close'].iloc[i]
            elif goshort:
                position = "short"
                entry_date = df['timestamp'].iloc[i]
                entry_price = df['close'].iloc[i]    
    
    return balance, trade_log, start_date

utils = Utils("backtest-pinbar")
strategy = StrategyManager("backtest-pinbar")
trading = TradingUtils("backtest-pinbar")

initial_balance = 96  # Solde initial
save_trades = True
start_date_param = "2025-02-01"  # Exemple de date de début, à remplacer par le paramètre réel

for crypto in cryptos:
    symbol = crypto['symbol']
    timeframe = crypto['timeframe']
    risk = crypto['risk']
    leverage = crypto['levier']

    sma_slow = crypto["sma_slow"]
    ema_medium = crypto["ema_medium"]
    ema_fast = crypto["ema_fast"]
    
    print(f"Traitement du token {symbol} pour la Timeframe {timeframe}")

    # Charger les données OHLCV depuis un fichier ou autre source
    data = utils.load_ohlcv_data(symbol,"/home/cridel/projects/trading/bot/python/database//bitget/",timeframe )

    # Filtrer les données à partir de la date de début
    if start_date_param:
        data = utils.filter_data_from_date(data, start_date_param)

    final_balance, trade_log, start_date = backtest_strategy(data, 
                                                             initial_balance, 
                                                             risk, leverage,
                                                             sma_slow,
                                                             ema_medium,
                                                             ema_fast,
                                                             symbol,
                                                             timeframe)
    
    if(save_trades):
        strategy.save_trades(symbol, timeframe, "/home/cridel/projects/trading/bot/python/backtest/PinBar/trades/")
    
    summary = strategy.summarize_backtest(start_date, initial_balance)
    monthly_summary = strategy.summarize_monthly_backtest()

    strategy.display_summary(symbol, timeframe, initial_balance, final_balance, summary)
    strategy.display_best_trade(summary)
    strategy.display_worst_trade(summary)
    strategy.display_monthly_summary(monthly_summary)
