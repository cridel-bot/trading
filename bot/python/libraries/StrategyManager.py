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
from libraries.utils import Utils


class StrategyManager:
        
        def __init__(self, initial_balance) -> None:
                self.initial_balance = initial_balance
                self.trade_log = []
                self.summaries_backtest = []
                self.utils = Utils("strategy-manager")

        def clear_trade_log(self):
                self.trade_log = []

        # Fonction pour résumer le backtest
        def summarize_backtest(self, start_date, initial_balance):
                total_trades = len(self.trade_log)
                winning_trades = len([trade for trade in self.trade_log if trade['profit_loss'] > 0])
                losing_trades = total_trades - winning_trades
                win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
                max_drawdown = min(trade['balance'] for trade in self.trade_log) if self.trade_log else 0
                max_drawdown_pct = (initial_balance - max_drawdown) / initial_balance * 100 if self.trade_log else 0
                best_trade = max(self.trade_log, key=lambda x: x['profit_loss']) if self.trade_log else {}
                worst_trade = min(self.trade_log, key=lambda x: x['profit_loss']) if self.trade_log else {}

                summary = {
                        'total_trades': total_trades,
                        'winning_trades': winning_trades,
                        'losing_trades': losing_trades,
                        'win_rate': win_rate,
                        'max_drawdown': initial_balance - max_drawdown if self.trade_log else 0,
                        'max_drawdown_pct': max_drawdown_pct if self.trade_log else 0,
                        'best_trade': best_trade,
                        'worst_trade': worst_trade,
                        'start_date': start_date
                }
        
                return summary
        
        # Fonction pour résumer le backtest mensuellement
        def summarize_monthly_backtest(self):
                monthly_summary = {}
                
                for trade in self.trade_log:
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

        # Filtrer les données à partir de la date de début
        def filter_data_from_date(self,data, start_date):
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                filtered_df = df[df['datetime'] >= pd.to_datetime(start_date)]
                return filtered_df.values.tolist()
       
        def add_summary_backtest_entry(self, backtest_parameters, initial_balance, final_balance, total_trades, winning_trades, losing_trades, win_rate, max_drawdown, max_drawdown_pct):
                pct_rendement = ((final_balance / initial_balance) - 1 ) * 100
                self.summaries_backtest.append({
                        'backtest_parameters' : backtest_parameters,
                        'initial_balance' : initial_balance,
                        'final_balance' : final_balance,
                        'total_trades' : total_trades,
                        'winninf_trades' : winning_trades,
                        'losing_trades': losing_trades,
                        'win_rate' : win_rate,
                        'max_drawdown' : max_drawdown,
                        'max_drawdown_pct' : max_drawdown_pct,
                        'pct_rendement' : pct_rendement
                })

        def display_summary(self, symbol, timeframe, initial_balance, final_balance, summary):
                pct_rendement = ((final_balance / initial_balance) - 1 ) * 100
                print(f"\nRésumé du backtest: {symbol}-{timeframe}")
                print(f"Date de début: {summary['start_date']}")
                print(f"Blance initiale : {initial_balance} USDT")
                print(f"Balance finale : {final_balance} USDT")
                print(f"Rendement : {pct_rendement:.2f}%")
                print(f"Nombre total de trades: {summary['total_trades']}")
                print(f"Nombre de trades gagnants: {summary['winning_trades']}")
                print(f"Nombre de trades perdants: {summary['losing_trades']}")
                print(f"Winrate: {summary['win_rate']:.2f}%")
                print(f"Max Drawdown: {summary['max_drawdown']} USDT")
                print(f"Max Drawdown (%): {summary['max_drawdown_pct']:.2f}%")                

        def display_best_trade(self, summary):
                print("\nMeilleur Trade:")
                print(f"Position: {summary['best_trade'].get('position', 'N/A')}")
                print(f"Date d'entrée: {summary['best_trade'].get('entry_date', 'N/A')}")
                print(f"Prix d'entrée: {summary['best_trade'].get('entry', 'N/A')}")
                print(f"Date de sortie: {summary['best_trade'].get('exit_date', 'N/A')}")
                print(f"Prix de sortie: {summary['best_trade'].get('exit', 'N/A')}")
                print(f"Taille (USD): {summary['best_trade'].get('size_usd', 'N/A')}")
                print(f"Bénéfice/Pertes: {summary['best_trade'].get('profit_loss', 'N/A')} USDT")

        def display_worst_trade(self, summary):
                print("\nPire Trade:")
                print(f"Position: {summary['worst_trade'].get('position', 'N/A')}")
                print(f"Date d'entrée: {summary['worst_trade'].get('entry_date', 'N/A')}")
                print(f"Prix d'entrée: {summary['worst_trade'].get('entry', 'N/A')}")
                print(f"Date de sortie: {summary['worst_trade'].get('exit_date', 'N/A')}")
                print(f"Prix de sortie: {summary['worst_trade'].get('exit', 'N/A')}")
                print(f"Taille (USD): {summary['worst_trade'].get('size_usd', 'N/A')}")
                print(f"Bénéfice/Pertes: {summary['worst_trade'].get('profit_loss', 'N/A')} USDT")

        def display_monthly_summary(self, monthly_summary):
                print("\nRésumé Mensuel du Backtest:")
                print(monthly_summary.to_string(index=False))

        def display_trades(self):
                print("Journal des trades:")
                for trade in self.trade_log:
                        print(trade) 

        def save_trades(self, symbol, timeframe, path):
                df = pd.DataFrame(self.trade_log, columns=['position', 'entry_date', 'exit_date', 'entry', 'exit', 'size_usd', 'tp', 'sl', 'size_asset', 'balance', 'profit_loss'])
                self.utils.save_trades_to_csv(df, symbol, timeframe, path)

        def add_trade_log(self, 
                          position, 
                          entry_date, 
                          exit_date, 
                          entry_price, 
                          exit_price, 
                          position_size_usd, 
                          position_size_asset, 
                          balance, 
                          profit_loss,
                          tp_price=None,
                          sl_price=None):
            
                self.trade_log.append({
                        'position': position, 
                        'entry_date': datetime.fromtimestamp(entry_date / 1000).strftime('%Y-%m-%d %H:%M:%S'), 
                        'exit_date': datetime.fromtimestamp(exit_date / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                        'entry': entry_price, 
                        'exit': exit_price, 
                        'size_usd': position_size_usd, 
                        'tp' : tp_price, 
                        'sl' : sl_price,
                        'size_asset': position_size_asset, 
                        'balance': balance, 
                        'profit_loss': profit_loss                
                })

