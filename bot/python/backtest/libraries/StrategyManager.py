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


class StrategyManager:
        
        def __init__(self, exchange_name, path_download="./") -> None:
                self.exchange_name = exchange_name.lower()
