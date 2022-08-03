from config import * 
import asyncio
from market_adapter import MarketAdapter, ADAPTERS_DICT
from Devset.strategies import DataHandler, TripleTimeBands
from multiprocessing import Process


def convert_unix(timestamp):

    date = datetime.datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d %H:%M:%S")
    return date

class Logger:
    def __init__(self):
        self.ruta_logs = "logs.csv"
        self.ruta_status = "status.csv"

    def write(self,event_type,event_info):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"\n{timestamp};{event_type};{event_info}"
        with open(self.ruta_logs,"a")  as file:
            file.write(line)
    def set_status(self,equity,posiciones):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"\n{timestamp};{equity};{posiciones}"
        with open(self.ruta_status,"a")  as file:
            file.write(line)
    def get_status(self):
        # timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # line = f"\n{timestamp};{equity};{posiciones}"
        with open(self.ruta_status,"r")  as file:
            last_status = file.readlines()[-1]
        return last_status

class TelegramMessager:
    def __init__(self,carpeta_apis):
        self.ruta = os.path.join(carpeta_apis,"Telegram.json")
        tg_config = open(self.ruta,"r")
        tg_config = json.load(tg_config)
        self.tg_key = tg_config["API"]
        self.chat_id = tg_config["chat_id"]
        self.event = False

        self.channel = telebot.TeleBot(self.tg_key)
        self.interval = 3
        self.timeout = 30

        balance_dict = dict(
            function=lambda msg, obj=self: obj.balance_handler(msg),
            filters=dict(
                commands=["balance","restart","status","positions","menu"],
            )
        )
        self.channel.add_message_handler(balance_dict)
        self.queue = []

    def set_restart(self):
        self.channel.stop_polling()

    def balance_handler(self, message):
        print("Event command")
        if not self.event:
            pass
        else:
            self.event.set()
            message = message.text
            self.queue.append(message)
            self.channel.send_message(self.chat_id,"Event set")
    def poll(self,event):
        # print("polling")
        self.event = event
        try:
            self.channel.send_message(self.chat_id,"polling")
        # self.channel.polling()
        except:
            print("")
        #global bot #Keep the bot object as global variable if needed
        print("Starting bot polling now")
        while True:
            try:
                print("New bot instance started")
                self.channel = telebot.TeleBot(self.tg_key) #Generate new bot instance
                balance_dict = dict(
            function=lambda msg, obj=self: obj.balance_handler(msg),
            filters=dict(
                commands=["balance","restart","status","positions","menu"],
            )
        )
                self.channel.add_message_handler(balance_dict)
                self.channel.polling(none_stop=True, interval=self.interval, timeout=self.timeout)
            except Exception as ex: #Error in polling
                print("Bot polling failed, restarting in {}sec. Error:\n{}".format(self.timeout, ex))
                self.channel.stop_polling()
                time.sleep(self.timeout)
            else: #Clean exit
                self.channel.stop_polling()
                print("Bot polling loop finished")
                break #End loop
    def enviar_mensaje(self,mensaje):
            self.channel.send_message(self.chat_id,mensaje)


class ComplexEventProcessing:
    def __init__(self,market_adapter,telegram_bot):
        self.market_adapter = market_adapter
        self.telegram_bot = telegram_bot
        self.symbols_usables = ["BTCUSDT","ETHUSDT","MATICUSDT",
                        "FTMUSDT","STMXUSDT","COTIUSDT","DUSKUSDT","SANDUSDT"]
        self.timeframes_usables = ["kline_15m"]
        self.strategy  = TripleTimeBands()
        self.lock = threading.Lock()
        db_file = os.path.join("Databases","BinanceFutures.db")
        self.datahandler = DataHandler(db_file)

        self.logger = Logger()
        self.restart = False


    
    def operar(self,event):
        self.restart = False
        while True:
            if self.restart == True:
                break
            if event.isSet():

                time.sleep(2)
                print("Obteniendo data")
                self.lock.acquire()
                self.market_adapter.reconnect_client()
                self.portafolio_actual = 0
                while self.portafolio_actual == 0:
                    try :
                        print("Obteniendo portafolio")
                        self.portafolio_actual = self.market_adapter.order_manager.get_posiciones()

                    except :
                        time.sleep(5)
                        self.market_adapter.reconnect_client()
                print("Portafolio actual ",self.portafolio_actual)
                operables = len(self.symbols_usables)
                dic_data = self.datahandler.get_live("15m",10000*operables)
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.strategy_dataset = self.strategy.math_live(dic_data)
                last_timestamp = self.strategy_dataset["BTCUSDT"].index[-1]
                print(last_timestamp)
                to_close_positions = self.strategy.check_exits(last_timestamp,self.strategy_dataset,self.portafolio_actual)
                for posicion in to_close_positions:
                    self.close_trade(posicion)
                    print(f"Trade cerrado {posicion}")
                self.portafolio_actual = self.market_adapter.order_manager.get_posiciones()
                to_open_positions = self.strategy.check_entries(last_timestamp,self.strategy_dataset,self.portafolio_actual)
                for posicion in to_open_positions:
                    self.send_trade(posicion[0],posicion[1])
                    print(f"Trade enviado para {posicion[0]},{posicion[1]}")

                print(to_open_positions)
                self.portafolio_actual = self.market_adapter.order_manager.get_posiciones()
                equity = self.market_adapter.order_manager.get_balance_total()
                self.logger.set_status(equity,self.portafolio_actual)
                
                print(now)
                self.lock.release()
                event.clear()
            else:
                time.sleep(1)

    def stream_market(self,event):
        self.market_adapter.stream_market(event)
        
    def set_restart(self):
        self.restart = True
    def main_event(self):
        evento = threading.Event()
        evento_bot = threading.Event()

        self.logger.write("PROCESS","starting main event")

        self.thread_operar = threading.Thread(target = self.operar,args =(evento,))
        self.thread_market = threading.Thread(target = self.stream_market,args =(evento,))
        self.thread_telegram = threading.Thread(target = self.telegram_bot.poll,args = (evento_bot,))
        
        self.thread_operar.start()
        self.thread_market.start()
        self.thread_telegram.start()

        while True:
            if not self.thread_telegram.is_alive():
                print("Iniciando bot de telegram")
                self.logger.write("PROCESS","restarting telegram bot")
                self.telegram_bot.set_restart()
                time.sleep(10)
                evento_bot = threading.Event()
                self.thread_telegram = threading.Thread(target = self.telegram_bot.poll,args = (evento_bot,))
                self.thread_telegram.start()
                
            if evento_bot.isSet():
                print("Event Set")
                self.telegram_bot.queue = self.process_events(self.telegram_bot.queue)
                evento_bot.clear()
            else:
                time.sleep(5)


    def send_trade(self,symbol,side):
        risk_management = self.strategy.risk_management
        amount = self.market_adapter.order_manager.get_balance_total()
        order = self.strategy.set_risk_management(amount,[(symbol,side)])[0]
        risk_dict = self.market_adapter.order_manager.set_risk_management(symbol,side,order)
        monto_trade = self.market_adapter.order_manager.calculate_amount(order["amount"],symbol,order["leverage"])
        self.market_adapter.order_manager.create_order(symbol,side,monto_trade,
                            take_profit  = risk_dict["take_profit_price"],
                            stop_loss = risk_dict["stop_loss_price"],
                            leverage = risk_management["leverage"])
        print("Trade realizado con exito")
        symbol = symbol
        if side == 1:
            accion = "BUY"
        else:
            accion = "SELL"
        monto = order["amount"]
        leverage = order["leverage"]
        actual = risk_dict["actual_price"]
        self.logger.write("MARKET",f"{accion} {symbol} at {actual} X{leverage}")

    def close_trade(self,symbol):
        posiciones = self.market_adapter.order_manager.get_posiciones()

        symbols = [par["symbol"] for par in posiciones]
        
        
        while symbol in symbols:
                pos = [par for par in posiciones if par["symbol"] == symbol][0]
                print(pos)
                amount = float(pos["margin"])
                side = float(pos["amount"])
                if side > 0:
                    side = 1
                else:
                    side = -1
                try :
                    self.market_adapter.order_manager.close_position(symbol,amount,side*-1)
                except:
                    self.market_adapter.order_manager.close_position(symbol,amount,side)
                posiciones = self.market_adapter.order_manager.get_posiciones()
                symbols = [par["symbol"] for par in posiciones]
        self.market_adapter.order_manager.eliminar_orden(symbol)
        self.logger.write("MARKET",f"{symbol}  position closed")

    def process_events(self,queue):
        while len(queue) > 0:
            evento = queue.pop(0)
            if evento == "/balance":
                value = self.market_adapter.order_manager.get_balance()
                message = f"Balance value : {value}"
                self.telegram_bot.enviar_mensaje(message)
            elif evento == "/restart":
                print("Restarting")
                self.logger.write("PROCESS","restarting threads")
                evento = threading.Event()
                x  = 0
                while  x <2:
                    x = 0
                    print("Restarting threads")
                    if self.thread_operar.is_alive():
                        self.set_restart()
                    else :
                        x += 1.5
                    if self.thread_market.is_alive():
                        self.market_adapter.set_restart()
                    else:
                        x+=1
                    print(x)
                    time.sleep(2)

                self.thread_operar = threading.Thread(target = self.operar,args =(evento,))
                self.thread_market = threading.Thread(target = self.stream_market,args =(evento,))
                self.thread_operar.start()
                self.thread_market.start()
                mensaje = "Threads Restarted"
                self.telegram_bot.enviar_mensaje(mensaje)
            elif evento == "/status":
                mensaje = self.logger.get_status()
                self.telegram_bot.enviar_mensaje(mensaje)
            elif evento == "/positions":
                posiciones = self.market_adapter.order_manager.get_positions()
                message = f"Posiciones actuales : \n {posiciones}"
                self.telegram_bot.enviar_mensaje(message)
            elif evento == "/menu":
                mensaje = """Comandos : 
                            menu
                            positions
                            restart
                            status
                            """
                self.telegram_bot.enviar_mensaje(mensaje)
        return queue
if __name__ == '__main__':
    # asyncio.run(streaming())
    ma =MarketAdapter(ADAPTERS_DICT)
    tg_bot = TelegramMessager(CARPETA_APIS)
    cep = ComplexEventProcessing(ma,tg_bot)
    cep.main_event()

    # logger.write("MARKET","buy BTCUSDT at 50000")



    # print(cep.market_adapter.order_manager.get_posiciones()[0])
    # # cep.send_trade("BTCUSDT",-1)
    # # print("Trade enviado")
    # # time.sleep(20)
    # cep.close_trade("BTCUSDT")


