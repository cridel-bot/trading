import asyncio
from posixpath import dirname
from pathlib import Path
import ccxt.async_support as ccxt
import pytz
import pandas as pd
import os
from datetime import datetime, timedelta
from tqdm.auto import tqdm
from asyncio import Semaphore

class Utils:
        
        def __init__(self, process_name) -> None:
                self.process_name = process_name.lower()

        # Fonction pour sauvegarder les trades dans un fichier CSV
        def save_trades_to_csv(self,data, symbol, timeframe,path):
            # Créer le répertoire s'il n'existe pas
            os.makedirs(path, exist_ok=True)
            
            # Générer le nom du fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_{timeframe}_{timestamp}.csv"
            filename = filename.replace('/','_')
            full_path = os.path.join(path, filename)
            
            # Sauvegarder le DataFrame en CSV
            data.to_csv(full_path, index=False)
            print(f"Data sauvegardés dans {full_path}")

        def load_ohlcv_data(self,symbol, path, timeframe):
                final_path = f"{path}{timeframe}/"
                filename = final_path + f"{symbol}.csv"
                data = pd.read_csv(filename)
                return data.values
        
        # Filtrer les données à partir de la date de début
        def filter_data_from_date(self, data, start_date):
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            filtered_df = df[df['datetime'] >= pd.to_datetime(start_date)]
            return filtered_df
        
        def add_readble_date_to_dataframe(self,df, date_column_name):
              df['readable_date'] = pd.to_datetime(df[date_column_name], unit='ms')
              return df