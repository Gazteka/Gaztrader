from config import  * 



class BrokerAdapter:
    def __init__(self,name):
        print(f"Iniciando {name} adapter")
        self.name  = name
        self.carpeta_apis = CARPETA_APIS
        self.carpeta_databases = CARPETA_DATABASES
        self.api_route = os.path.join(self.carpeta_apis,f"{self.name}.json")
        self.database_route = os.path.join(self.carpeta_databases,f"{self.name}.db")
        self.api_dic = self.load_api()
        self.conn = self.load_database()
        self.cursor = self.conn.cursor()

    def load_api(self):
        api_dic = open(self.api_route,"r")
        api_dic = json.load(api_dic)
        return api_dic
    def convert_unix(self,timestamp):

        date = datetime.datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d %H:%M:%S")
        return date
    def load_database(self):
        conn = sqlite3.connect(self.database_route,check_same_thread= False)
        print(f"Conectado a {self.database_route}")
        return conn

    def create(self):
        pass
    def connectar_client(self):
        pass
    

class BinanceFuturesAdapter(BrokerAdapter):
    def __init__(self):
        super().__init__("BinanceFutures")
        self.binance_client = self.connectar_client()
        self.create()
        self.restart = False

        self.intraday_symbols = {"5m":["BTCUSDT","ETHUSDT","BNBUSDT","ADAUSDT"],
                                "15m":["BTCUSDT","ETHUSDT","MATICUSDT",
                        "FTMUSDT","STMXUSDT","COTIUSDT","DUSKUSDT","SANDUSDT"],
                    }
    def create(self):
        self.cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS crypto(
                        id INTEGER PRIMARY KEY,
                        symbol TEXT NOT NULL UNIQUE
                    )""")
        self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS crypto_prices_binance(
                    id INTEGER PRIMARY KEY,
                    crypto_symbol TEXT NOT NULL,
                    identifier NOT NULL UNIQUE,
                    timestamp NOT NULL,
                    timeframe NOT NULL,
                    open_time NOT NULL,
                    open NOT NULL,
                    high NOT NULL,
                    low NOT NULL,
                    close NOT NULL,
                    volume NOT NULL,
                    close_time NOT NULL,
                    FOREIGN KEY (crypto_symbol) REFERENCES crypto (symbol)
                )""")

    def connectar_client(self):
        binance_client = Client(api_key = self.api_dic["key"],api_secret = self.api_dic["secret"])
        print(f"Conectado a {self.name} client")   
        return binance_client
        
    def reconnect_client(self):
        binance_client = Client(api_key = self.api_dic["key"],api_secret = self.api_dic["secret"])
        print(f"Conectado a {self.name} client")   

        self.binance_client = binance_client


    def guardar_kline(self,kline):
        open_time = kline["t"]
        timestamp = kline["t"]
        open_time = self.convert_unix(open_time)
        symbol = kline["s"]
        close_time = kline["T"]
        close_time = self.convert_unix(close_time)
        open_price = kline["o"]
        high = kline["h"]
        low = kline["l"]
        timeframe = kline["i"]
        close_price = kline["c"]
        volume = kline["v"]
        date_identifier = str(open_time).split(" ")[0]
        date_identifier = "".join(date_identifier.split("-"))
        hour_identifier = str(open_time).split(" ")[1]
        hour_identifier = "".join(hour_identifier.split(":"))
        identifier = date_identifier + hour_identifier


        identifier = date_identifier + hour_identifier
        identifier = identifier + timeframe + "-" + symbol
        try:
            self.cursor.execute(f"""
                    INSERT INTO crypto_prices_binance (
                    crypto_symbol,identifier,timestamp,timeframe,open_time,open,high,low,close,volume,close_time
                    ) 
                    VALUES
                     ('{symbol}','{identifier}',{timestamp},'{timeframe}','{open_time}',{open_price},
                    {high},{low},{close_price},{volume},
                    '{close_time}')
                
                """)
            print(identifier,"guarado en la base de datos",open_time)
        except Exception as e:
            print(e)
            print("Este dato ya existe en la base de datos:",identifier)
        self.conn.commit()
        pass

    def descargar_historic_ohclv(self,symbol = "BTCUSDT",timeframe = "1d",start_date = "1 Jan, 2017",end_date = False):
        start_date = pd.to_datetime(start_date)
        start_date = start_date.strftime("%Y %b, %d")
        print(f"Descargando Datos de {symbol}-{timeframe} desde {start_date}")
        try :
            if end_date ==False:
                klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date)
                return klines
            else:
                klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date,end_date)
                return klines 
        except Exception as e:
            if e.status_code == 400:
                print("Ticker no encontrado")
                print(e)
                return []
            else:
                print(e)
                print("Limite de requisitos excedido, espera un momento....")
                time.sleep(100)
                if end_date ==False:
                    klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date)
                    return klines
                else:
                    klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date,end_date)
                    return klines 


                
    def obtener_pares_binance(self,quote_currency = "USDT"):
        binance_tickers = self.binance_client.get_all_tickers()
        # Client().futures_symbol_ticker()
        binance_tickers = [ticker["symbol"] for ticker in binance_tickers if quote_currency in ticker["symbol"]]
        # binance_symbols =[ticker[:-4] for ticker in binance_tickers]
        # id_map = id_map[id_map.symbol.isin(binance_symbols)]
        return binance_tickers




    def obtener_ultima_fecha_ohlcv_binance(self,symbol,timeframe = "1d"):
        self.cursor.execute(f"""
                SELECT * FROM crypto_prices_binance WHERE crypto_prices_binance.crypto_symbol= '{symbol}' 
                AND crypto_prices_binance.timeframe = '{timeframe}'
                ORDER BY open_time DESC LIMIT 1
        """)
        result = self.cursor.fetchall()
        
        if len(result) == 0:
            print("No existen fechas para ", symbol)
        return result


    def obtener_dataframe(self,symbol,n =200,timeframe = "1d" ):
        self.cursor.execute(f"""
                SELECT * FROM crypto_prices_binance WHERE crypto_prices_binance.crypto_symbol= '{symbol}' 
                AND crypto_prices_binance.timeframe = '{timeframe}'
                ORDER BY open_time DESC LIMIT {n}
        """)
        result = self.cursor.fetchall()
        
        if len(result) == 0:
            print("No existen fechas para ", symbol)
        return result
    def get_local(self,symbols,n = 7000,timeframe = "15m"):
        dic_data = {}
        for symbol in symbols:
            
            dic_data[symbol] = self.obtener_dataframe(symbol,n = n,timeframe = timeframe)
            print(symbol,"listo")
        return dic_data
    def guardar_historic_ohlcv(self,symbol,klines,tf):

        try : 
            self.cursor.execute(f"INSERT INTO crypto (symbol) values ('{symbol}')")
            print(f"{symbol} agregado a la base de datos")

        except:
            print("")

        df = pd.DataFrame(klines)
        df = df.iloc[:,:7]
        df.columns = ["open_time","open","high","low","close","volume","close_time"]
        df["timestamp"] = df["open_time"]
        df["open_time"] = df["open_time"].apply(self.convert_unix)
        timeframe = tf
        df["close_time"] = df["close_time"].apply(self.convert_unix)

        for i in range(df.shape[0]):
            row = df.iloc[i]

            open_t = row["open_time"]
            close_t = row["close_time"]
            open_p = row["open"]
            close_p = row["close"]
            timestamp = row["timestamp"]
            low = row["low"]
            high = row["high"]
            volume = row["volume"]
            hour_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hour_now = datetime.datetime.strptime(hour_now, "%Y-%m-%d %H:%M:%S")
            date_today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # print("-"*22,close_t)
            diff = datetime.datetime.strptime(date_today,"%Y-%m-%d %H:%M:%S") -datetime.datetime.strptime(close_t, "%Y-%m-%d %H:%M:%S") 
            diff = str(diff).split(",")
            # print(diff)
            if "-1 day" in diff:
                print("Vela no cerrada", close_t)
                continue
            if date_today == close_t:
                if hour_now.hour < 21:
                    print("Vela no cerrada", close_t)
                    continue
            date_identifier = row["open_time"].split(" ")[0]
            date_identifier = "".join(date_identifier.split("-"))
            hour_identifier = row["open_time"].split(" ")[1]
            hour_identifier = "".join(hour_identifier.split(":"))
            identifier = date_identifier + hour_identifier
            identifier = identifier + tf + "-" + symbol
            try:
                self.cursor.execute(f"""
                INSERT INTO crypto_prices_binance (
                    crypto_symbol,identifier,timestamp,timeframe,open_time,open,high,low,close,volume,close_time
                    ) 
                    VALUES
                     ('{symbol}','{identifier}',{timestamp},'{timeframe}','{open_t}',{open_p},
                    {high},{low},{close_p},{volume},
                    '{close_t}')
                
                """)
                
            except Exception as e:
                print(e)
                print("Este dato ya existe en la base de datos:",identifier)
        self.conn.commit()



    def obtener_pares_disponibles(self):
        self.cursor.execute(""" SELECT *  FROM crypto
        """)
        ans = self.cursor.fetchall()
        return ans

    def actualizar_datos(self,symbol = "BTCUSDT",timeframe = "1d"):
        ans = self.obtener_ultima_fecha_ohlcv_binance(symbol,timeframe)
        print(ans)
        if ans ==[]:
            klines = self.descargar_historic_ohclv(symbol = symbol,timeframe=timeframe)
            self.guardar_historic_ohlcv(symbol,klines,timeframe)
        else:
            last_date = ans[0][5]
            start_date = pd.to_datetime(last_date)
            start_date = start_date.strftime("%Y %b, %d")
            hora = datetime.datetime.now().hour

            klines = self.descargar_historic_ohclv(
                symbol = symbol,timeframe=timeframe,start_date = start_date)
            self.guardar_historic_ohlcv(symbol,klines,timeframe)

    def actualizacion_diaria(self):
        # symbols = self.obtener_pares_binance()
        symbols = self.obtener_pares_disponibles()
        symbols = [x[1] for x in symbols]

        for symbol in symbols:
            try :
                self.actualizar_datos(symbol = symbol)

            except  Exception as e:
                print(e)
                print("No se pudo actualizar : (Futures)",symbol)

    def actualizacion_5m(self):
        symbols = self.intraday_symbols["5m"]
        for symbol in symbols:
            try :
                self.actualizar_datos(symbol = symbol,timeframe = "5m")
            except  Exception as e:
                print(e)
                print("No se pudo actualizar : (Futures)",symbol)
    def actualizacion_15m(self):

        # self.symbols_15m = ["BTCUSDT","ETHUSDT","BNBUSDT","ADAUSDT","XRPUSDT","DOGEUSDT","DOTUSDT"
        #             ,"MATICUSDT","COTIUSDT","FTMUSDT","SANDUSDT","MANAUSDT"]
        symbols = self.intraday_symbols["15m"]
        for symbol in symbols:
            try :
                self.actualizar_datos(symbol = symbol,timeframe = "15m")
            except :
                print("No se pudo actualizar : (Futures)",symbol) 

    def actualizacion_completa(self):
        # print("Actualizacion diaria")
        # self.actualizacion_diaria()
        # print("Actualizacion 5m ")
        # self.actualizacion_5m()
        print("Actualizacion 15m")
        self.actualizacion_15m()

    def stream_market(self,symbols,klines,event):
        print(f"Stream iniciado para {symbols}-{klines}")
        ubwa = unicorn_binance_websocket_api.BinanceWebSocketApiManager(exchange="binance.com-futures")
        ubwa.create_stream(klines,symbols,output= "dict")
        while True:
            oldest_data_from_stream_buffer = ubwa.pop_stream_data_from_stream_buffer()
            if self.restart == True:
                print("Restarting websocket")
                break
            if oldest_data_from_stream_buffer:
                self.procesar_mensajes(oldest_data_from_stream_buffer,event)

    def set_restart(self):
        self.restart = True
    def procesar_mensajes(self,mensaje,event):
        try :
            kline = mensaje["data"]["k"]
            closed_candle = kline["x"]

            if closed_candle:
                # print(mensaje)
                print("Guardando vela")
                open_time = kline["t"]
                open_time = self.convert_unix(open_time)
                symbol = kline["s"]
                close_time = kline["T"]
                close_time = self.convert_unix(close_time)
                open_price = kline["o"]
                high = kline["h"]
                low = kline["l"]
                close_price = kline["c"]
                volume = kline["v"]
                row = {"symbol":symbol,
                        "open_time":open_time,"open":open_price,"high":high,"low":low,"close":close_price,
                            "volume":volume,"close_time":close_time}
                print(row)
                self.guardar_kline(kline)

                print("kline guardada")
                event.set()

                    
                
        except :
            print(mensaje)
        
        finally:
            return 

    def stream_15m(self,event):
        # self.thread_update = threading.Thread(target = self.actualizacion_15m())
        # self.thread_update.start()
        self.restart = False
        self.actualizacion_15m()
        self.actualizacion_15m()
        self.stream_market(self.intraday_symbols["15m"],["kline_15m"],event)
        
        # self.stream_market()
        # self.actualizacion_15m()
        







class BinanceFuturesAdapter2(BrokerAdapter):
    def __init__(self):
        super().__init__("BinanceFutures")
        self.binance_client = self.connectar_client()
        self.create()
        self.restart = False
        self.order_manager_class = BinanceFuturesOrderManager
        self.order_manager = BinanceFuturesOrderManager(self.binance_client)

        self.intraday_symbols = {"5m":["BTCUSDT","ETHUSDT","BNBUSDT","ADAUSDT"],
                                "15m":["BTCUSDT","ETHUSDT","MATICUSDT",
                        "FTMUSDT","STMXUSDT","COTIUSDT","DUSKUSDT","SANDUSDT"],
                    }
        print("BinanceFutures adapter listo")

    def create(self):
        self.cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS crypto(
                        id INTEGER PRIMARY KEY,
                        symbol TEXT NOT NULL UNIQUE
                    )""")
        self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS crypto_prices_binance(
                    id INTEGER PRIMARY KEY,
                    crypto_symbol TEXT NOT NULL,
                    identifier NOT NULL UNIQUE,
                    timestamp NOT NULL,
                    timeframe NOT NULL,
                    open_time NOT NULL,
                    open NOT NULL,
                    high NOT NULL,
                    low NOT NULL,
                    close NOT NULL,
                    volume NOT NULL,
                    close_time NOT NULL,
                    FOREIGN KEY (crypto_symbol) REFERENCES crypto (symbol)
                )""")

    def connectar_client(self):
        binance_client = Client(api_key = self.api_dic["key"],api_secret = self.api_dic["secret"])
        print(f"Conectado a {self.name} client")   
        return binance_client

    def reconnect_client(self):
        binance_client = Client(api_key = self.api_dic["key"],api_secret = self.api_dic["secret"])
        print(f"Conectado a {self.name} client")   

        self.binance_client = binance_client
        self.order_manager = self.order_manager_class(self.binance_client)

    def get_historical_candles(self,symbol = "BTCUSDT",timeframe = "1d",start_date = "1 Jan, 2017",end_date = False):
        start_date = pd.to_datetime(start_date)
        start_date = start_date.strftime("%Y %b, %d")
        print(f"Descargando Datos de {symbol}-{timeframe} desde {start_date}")
        try :
            if end_date ==False:
                klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date)
                return klines
            else:
                klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date,end_date)
                return klines 
        except Exception as e:
            if e.status_code == 400:
                print("Ticker no encontrado")
                print(e)
                return []
            else:
                print(e)
                print("Limite de requisitos excedido, espera un momento....")
                time.sleep(100)
                if end_date ==False:
                    klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date)
                    return klines
                else:
                    klines = self.binance_client.futures_historical_klines(symbol,timeframe,start_date,end_date)
                    return klines 

    def obtener_all_tickers(self,quote_currency = "USDT"):
        binance_tickers = self.binance_client.get_all_tickers()

        binance_tickers = [ticker["symbol"] for ticker in binance_tickers if quote_currency in ticker["symbol"]]

        return binance_tickers


    def get_dataframe(self,symbol,n =200,timeframe = "1d" ):

        if n =="all":
            self.cursor.execute(f"""
                    SELECT * FROM crypto_prices_binance WHERE crypto_prices_binance.crypto_symbol= '{symbol}' 
                    AND crypto_prices_binance.timeframe = '{timeframe}'
                    ORDER BY open_time DESC 
            """)
            result = self.cursor.fetchall()
        else:
                
            self.cursor.execute(f"""
                    SELECT * FROM crypto_prices_binance WHERE crypto_prices_binance.crypto_symbol= '{symbol}' 
                    AND crypto_prices_binance.timeframe = '{timeframe}'
                    ORDER BY open_time DESC LIMIT {n}
            """)
            result = self.cursor.fetchall()
            
        if len(result) == 0:
            print("No existen fechas para ", symbol)
        return result

    def get_available_tickers(self):
        self.cursor.execute(""" SELECT *  FROM crypto
        """)
        ans = self.cursor.fetchall()
        return ans

    def last_saved_timestamp(self,symbol,timeframe = "1d"):
        self.cursor.execute(f"""
                SELECT * FROM crypto_prices_binance WHERE crypto_prices_binance.crypto_symbol= '{symbol}' 
                AND crypto_prices_binance.timeframe = '{timeframe}'
                ORDER BY open_time DESC LIMIT 1
        """)
        result = self.cursor.fetchall()
        
        if len(result) == 0:
            print("No existen fechas para ", symbol)
        return result

    def update_ticker(self,symbol = "BTCUSDT",timeframe = "1d"):
        ans = self.last_saved_timestamp(symbol,timeframe)
        print(ans)
        if ans ==[]:
            klines = self.get_historical_candles(symbol = symbol,timeframe=timeframe)
            self.save_historical_candles(symbol,klines,timeframe)
        else:
            last_date = ans[0][5]
            start_date = pd.to_datetime(last_date)
            start_date = start_date.strftime("%Y %b, %d")
            hora = datetime.datetime.now().hour

            klines = self.get_historical_candles(
                symbol = symbol,timeframe=timeframe,start_date = start_date)
            self.save_historical_candles(symbol,klines,timeframe)

    def full_update(self,timeframe):

        # self.symbols_15m = ["BTCUSDT","ETHUSDT","BNBUSDT","ADAUSDT","XRPUSDT","DOGEUSDT","DOTUSDT"
        #             ,"MATICUSDT","COTIUSDT","FTMUSDT","SANDUSDT","MANAUSDT"]
        symbols = self.intraday_symbols[timeframe]
        for symbol in symbols:
            try :
                self.update_ticker(symbol = symbol,timeframe = timeframe)
            except  Exception as e:
                print(e)
                print("No se pudo actualizar : (Futures)",symbol) 

    def process_live_message(self,mensaje,event):
        try :
            kline = mensaje["data"]["k"]
            closed_candle = kline["x"]

            if closed_candle:
                # print(mensaje)
                print("Guardando vela")
                open_time = kline["t"]
                open_time = self.convert_unix(open_time)
                symbol = kline["s"]
                close_time = kline["T"]
                close_time = self.convert_unix(close_time)
                open_price = kline["o"]
                high = kline["h"]
                low = kline["l"]
                close_price = kline["c"]
                volume = kline["v"]
                row = {"symbol":symbol,
                        "open_time":open_time,"open":open_price,"high":high,"low":low,"close":close_price,
                            "volume":volume,"close_time":close_time}
                print(row)
                self.save_live_candle(kline)

                print("kline guardada")
                event.set()

                    
                
        except Exception as e:
            print("ERROR:",e)
            print(mensaje)
        
        finally:
            return 

    def set_restart(self):
        self.restart = True
        
    def stream_market(self,symbols,klines,event):
        print(f"Stream iniciado para {symbols}-{klines}")
        ubwa = unicorn_binance_websocket_api.BinanceWebSocketApiManager(exchange="binance.com-futures")
        ubwa.create_stream(klines,symbols,output= "dict")
        while True:
            oldest_data_from_stream_buffer = ubwa.pop_stream_data_from_stream_buffer()
            if self.restart == True:
                print("Restarting websocket")
                break
            if oldest_data_from_stream_buffer:
                self.process_live_message(oldest_data_from_stream_buffer,event)

    def save_historical_candles(self,symbol,klines,tf):

        try : 
            self.cursor.execute(f"INSERT INTO crypto (symbol) values ('{symbol}')")
            print(f"{symbol} agregado a la base de datos")

        except:
            print("")

        df = pd.DataFrame(klines)
        df = df.iloc[:,:7]
        df.columns = ["open_time","open","high","low","close","volume","close_time"]
        df["timestamp"] = df["open_time"]
        df["open_time"] = df["open_time"].apply(self.convert_unix)
        timeframe = tf
        df["close_time"] = df["close_time"].apply(self.convert_unix)

        for i in range(df.shape[0]):
            row = df.iloc[i]

            open_t = row["open_time"]
            close_t = row["close_time"]
            open_p = row["open"]
            close_p = row["close"]
            timestamp = row["timestamp"]
            low = row["low"]
            high = row["high"]
            volume = row["volume"]
            hour_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hour_now = datetime.datetime.strptime(hour_now, "%Y-%m-%d %H:%M:%S")
            date_today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # print("-"*22,close_t)
            diff = datetime.datetime.strptime(date_today,"%Y-%m-%d %H:%M:%S") -datetime.datetime.strptime(close_t, "%Y-%m-%d %H:%M:%S") 
            diff = str(diff).split(",")
            # print(diff)
            if "-1 day" in diff:
                print("Vela no cerrada", close_t)
                continue
            if date_today == close_t:
                if hour_now.hour < 21:
                    print("Vela no cerrada", close_t)
                    continue
            date_identifier = row["open_time"].split(" ")[0]
            date_identifier = "".join(date_identifier.split("-"))
            hour_identifier = row["open_time"].split(" ")[1]
            hour_identifier = "".join(hour_identifier.split(":"))
            identifier = date_identifier + hour_identifier
            identifier = identifier + tf + "-" + symbol
            try:
                self.cursor.execute(f"""
                INSERT INTO crypto_prices_binance (
                    crypto_symbol,identifier,timestamp,timeframe,open_time,open,high,low,close,volume,close_time
                    ) 
                    VALUES
                     ('{symbol}','{identifier}',{timestamp},'{timeframe}','{open_t}',{open_p},
                    {high},{low},{close_p},{volume},
                    '{close_t}')
                
                """)
                
            except Exception as e:
                print(e)
                print("Este dato ya existe en la base de datos:",identifier)
        self.conn.commit()

    def save_live_candle(self,kline):
        open_time = kline["t"]
        timestamp = kline["t"]
        open_time = self.convert_unix(open_time)
        symbol = kline["s"]
        close_time = kline["T"]
        close_time = self.convert_unix(close_time)
        open_price = kline["o"]
        high = kline["h"]
        low = kline["l"]
        timeframe = kline["i"]
        close_price = kline["c"]
        volume = kline["v"]
        date_identifier = str(open_time).split(" ")[0]
        date_identifier = "".join(date_identifier.split("-"))
        hour_identifier = str(open_time).split(" ")[1]
        hour_identifier = "".join(hour_identifier.split(":"))
        identifier = date_identifier + hour_identifier


        identifier = date_identifier + hour_identifier
        identifier = identifier + timeframe + "-" + symbol
        try:
            self.cursor.execute(f"""
                    INSERT INTO crypto_prices_binance (
                    crypto_symbol,identifier,timestamp,timeframe,open_time,open,high,low,close,volume,close_time
                    ) 
                    VALUES
                     ('{symbol}','{identifier}',{timestamp},'{timeframe}','{open_time}',{open_price},
                    {high},{low},{close_price},{volume},
                    '{close_time}')
                
                """)
            print(identifier,"guarado en la base de datos",open_time)
        except Exception as e:
            print(e)
            print("Este dato ya existe en la base de datos:",identifier)
        self.conn.commit()
        pass
    



class BinanceFuturesOrderManager:

    def __init__(self,client):
        self.binance_client = client
        self.ex_info = self.binance_client.get_exchange_info()
        self.leverage = 1

    

    def create_order(self,symbol,type,amount,take_profit = False,stop_loss = False,leverage = 1):
        if type == 1:
            type = "BUY"
        elif type == -1:
            type = "SELL"
        self.binance_client.futures_change_leverage(symbol = symbol,leverage = leverage)
        # self.binance_client.futures_}
        try :
            self.binance_client.futures_change_margin_type(symbol = symbol,marginType = "ISOLATED")
        except Exception as e :
            print(e,symbol)
            pass
        order = {"main":None,"stop_loss":False,"take_profit":False}
        if type == "BUY":
            order["main"] = self.binance_client.futures_create_order(symbol = symbol,type = "MARKET",side = "BUY",quantity = amount,leverage = 1)
            if stop_loss:
                sl_order = self.binance_client.futures_create_order(symbol = symbol,type = "STOP_MARKET",side = "SELL",quantity = amount,stopPrice = stop_loss)
                order["stop_loss"] = sl_order
            if take_profit:
                tp_order = self.binance_client.futures_create_order(symbol = symbol,type = "TAKE_PROFIT_MARKET",side = "SELL",quantity = amount,stopPrice = take_profit)
                order["take_profit"] = tp_order

            return order
        
        elif type == "SELL":
            order["main"] = self.binance_client.futures_create_order(symbol = symbol,type = "MARKET",side = "SELL",quantity = amount,leverage = 1)
            if stop_loss:
                sl_order = self.binance_client.futures_create_order(symbol = symbol,type = "STOP_MARKET",side = "BUY",quantity = amount,stopPrice = stop_loss)
                order["stop_loss"] = sl_order
            if take_profit:
                tp_order = self.binance_client.futures_create_order(symbol = symbol,type = "TAKE_PROFIT_MARKET",side = "BUY",quantity = amount,stopPrice = take_profit)
                order["take_profit"] = tp_order
            return order

    def get_decimals(self,symbol):
        order_book = self.binance_client.futures_order_book(symbol = symbol)
        bid = order_book["bids"][0][0]
        n_string = str(bid)
        n_split = n_string.split(".")
        decimals = len(n_split[1])
        return decimals


    def set_risk_management(self,symbol,side,risk_management):

        decimals = self.get_decimals(symbol)
        price = self.binance_client.futures_mark_price(symbol = symbol)["markPrice"]
        price = float(price)
        take_profit = price*(1+side*risk_management["take_profit"])
        take_profit = round(take_profit,decimals)
        stop_loss = price*(1-side*risk_management["stop_loss"])
        stop_loss = round(stop_loss,decimals)

        return {"take_profit_price":take_profit,"stop_loss_price":stop_loss,"actual_price":price}
    def calculate_amount(self,dolar_amount,symbol,leverage = 1):

        price = self.binance_client.futures_mark_price(symbol = symbol)["markPrice"]
        presicion = self.get_symbol_precision(symbol)
        dolar_amount = dolar_amount*leverage
        monto = dolar_amount/float(price)
        monto = round(monto,presicion)
        return monto


    def get_symbol_precision(self,symbol):
        ticker_info = self.binance_client.futures_ticker(symbol = symbol)
        last_qty = ticker_info["lastQty"]
        last_qty = str(last_qty)
        last_qty_split = last_qty.split(".")
        try :
            precision = len(last_qty_split[1])
            return precision
        except:
            return 0

    def get_balance_total(self):
        assets = self.binance_client.futures_account_balance()
        assets_search = [asset for asset in assets if asset["asset"] == "USDT"]
        print(assets_search)
        balance = assets_search[0]["balance"]
        balance = float(balance)
        balance = round(balance,0)
        return balance

    def get_balance_disponible(self):
        assets = self.binance_client.futures_account_balance()
        assets_search = [asset for asset in assets if asset["asset"] == "USDT"]
        print(assets_search)
        balance = assets_search[0]["withdrawAvailable"]
        balance = float(balance)
        balance = round(balance,0)
        return balance

    def get_posiciones(self):
        try :
            assets = self.binance_client.futures_position_information()
            assets_usados = [{asset["symbol"]:float(asset["isolatedMargin"])} for asset in assets if float(asset["isolatedMargin"]) != 0]
            posiciones_info = [asset for asset in assets if assets if float(asset["isolatedMargin"]) != 0]
            list_pos = []
            for pos in posiciones_info:
                    symbol = pos["symbol"]
                    amount = pos["positionAmt"]
                    margin = pos["isolatedMargin"]
                    dic_pos = {"symbol":symbol,"amount": amount,"margin":margin}
                    list_pos.append(dic_pos)

            print(posiciones_info)
            return list_pos
        except  Exception as e:
            print("Exception in get_posiciones",e)
            print(type(e))
            return 0
            

    def eliminar_ordenes(self):
        posiciones = self.get_posiciones()
        lista_posiciones = []
        for posicion in posiciones:
            pos = list(posicion.keys())["symbol"]
            lista_posiciones.append(pos)
        ordenes = self.binance_client.futures_get_open_orders()

        ordenes_abiertas = self.binance_client.futures_get_open_orders()
        for orden in ordenes_abiertas:
            id = orden["orderId"]
            symbol = orden["symbol"]
            if symbol in lista_posiciones:
                continue
            else:
                self.binance_client.futures_cancel_order(symbol = symbol,orderId = id)

    def eliminar_orden(self,symbol):
        ordenes_abiertas = self.binance_client.futures_get_open_orders()
        for orden in ordenes_abiertas:
            id = orden["orderId"]
            symbol_orden = orden["symbol"]
            if symbol ==symbol_orden:
                self.binance_client.futures_cancel_order(symbol = symbol,orderId = id)

            else:
                continue
   

    def close_position(self,symbol,amount,side = "SELL",leverage = 3):
        if side == 1:
            side = "BUY"
        elif side == -1:
            side = "SELL"
        

        amount = self.calculate_amount(amount*2,symbol,leverage)
        self.binance_client.futures_create_order(symbol = symbol,type = "MARKET",side = side,quantity = amount,reduceOnly = "true")
        pass

            
if __name__ == "__main__":
    ba = BinanceFuturesAdapter2()
    ba.full_update("15m")
    ba.reconnect_client()
    balance = ba.order_manager.get_balance_total()
    disponible = ba.order_manager.get_balance_disponible()
    print(balance/disponible)
    # ba.actualizacion_completa()
    # ba.stream_15m()
    # print(ba.obtener_pares_disponibles())