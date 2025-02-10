import asyncio
from posixpath import dirname
from pathlib import Path
import ccxt.async_support as ccxt
import pytz
import pandas as pd
import pandas_ta as ta
import os
from datetime import datetime, timedelta
from tqdm.auto import tqdm
from asyncio import Semaphore

class TradingUtils:

    def __init__(self, process_name) -> None:
        self.process_name = process_name.lower()

    def ema(self,price, period):
        return ta.ema(price, period)

    def sma(self,price, period):
        return ta.sma(price, period)
    
    