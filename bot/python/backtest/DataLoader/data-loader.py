import sys
import os
import pandas as pd

# Ajouter les chemins
sys.path.append('./')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from libraries.DataManager import ExchangeDataManager

exchange_name = "bitget"
intervals = ["15m","30m","1h", "2h", "4h"]
coin_to_dl = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "ADA/USDT:USDT",
    "TAO/USDT:USDT",
    "EGLD/USDT:USDT",
    "RUNE/USDT:USDT",
    "ONDO/USDT:USDT",
    "INJ/USDT:USDT",
    "IO/USDT:USDT",
    ]

path="/home/cridel/projects/trading/bot/python/database/"

exchange = ExchangeDataManager(
    exchange_name=exchange_name, path_download=path
)

async def main():
    await exchange.download_data(
        coins=coin_to_dl,
        intervals=intervals,
    )

# Exécuter la fonction asynchrone
import asyncio
asyncio.run(main())
