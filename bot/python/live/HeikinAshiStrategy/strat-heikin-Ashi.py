import sys
import os
import json
import traceback
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime

# Ajouter les chemins
sys.path.append('./')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from libraries.perp_bitget import PerpBitget as Exchange


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

try:
    production = True
    display_data = True

    # Charger la liste des cryptos
    with open('tokens.json', 'r') as f:
        cryptos = json.load(f)

    start_time = datetime.now()
    print(f"------------- Start Heikin Ashin strategy at {start_time} ")

    # Initialiser le client CCXT
    with open('secret.json', 'r') as f:
        config = json.load(f)

    account_to_select = 'bg_has'
    exchange = Exchange(
    apiKey=config[account_to_select]["apiKey"],
    secret=config[account_to_select]["secret"],
    password=config[account_to_select]["password"])

    balance = float(exchange.get_usdt_equity())
    print(f"Solde du compte : {balance} USDT")

    # Boucle principale pour parcourir les cryptos et exécuter la stratégie
    for crypto in cryptos:
        symbol = crypto['symbol']
        timeframe = crypto['timeframe']
        levier= crypto["levier"]
        risk=crypto["risk"]
        ema_fast = crypto["ema_fast"]
        ema_slow = crypto["ema_slow"]

        doSomething = True
            
        print(f"Traitement du token {symbol} pour la Timeframe {timeframe}")

        # Récupérer les données OHLCV
        # Changement temporaire de symbole pour aller prendre le prix "Futures"
        symbol_future = symbol + ":USDT"

        # Get last 6 months of data
        maintenant = datetime.now()
        # Calculer le nombre total de minutes depuis minuit
        total_minutes = maintenant.hour * 60 + maintenant.minute
        # Arrondir au quart d'heure inférieur
        minutes_arrondies = total_minutes - (total_minutes % 15)
        # Obtenir la nouvelle heure arrondie
        nouvelle_heure = maintenant.replace(hour=minutes_arrondies // 60, minute=minutes_arrondies % 60, second=0, microsecond=0)

        print(f"Heure : {nouvelle_heure}")
        nouvelle_heure = nouvelle_heure - relativedelta(months=6)
        print(f"Heure : {nouvelle_heure}")

        date_from = nouvelle_heure

        # Convertir la date en timestamp
        since_date = date_from.timestamp()

        data = exchange.fetch_ohlcv_wrapped(symbol= symbol_future, timeframe = timeframe,limit= 3000)

        # Appliquer la stratégie Heikin Ashi
        df = heikin_ashi_strategy(data,ema_fast,ema_slow)

        first_candle_date = datetime.fromtimestamp(data[0][0] / 1000)  # Convertir le timestamp en datetime
        last_candle_date = datetime.fromtimestamp(data[-1][0] / 1000)  # Convertir le timestamp en datetime
        first_candle_open = df['open'].iloc[0]
        last_candle_open = df['open'].iloc[-1]
        first_candle_close = df['close'].iloc[0]
        last_candle_close = df['close'].iloc[-1]

        # Afficher les dates de manière lisible
        print(f"Date de la première bougie : {first_candle_date.strftime('%Y-%m-%d %H:%M:%S')} - Open : {first_candle_open} - Close : {first_candle_close}")
        print(f"Date de la dernière bougie : {last_candle_date.strftime('%Y-%m-%d %H:%M:%S')} - Open : {last_candle_open} - Close : {last_candle_close}")

        if(display_data):
            df['readable_date'] = pd.to_datetime(df['timestamp'], unit='ms')
            save_trades_to_csv(df,symbol,timeframe,"/home/cridel/projects/trading/bot/python/live/HeikinAshiStrategy/dataframe/")

        # As t'on des positions short/longs pour le token en cours
        buy_orders = []
        sell_orders = []
        orders = exchange.fetch_position_thicker(symbol)

        for order in orders:
            t = order["side"]
            if order["side"] == "long":
                buy_orders.append(order)
            elif order["side"] == "short":
                sell_orders.append(order)

        has_long_orders = len(buy_orders) > 0
        has_short_orders = len(sell_orders) > 0

        print(f"Ordre long déja actif pour la paire {symbol} : {has_long_orders}")
        print(f"Ordre short déja actif pour la paire {symbol} : {has_short_orders}")

        # Conditions d'entrée et de sortie
        golong = (df['EMA_Fast'].iloc[-1] > df['EMA_Slow'].iloc[-1]) and (df['MACD_Line'].iloc[-1] > df['Signal_Line'].iloc[-1]) and has_long_orders == False
        goshort = (df['EMA_Fast'].iloc[-1] < df['EMA_Slow'].iloc[-1]) and (df['MACD_Line'].iloc[-1] < df['Signal_Line'].iloc[-1]) and has_short_orders == False
        
        print(f"Condition Long : {golong}")
        print(f"Condition Short : {goshort}")

        # Si nous avons un long en cours et que l'action est d'ouvrir un long alors nous ne faisons rien
        if(has_long_orders and golong):
            doSomething = False
        # Si nous avons un short en cours et que l'action est d'ouvrir un short alors nous ne faisons rien
        if(has_short_orders and goshort):
            doSomething = False
        if(golong == False and goshort == False):
            doSomething = False

        if(doSomething==False):
            print("Pas d'actions a entreprendre")
        else:
            if (golong or goshort):
                print(f"Fermeture des positions pour {symbol}")
                exchange.close_open_positions(symbol, with_retry=True)  # Fermer les positions courtes ouvertes avant d'ouvrir une position longue

            # Calcul de la taille de position
            position_size = float(balance  * (risk/100) * levier)
            prices = exchange.get_bid_ask_price(symbol)
            amount_symbol = float(position_size / prices["bid"])

            # Exécuter les trades en fonction des conditions
            if golong:
                print(f"Ouverture d'une position longue pour {symbol}/{timeframe} - Taille de la position : {position_size}$ ({amount_symbol} {symbol})")
                if(production):
                    exchange.place_market_order_direct(symbol + ":USDT", "buy", amount_symbol)  # Achat
            elif goshort:
                print(f"Ouverture d'une position short pour {symbol}/{timeframe} - Taille de la position : {position_size}$ ({amount_symbol} {symbol})")
                if(production):
                    exchange.place_market_order_direct(symbol + ":USDT", "sell", amount_symbol)  # Vente
        
        end_time = datetime.now()
        print(f"------------- End Heikin Ashin strategy at {end_time} ")
   
except Exception as e:
        print(f"Erreur lors de l'éxécution du script' : {e}")
        traceback.print_exc()
        end_time = datetime.now()
        print(f"------------- End Heikin Ashin strategy at {end_time} ")

