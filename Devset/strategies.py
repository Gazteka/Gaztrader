import pandas as pd
import numpy as np
import json
import os
import datetime
import sqlite3
import matplotlib.pyplot as plt
import time

def cret(data, last_row=False):
    df = ((1+data).cumprod(axis=0)-1)
    if last_row:
        return df.iloc[-1]
    return df

def sharpe_ratio(serie):
    mean = serie.mean()
    std = serie.std()
    return mean/std

def timer(funcion):
    """
    Se crea un decorador (googlear) del tipo timer para testear el tiempo
    de ejecucion del programa
    """
    def inner(*args, **kwargs):

        inicio = time.time()
        resultado = funcion(*args, **kwargs)
        final = round(time.time() - inicio, 3)
        print("\nTiempo de ejecucion total: {}[s]".format(final))

        return resultado
    return inner


class DataHandler:
    def __init__(self,database_file):
        self.database_file = database_file
        self.conn = sqlite3.connect(database_file,check_same_thread= False)
        self.cursor = self.conn.cursor()
        print("Conectado a la base de datos")
    def get_all(self,timeframe = "1d"):
        self.cursor.execute(f"SELECT *  FROM crypto_prices_binance WHERE crypto_prices_binance.timeframe = '{timeframe}' ")
        data = self.cursor.fetchall()
        df = pd.DataFrame(data)
        if df.shape[1] == 12:
            print("Futures")
            df = df.drop([0,2,3,4],axis = 1)
            df.columns = ["symbol","open_time","open","high","low","close","volume","close_time"]
            
            df["open_time"] == pd.to_datetime(df["open_time"])
            df["close_time"] == pd.to_datetime(df["close_time"])
            df.index = df["open_time"]
            dic_data ={}
            symbols = set(df["symbol"])
            for symbol in symbols:
                dic_data[symbol] = df[df["symbol"] == symbol]
            return dic_data
        elif df.shape[1] == 15:
            print("Spot")
    @timer
    def get_local(self,timeframe,limit = 15000):
        self.cursor.execute(f"""SELECT *  FROM crypto_prices_binance WHERE crypto_prices_binance.timeframe = '{timeframe}'
        ORDER BY open_time DESC LIMIT {limit} """)
        data = self.cursor.fetchall()
        df = pd.DataFrame(data)
        if df.shape[1] == 12:
            print("Futures")
            df = df.drop([0,2,3,4],axis = 1)
            df.columns = ["symbol","open_time","open","high","low","close","volume","close_time"]
            df = df.iloc[::-1]
            df["open_time"] == pd.to_datetime(df["open_time"])
            df["close_time"] == pd.to_datetime(df["close_time"])
            df.index = df["open_time"]
            dic_data ={}
            symbols = set(df["symbol"])
            for symbol in symbols:
                dic_data[symbol] = df[df["symbol"] == symbol]
            return dic_data
        elif df.shape[1] == 15:
            print("Spot")
    @timer
    def get_live(self,timeframe,limit = 15000):
        self.cursor.execute(f"""SELECT open_time,crypto_symbol,close,close_time  FROM crypto_prices_binance WHERE crypto_prices_binance.timeframe = '{timeframe}'
        ORDER BY open_time DESC LIMIT {limit} """)
        data = self.cursor.fetchall()
        df = pd.DataFrame(data)
        df.columns = ["open_time","symbol","close","close_time"]
        df = df.iloc[::-1]
        df["open_time"] == pd.to_datetime(df["open_time"])
        df["close_time"] == pd.to_datetime(df["close_time"])

        df.index = df["open_time"]
        dic_data ={}
        symbols = set(df["symbol"])
        for symbol in symbols:
            dic_data[symbol] = df[df["symbol"] == symbol]
        return dic_data
class Strategy:

    def __init__(self):
        self.name = "Base Strategy"
        self.timeframe = "15m"

        self.risk_management = {"pos_sizing":0.25,"take_profit":0.05,"stop_loss":0.005,"leverage":1}
        self.max_posiciones = 3
        

    def math(self,dataset):
        for symbol in dataset:
            dataset[symbol]["30_mm"] = dataset[symbol]["close"].rolling(30).mean()
            dataset[symbol]["60_mm"] = dataset[symbol]["close"].rolling(60).mean()


        self.dataset = dataset
        return dataset
    def operar(self,timestamp,portafolio):
        print("Operando",timestamp)
        pass
    def check_entries(self,timestamp,data,portafolio):
        candidatos = []
        espacios_disponibles = self.get_available_spaces(portafolio)
        if espacios_disponibles == 0:
            return []

        for symbol in data:
            try:
                short_mm_value = data[symbol].loc[timestamp]["30_mm"]
                long_mm_value = data[symbol].loc[timestamp]["60_mm"]
                diff_mm = short_mm_value - long_mm_value
                if diff_mm > 0:
                    candidatos.append((symbol,diff_mm))
                
            except:
                continue
        
        candidatos = sorted(candidatos,key = lambda x : x[1],reverse = True)
        candidatos = [(x[0],1) for x in candidatos]
        return candidatos[:espacios_disponibles]

    def check_exits(self,timestamp,data,portafolio):
        if len(portafolio) == 0:
            return []
        elif portafolio[0] == 0:
            return []
        to_close = []
        symbols = [x["symbol"] for x in portafolio]
        cerrar = []
        for symbol in symbols:
            try:
                short_mm_value = data[symbol].loc[timestamp]["30_mm"]
                long_mm_value = data[symbol].loc[timestamp]["60_mm"]
                diff_mm = short_mm_value - long_mm_value
                if diff_mm < 0:
                    cerrar.append(symbol)
                
            except:
                continue          
        return cerrar
        pass

    def get_available_spaces(self,portafolio):
        n_pos = len(portafolio)
        return self.max_posiciones - n_pos
    
    def set_risk_management(self,cash,positions):
        orders = []
        for pos in positions:
            symbol = pos[0]
            side = pos[1]
            tp = self.risk_management["take_profit"]
            sl = self.risk_management["stop_loss"]
            leverage = self.risk_management["leverage"]

            amount = 10
            dict_order = {"symbol":symbol,"take_profit":tp,"stop_loss":sl,"leverage":leverage,"amount":amount,"side":side}
            orders.append(dict_order)
        return orders


            
    
class Backtester:
    def __init__(self,strategy,data_handler):

        self.data_handler = data_handler
        self.benchmark = "BTCUSDT"
        self.strategy = strategy

        self.n_order = 1
        self.trades = {}
        self.ordenes = {}
        self.equity_ordenes = {}
        self.amount_ordenes = 0
        self.weekDays = ("Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo")
        self.dias_operables = ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]
        self.cash = 100
    
    def portafolio_to_list(self,portafolio):
        lista_portafolio = []
        for key in portafolio:
            asset = portafolio[key]
            if asset == 0:
                continue
            else:
                lista_portafolio.append(asset)
        return lista_portafolio

    def obtener_dia_por_fecha(self,date):
        date = str(date)
        date = date.split(" ")[0]
        separados = date.split("-")
        date = datetime.date(int(separados[0]),int(separados[1]),int(separados[2]))
        weekday = date.weekday()
        weekday = self.weekDays[weekday]
        return weekday

    def realizar_backtesting(self,start_date = "2022-01",end_date = "2022-02"):

        self.dataset = self.data_handler.get_all(self.strategy.timeframe)
        self.strategy_dataset = self.strategy.math(self.dataset)

        self.date_range = self.dataset[self.benchmark].loc[start_date:end_date]
        self.date_range = self.date_range.index 
        self.date_range = self.dataset[self.benchmark].loc[start_date:end_date]
        self.date_range = self.date_range.index 

        self.equity = {}
        self.posiciones = self.posiciones = dict.fromkeys(range(self.strategy.max_posiciones),0)
        self.portafolio_actual = self.portafolio_to_list(self.posiciones)
        print(self.portafolio_actual)

        for fecha in self.date_range:
            self.equity[fecha] = self.cash
            self.equity_ordenes[fecha] = self.amount_ordenes
            self.verificar_posiciones(fecha)

            print("-"*22)

            dia_de_la_semana = self.obtener_dia_por_fecha(fecha)
            if dia_de_la_semana in self.dias_operables:
                print(dia_de_la_semana,fecha,"operando")
                to_close_positions = self.strategy.check_exits(fecha,self.strategy_dataset,self.portafolio_actual)
                self.close_trades(fecha,to_close_positions)

                self.portafolio_actual = self.portafolio_to_list(self.posiciones)

                to_open_positions = self.strategy.check_entries(fecha,self.strategy_dataset,self.portafolio_actual)
                self.orders = self.strategy.set_risk_management(self.cash,to_open_positions)
                self.orders = self.fill_orders(self.orders,fecha)

            else:
                print(dia_de_la_semana,fecha,"no se opera")
            print("-"*22)

    def verificar_posiciones(self,timestamp):
        for i in self.posiciones:
            if self.posiciones[i] != 0:
                try :
                    symbol = self.posiciones[i]["symbol"]
                    candle = self.dataset[symbol].loc[timestamp]
                    entry_price = self.posiciones[i]["entry_price"]
                    side = self.posiciones[i]["side"]
                    leverage = self.posiciones[i]["leverage"]
                except Exception as e:
                    print(symbol, timestamp)
                    return 0

                if self.posiciones[i]["side"] == 1:
                    if candle["low"] < self.posiciones[i]["stop_loss"]:
                        self.posiciones[i]["close_price"] = self.posiciones[i]["stop_loss"]
                        self.posiciones[i]["close_type"] = "stop_loss"
                        self.posiciones[i]["close_time"] = timestamp
                        self.posiciones[i]["returns"] = \
                                        ((self.posiciones[i]["close_price"]-entry_price)/entry_price)*side*leverage
                        self.cash += self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"]) 
                        self.posiciones[i]["amount_final"] =  self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"])
                        self.amount_ordenes -= self.posiciones[i]["amount"]
                        self.trades[self.n_order] = self.posiciones[i]
                        self.posiciones[i] = 0
                        self.n_order += 1
                        continue
                    elif candle["high"] > self.posiciones[i]["take_profit"]:
                        self.posiciones[i]["close_price"] = self.posiciones[i]["take_profit"]
                        self.posiciones[i]["close_type"] = "take_profit"
                        self.posiciones[i]["close_time"] = timestamp
                        self.posiciones[i]["returns"] = \
                                        ((self.posiciones[i]["close_price"]-entry_price)/entry_price)*side*leverage
                        self.cash += self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"])
                        self.amount_ordenes -= self.posiciones[i]["amount"]
                        self.posiciones[i]["amount_final"] =  self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"])
                        self.trades[self.n_order] = self.posiciones[i]
                        self.posiciones[i] = 0
                        self.n_order += 1



                elif self.posiciones[i]["side"] == -1:
                    if candle["high"] >  self.posiciones[i]["stop_loss"]:
                        self.posiciones[i]["close_price"] = self.posiciones[i]["stop_loss"]
                        self.posiciones[i]["close_type"] = "stop_loss"
                        self.posiciones[i]["close_time"] = timestamp
                        self.posiciones[i]["returns"] = \
                                        ((self.posiciones[i]["close_price"]-entry_price)/entry_price)*side*leverage
                        self.amount_ordenes -= self.posiciones[i]["amount"]
                        self.cash += self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"])
                        self.posiciones[i]["amount_final"] =  self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"]) 
                        self.trades[self.n_order] = self.posiciones[i]
                        
                        self.posiciones[i] = 0
                        self.n_order += 1


                    elif candle["low"] < self.posiciones[i]["take_profit"]:
                        self.posiciones[i]["close_price"] = self.posiciones[i]["take_profit"]
                        self.posiciones[i]["close_type"] = "take_profit"
                        self.posiciones[i]["close_time"] = timestamp
                        self.posiciones[i]["returns"] = \
                                        ((self.posiciones[i]["close_price"]-entry_price)/entry_price)*side*leverage
                        self.cash += self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"])
                        self.posiciones[i]["amount_final"] =  self.posiciones[i]["amount"]*(1+self.posiciones[i]["returns"])
                        self.amount_ordenes -= self.posiciones[i]["amount"]
                        self.trades[self.n_order] = self.posiciones[i]
                        self.posiciones[i] = 0
                        self.n_order += 1

    def cerrar_posicion(self,n_posicion,timestamp):
        try :
            symbol = self.posiciones[n_posicion]["symbol"]
            entry_price = self.posiciones[n_posicion]["entry_price"]
            side = self.posiciones[n_posicion]["side"]
            leverage = self.posiciones[n_posicion]["leverage"]
            close_price = self.dataset[symbol].loc[timestamp,"close"]
            self.posiciones[n_posicion]["close_price"] = close_price
            self.posiciones[n_posicion]["close_time"] = timestamp
            self.posiciones[n_posicion]["close_type"] = "manual"
            self.posiciones[n_posicion]["returns"] = \
                                            ((self.posiciones[n_posicion]["close_price"]-entry_price)/entry_price)*side*leverage
            self.cash += self.posiciones[n_posicion]["amount"]*(1+self.posiciones[n_posicion]["returns"])
            self.amount_ordenes -= self.posiciones[n_posicion]["amount"]
            self.posiciones[n_posicion]["amount_final"] = self.posiciones[n_posicion]["amount"]*(1+self.posiciones[n_posicion]["returns"])
            self.trades[self.n_order] = self.posiciones[n_posicion]
            self.posiciones[n_posicion] = 0
            self.n_order += 1
        except Exception as e:
            print(self.posiciones[n_posicion],timestamp)
    def crear_orden_backtest(self,timestamp,symbol,side,amount,type = "MARKET",take_profit = False,stop_loss = False,leverage = 1):
        lugar = -1
        for n_posicion in self.posiciones:
            if lugar == -1:
                if self.posiciones[n_posicion] ==0:
                    lugar = n_posicion

            if self.posiciones[n_posicion] != 0:
                if self.posiciones[n_posicion]["symbol"] == symbol:
                    print("Ya existe una posicion en este simbolo")
                    lugar = -1
                    break
                    

        if lugar == -1:
            print(f"No hay espacio para rellenar esta posicion :{symbol}-{timestamp}")
            return 0
        
        entry_price = self.dataset[symbol].loc[timestamp,"close"]

        take_profit = entry_price*(1+side*take_profit)
        stop_loss = entry_price*(1-side*stop_loss)
        self.cash -= amount
        self.amount_ordenes += amount





        orden = {"symbol":symbol,"type":type,"side":side,"amount":amount,
                    "entry_time":timestamp,"entry_price":entry_price,"take_profit":take_profit,
                        "stop_loss":stop_loss,"leverage":leverage}
        self.posiciones[lugar] = orden
        print(f"Orden creada para {symbol}-Entry :{entry_price}({timestamp})")
    def calcular_estadisticas(self):
        self.trades = pd.DataFrame(self.trades)
        self.trades =self.trades.T
        wins = self.trades[self.trades["returns"] > 0]["returns"]
        losses = self.trades[self.trades["returns"] < 0]["returns"]
        total_trades = len(wins) +len(losses)
        avg_win = wins.mean()
        avg_loss = np.mean(losses)
        avg_amount = self.trades["amount"].mean()
        win_rate = len(wins)/total_trades
        r = self.equity_final.pct_change()
        cr = (1+r).cumprod()
        peaks = cr.cummax()
        drawdown = (cr-peaks)/peaks
        max_dd_period = peaks.value_counts().max()
        max_dd = drawdown.min()
        total_ret = (self.equity_final[-1] -self.equity_final[0])/self.equity_final[0]
        monthly_ret = self.equity_final.pct_change().resample("M").apply(cret,last_row = True)
        best_month = monthly_ret.max()
        worst_month = monthly_ret.min()
        avg_month = monthly_ret.mean()
        weekly_ret = self.equity_final.pct_change().resample("W").apply(cret,last_row = True)
        best_week = weekly_ret.max()
        worst_week = weekly_ret.min()
        avg_week = weekly_ret.mean()
        expectancy = avg_win*win_rate +avg_loss*(1-win_rate)
        
        results = {"avg_win":avg_win,"avg_loss":avg_loss,"win_rate":win_rate,
                    "avg_amount":avg_amount,"total_ret":total_ret,
                    "amount_inicial":self.equity_final[0],"amount_final":self.equity_final[-1],"max_dd":max_dd,
                    "max_dd_period":max_dd_period,"best_month":best_month,"worst_month":worst_month,
                    "avg_month":avg_month,"avg_week":avg_week,"worst_week":worst_week,"best_week":best_week,
                    "expectancy":expectancy}
        print(results)
        pass
    def imprimir_resultados(self):
        self.equity = pd.Series(self.equity)
        self.equity.index = pd.to_datetime(self.equity.index)
        self.equity_ordenes = pd.Series(self.equity_ordenes)
        self.equity_final = self.equity + self.equity_ordenes
        self.calcular_estadisticas()
        # print(self.trades)
        self.equity_final = self.equity + self.equity_ordenes
        self.equity_final = self.equity_final.pct_change()
        self.equity_final = (1+self.equity_final).cumprod()

        self.dataset["BTCUSDT"]["r"] = self.dataset["BTCUSDT"]["close"].pct_change()
        self.dataset["BTCUSDT"]["cr"] = (1+self.dataset["BTCUSDT"]["r"].loc[self.date_range]).cumprod()
        plt.plot(self.equity.index,self.equity_final,label = "Equity")
        # plt.plot(self.equity.index,self.dataset["BTCUSDT"]["cr"].loc[self.date_range],label = "Benchmark")
        # plt.plot(self.equity_ordenes.index,self.equity_ordenes)
        plt.legend()
        plt.show()
        pass
    def fill_orders(self,orders,fecha):
        for order in orders:
            self.crear_orden_backtest(
                fecha,order["symbol"],
                order["side"],order["amount"],type = "MARKET",
                take_profit = order["take_profit"],stop_loss = order["stop_loss"],leverage = order["leverage"])
        return []

    def close_trades(self,timestamp,to_close):
        if len(to_close) > 0:
            for symbol in to_close:
                for key in self.posiciones:
                    try:
                        if self.posiciones[key]["symbol"] == symbol:
                            self.cerrar_posicion(key,timestamp)
                    except:
                        continue
        pass



class TripleTimeBands(Strategy):
    def __init__(self):
        self.name = "Triple Timeframe Bollinger Bands"
        self.timeframe = "15m"
        self.broker = "BinanceFutures"

        self.risk_management = {"pos_sizing":0.05,"take_profit":0.05,"stop_loss":0.01,"leverage":15}
        self.max_posiciones = 3
        self.dollar_amount = 3
    def math(self,dataset):
        new_dataset = {}
        self.dataset_macro = {}
        for symbol in dataset:
            try:
                data_15m = dataset[symbol]
                data_15m.index = pd.to_datetime(data_15m["close_time"])
                resample_dict = {"open":"first",
                                    "high":"max","low":"min",
                                    "close":"last","volume":"sum",
                                    "close_time":"last","symbol":"first",
                                    "open_time":"first"}
                data_2h = data_15m.resample("2H",offset= "21:00:00").apply(resample_dict)
                data_12h = data_15m.resample("12H",offset= "21:00:00").apply(resample_dict)

                data_12h["100_mm"] = data_12h["close"].rolling(100).mean()
                data_12h["r"] = data_12h["close"].pct_change()
                data_12h["100_vol"] = data_12h["r"].rolling(100).std()

                data_12h["100_vol_mm"] = data_12h["100_vol"].rolling(100).mean()
                vol_cond = data_12h["100_vol"] > data_12h["100_vol_mm"]
                regime_cond = data_12h["100_mm"] < data_12h["close"]
                data_2h["r"] = data_2h["close"].pct_change()
                data_2h["84_mm"] = data_2h["close"].rolling(84).mean()
                data_2h["84_std"] = data_2h["close"].rolling(84).std()
                data_2h["bb_up"] = data_2h["84_mm"] + data_2h["84_std"]
                data_2h["bb_down"] = data_2h["84_mm"] - data_2h["84_std"]
                overbought = data_2h["close"] > data_2h["bb_up"]
                oversold = data_2h["close"] < data_2h["bb_down"]
                in_range = (data_2h["close"] > data_2h["bb_down"])&(data_2h["close"] < data_2h["bb_up"])
                data_12h["regime"] = np.zeros(data_12h.shape[0])
                data_12h.loc[vol_cond&regime_cond,"regime"] = 4
                data_12h.loc[~vol_cond&regime_cond,"regime"] = 3
                data_12h.loc[vol_cond&~regime_cond,"regime"] = 1
                data_12h.loc[~vol_cond&~regime_cond,"regime"] = 2
                data_2h["status"] = np.zeros(data_2h.shape[0])
                data_2h.loc[oversold,"status"] = -1
                data_2h.loc[overbought,"status"] = 1
                data_2h.loc[in_range,"status"] = 0
                self.dataset_macro[symbol] = {"2H":data_2h,"12H":data_12h}
                new_dataset[symbol] = data_15m
            except Exception as e:
                print(e)

                continue

        # print(new_dataset)
        return new_dataset
    def math_live(self,dataset):
        new_dataset = {}
        self.dataset_macro = {}
        for symbol in dataset:
            try:
                data_15m = dataset[symbol]
                data_15m.index = pd.to_datetime(data_15m["close_time"])
                resample_dict = {"close":"last",
                                    "close_time":"last","symbol":"first",
                                    "open_time":"first"}
                data_2h = data_15m.resample("2H",offset= "21:00:00").apply(resample_dict)
                data_12h = data_15m.resample("12H",offset= "21:00:00").apply(resample_dict)

                data_12h["100_mm"] = data_12h["close"].rolling(100).mean()
                data_12h["r"] = data_12h["close"].pct_change()
                data_12h["100_vol"] = data_12h["r"].rolling(100).std()

                data_12h["100_vol_mm"] = data_12h["100_vol"].rolling(100).mean()
                vol_cond = data_12h["100_vol"] > data_12h["100_vol_mm"]
                regime_cond = data_12h["100_mm"] < data_12h["close"]
                data_2h["r"] = data_2h["close"].pct_change()
                data_2h["84_mm"] = data_2h["close"].rolling(84).mean()
                data_2h["84_std"] = data_2h["close"].rolling(84).std()
                data_2h["bb_up"] = data_2h["84_mm"] + data_2h["84_std"]
                data_2h["bb_down"] = data_2h["84_mm"] - data_2h["84_std"]
                overbought = data_2h["close"] > data_2h["bb_up"]
                oversold = data_2h["close"] < data_2h["bb_down"]
                in_range = (data_2h["close"] > data_2h["bb_down"])&(data_2h["close"] < data_2h["bb_up"])
                data_12h["regime"] = np.zeros(data_12h.shape[0])
                data_12h.loc[vol_cond&regime_cond,"regime"] = 4
                data_12h.loc[~vol_cond&regime_cond,"regime"] = 3
                data_12h.loc[vol_cond&~regime_cond,"regime"] = 1
                data_12h.loc[~vol_cond&~regime_cond,"regime"] = 2
                data_2h["status"] = np.zeros(data_2h.shape[0])
                data_2h.loc[oversold,"status"] = -1
                data_2h.loc[overbought,"status"] = 1
                data_2h.loc[in_range,"status"] = 0
                self.dataset_macro[symbol] = {"2H":data_2h,"12H":data_12h}
                new_dataset[symbol] = data_15m
            except Exception as e:
                print(e)

                continue

        # print(new_dataset)
        return new_dataset
    def check_entries(self,timestamp,data,portafolio):
        candidatos = []
        espacios_disponibles = self.get_available_spaces(portafolio)
        if espacios_disponibles == 0:
            return []

        for symbol in data:
            try:
                pos = 0
                macro_data = self.dataset_macro[symbol]
                regime_value = macro_data["12H"].loc[:timestamp,"regime"].iloc[-1]
                print(f"{symbol} Regime value :{regime_value}")
                status_value = macro_data["2H"].loc[:timestamp,"status"].iloc[-1]
                print(f"{symbol} Status value :{status_value}")
                if (regime_value == 1)|(regime_value == 4):
                    if status_value == -1:
                        pos = -1
                    elif status_value == 1:
                        pos = 1
                    
                candidatos.append((symbol,pos))
                
            except Exception as e:
                # print(e)
                continue
        
        candidatos = [x for x in candidatos if x[1] != 0]

        return candidatos
        # return [("BTCUSDT",-1)]


    def check_exits(self,timestamp,data,portafolio):
        if len(portafolio) == 0:
            return []
        elif portafolio[0] == 0:
            return []
        to_close = []
        symbols = [x["symbol"] for x in portafolio]
        cerrar = []
        for symbol in symbols:
            try:
                pos = 0
                macro_data = self.dataset_macro[symbol]
                regime_value = macro_data["12H"].loc[:timestamp,"regime"].iloc[-1]
                status_value = macro_data["2H"].loc[:timestamp,"status"].iloc[-1]

                if (regime_value == 1)|(regime_value == 4):
                    if status_value == -1:
                        pos = -1
                    elif status_value == 1:
                        pos = 1

                if pos == 0:
                    cerrar.append(symbol)
                
                
            except:
                continue          
        return cerrar
        # return ["ETHUSDT"]

        pass
    def set_risk_management(self,cash,positions):
        orders = []
        for pos in positions:
            symbol = pos[0]
            side = pos[1]
            tp = self.risk_management["take_profit"]
            sl = self.risk_management["stop_loss"]
            leverage = self.risk_management["leverage"]

            amount = self.dollar_amount
            dict_order = {"symbol":symbol,"take_profit":tp,"stop_loss":sl,"leverage":leverage,"amount":amount,"side":side}
            orders.append(dict_order)
        return orders


if __name__ == '__main__':
    db_file = os.path.join("Databases","BinanceFutures.db")
    dh = DataHandler(db_file)
    data = dh.get_local("15m",100000)
    strat = TripleTimeBands()
    s_data = strat.math(data)
    last_ts = s_data["BTCUSDT"].index[-1]
    print(last_ts)
    print(strat.check_entries(last_ts,s_data,[]))
    # btester = Backtester(strat,dh)
    # btester.realizar_backtesting(start_date = "2022-07",end_date = "2022-08")
    # btester.imprimir_resultados()
    # btester.trades.to_csv("Resultados.csv")