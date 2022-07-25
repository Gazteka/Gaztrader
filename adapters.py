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

        self.intraday_symbols = {"5m":["BTCUSDT","ETHUSDT","BNBUSDT","ADAUSDT"],
                                "15m":["BTCUSDT","ETHUSDT"],
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
            if oldest_data_from_stream_buffer:
                self.procesar_mensajes(oldest_data_from_stream_buffer,event)

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
                if self.thread_update.isAlive():
                    print("Aun estamos carrgando")
                    print("-"*20)
                    self.buffer.append(kline)
                    print(self.buffer)
                    print("-"*20)
                    
                
        except :
            print(mensaje)

    def stream_15m(self,event):
        # self.thread_update = threading.Thread(target = self.actualizacion_15m())
        # self.thread_update.start()
        self.actualizacion_15m()
        self.actualizacion_15m()
        self.stream_market(self.intraday_symbols["15m"],["kline_15m"],event)
        
        # self.stream_market()
        # self.actualizacion_15m()
        

if __name__ == "__main__":
    ba = BinanceFuturesAdapter()
    # ba.actualizacion_completa()
    ba.stream_15m()
    # print(ba.obtener_pares_disponibles())