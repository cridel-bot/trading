import os
import sys
import json
import pandas as pd

from datetime import datetime

# Ajouter les chemins
sys.path.append('./')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libraries.StrategyManager import StrategyManager

# Charger la liste des cryptos
with open('tokens.json', 'r') as f:
    cryptos = json.load(f)

def load_ohlcv_data(symbol, timeframe):
    path = f"/home/cridel/projects/trading/bot/python/database//bitget/{timeframe}/"
    filename = path + f"{symbol}.csv"
    data = pd.read_csv(filename)
    return data.values.tolist()

# Filtrer les données à partir de la date de début
def filter_data_from_date(data, start_date):
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    filtered_df = df[df['datetime'] >= pd.to_datetime(start_date)]
    return filtered_df.values.tolist()

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

# Simuler les trades et mesurer les performances
def backtest_strategy(data, initial_balance, risk, leverage,ema_fast,ema_slow):
    df = heikin_ashi_strategy(data,ema_fast,ema_slow)
    balance = initial_balance
    position = None
    entry_date = None
    trade_log = []
    start_date = None

    for i in range(len(df)):
        if i == 0:
            start_date = datetime.fromtimestamp(df['timestamp'].iloc[i] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            continue  # Skip the first row

        golong = (df['EMA_Fast'].iloc[i] > df['EMA_Slow'].iloc[i]) and (df['MACD_Line'].iloc[i] > df['Signal_Line'].iloc[i])
        goshort = (df['EMA_Fast'].iloc[i] < df['EMA_Slow'].iloc[i]) and (df['MACD_Line'].iloc[i] < df['Signal_Line'].iloc[i])

        if position == "long" and goshort:
            exit_price = df['HA_Close'].iloc[i]
            position_size_usd = position_size
            position_size_asset = position_size / entry_price
            profit_loss = position_size * (exit_price / entry_price - 1)
            balance += profit_loss
            trade_log.append({
                'position': 'long', 
                'entry_date': datetime.fromtimestamp(entry_date / 1000).strftime('%Y-%m-%d %H:%M:%S'), 
                'exit_date': datetime.fromtimestamp(df['timestamp'].iloc[i] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'entry': entry_price, 'exit': exit_price, 'size_usd': position_size_usd, 
                'size_asset': position_size_asset, 'balance': balance, 'profit_loss': profit_loss
            })
            position = None
        elif position == "short" and golong:
            exit_price = df['HA_Close'].iloc[i]
            position_size_usd = position_size
            position_size_asset = position_size / entry_price
            profit_loss = position_size * (1 - exit_price / entry_price)
            balance += profit_loss
            trade_log.append({
                'position': 'short', 
                'entry_date': datetime.fromtimestamp(entry_date / 1000).strftime('%Y-%m-%d %H:%M:%S'), 
                'exit_date': datetime.fromtimestamp(df['timestamp'].iloc[i] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'entry': entry_price, 'exit': exit_price, 'size_usd': position_size_usd, 
                'size_asset': position_size_asset, 'balance': balance, 'profit_loss': profit_loss
            })
            position = None
        
        if position is None:
            position_size = balance * (risk / 100) * leverage
            if golong:
                position = "long"
                entry_date = df['timestamp'].iloc[i]
                entry_price = df['HA_Close'].iloc[i]
            elif goshort:
                position = "short"
                entry_date = df['timestamp'].iloc[i]
                entry_price = df['HA_Close'].iloc[i]
    
    return balance, trade_log, start_date

# Fonction pour sauvegarder les trades dans un fichier CSV
def save_trades_to_csv(data, symbol, timeframe,path):
    # Créer le répertoire s'il n'existe pas
    os.makedirs(path, exist_ok=True)
    
    # Générer le nom du fichier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{timeframe}_{timestamp}.csv"
    filename = filename.replace('/','_')
    full_path = os.path.join(path, filename)
    
    # Sauvegarder le DataFrame en CSV
    data.to_csv(full_path, index=False)
    print(f"Trades sauvegardés dans {full_path}")

# Fonction pour résumer le backtest
def summarize_backtest(trade_log, start_date):
    total_trades = len(trade_log)
    winning_trades = len([trade for trade in trade_log if trade['profit_loss'] > 0])
    losing_trades = total_trades - winning_trades
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    max_drawdown = min(trade['balance'] for trade in trade_log) if trade_log else 0
    max_drawdown_pct = (initial_balance - max_drawdown) / initial_balance * 100 if trade_log else 0
    best_trade = max(trade_log, key=lambda x: x['profit_loss']) if trade_log else {}
    worst_trade = min(trade_log, key=lambda x: x['profit_loss']) if trade_log else {}

    summary = {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'max_drawdown': initial_balance - max_drawdown if trade_log else 0,
        'max_drawdown_pct': max_drawdown_pct if trade_log else 0,
        'best_trade': best_trade,
        'worst_trade': worst_trade,
        'start_date': start_date
    }
    
    return summary

# Fonction pour résumer le backtest mensuellement
def summarize_monthly_backtest(trade_log):
    monthly_summary = {}
    
    for trade in trade_log:
        date = datetime.strptime(trade['entry_date'], '%Y-%m-%d %H:%M:%S')
        month_year = date.strftime('%Y-%m')
        
        if month_year not in monthly_summary:
            monthly_summary[month_year] = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_loss': 0
            }
        
        monthly_summary[month_year]['total_trades'] += 1
        monthly_summary[month_year]['profit_loss'] += trade['profit_loss']
        if trade['profit_loss'] > 0:
            monthly_summary[month_year]['winning_trades'] += 1
        else:
            monthly_summary[month_year]['losing_trades'] += 1
        
        monthly_summary[month_year]['win_rate'] = (monthly_summary[month_year]['winning_trades'] / 
                                                   monthly_summary[month_year]['total_trades']) * 100
    
    # Convertir le dictionnaire en DataFrame pour un affichage tabulaire
    monthly_df = pd.DataFrame.from_dict(monthly_summary, orient='index')
    monthly_df.index.name = 'Mois'
    monthly_df.reset_index(inplace=True)
    monthly_df = monthly_df[['Mois', 'total_trades', 'winning_trades', 'losing_trades', 'win_rate', 'profit_loss']]
    
    return monthly_df

initial_balance = 96  # Solde initial
display_trades = False
start_date_param = "2022-01-01"  # Exemple de date de début, à remplacer par le paramètre réel

for crypto in cryptos:
    symbol = crypto['symbol']
    timeframe = crypto['timeframe']
    risk = crypto['risk']
    leverage = crypto['levier']
    ema_fast = crypto["ema_fast"]
    ema_slow = crypto["ema_slow"]
    
    print(f"Traitement du token {symbol} pour la Timeframe {timeframe}")

    # Charger les données OHLCV depuis un fichier ou autre source
    data = load_ohlcv_data(symbol, timeframe)

    # Filtrer les données à partir de la date de début
    #if start_date_param:
    #    data = filter_data_from_date(data, start_date_param)

    final_balance, trade_log, start_date = backtest_strategy(data, initial_balance, risk, leverage,ema_fast,ema_slow)
    summary = summarize_backtest(trade_log, start_date)
    monthly_summary = summarize_monthly_backtest(trade_log)
    
    if(display_trades):
        print("Journal des trades:")
        for trade in trade_log:
            print(trade)
    
    print(f"\nRésumé du backtest: {symbol}-{timeframe}")
    print(f"Date de début: {summary['start_date']}")
    print(f"Blance initiale : {initial_balance} USDT")
    print(f"Balance finale : {final_balance} USDT")
    print(f"Nombre total de trades: {summary['total_trades']}")
    print(f"Nombre de trades gagnants: {summary['winning_trades']}")
    print(f"Nombre de trades perdants: {summary['losing_trades']}")
    print(f"Winrate: {summary['win_rate']:.2f}%")
    print(f"Max Drawdown: {summary['max_drawdown']} USDT")
    print(f"Max Drawdown (%): {summary['max_drawdown_pct']:.2f}%")
    print("\nMeilleur Trade:")
    print(f"Position: {summary['best_trade'].get('position', 'N/A')}")
    print(f"Date d'entrée: {summary['best_trade'].get('entry_date', 'N/A')}")
    print(f"Prix d'entrée: {summary['best_trade'].get('entry', 'N/A')}")
    print(f"Date de sortie: {summary['best_trade'].get('exit_date', 'N/A')}")
    print(f"Prix de sortie: {summary['best_trade'].get('exit', 'N/A')}")
    print(f"Taille (USD): {summary['best_trade'].get('size_usd', 'N/A')}")
    print(f"Bénéfice/Pertes: {summary['best_trade'].get('profit_loss', 'N/A')} USDT")
    
    print("\nPire Trade:")
    print(f"Position: {summary['worst_trade'].get('position', 'N/A')}")
    print(f"Date d'entrée: {summary['worst_trade'].get('entry_date', 'N/A')}")
    print(f"Prix d'entrée: {summary['worst_trade'].get('entry', 'N/A')}")
    print(f"Date de sortie: {summary['worst_trade'].get('exit_date', 'N/A')}")
    print(f"Prix de sortie: {summary['worst_trade'].get('exit', 'N/A')}")
    print(f"Taille (USD): {summary['worst_trade'].get('size_usd', 'N/A')}")
    print(f"Bénéfice/Pertes: {summary['worst_trade'].get('profit_loss', 'N/A')} USDT")
    
    print("\nRésumé Mensuel du Backtest:")
    print(monthly_summary.to_string(index=False))