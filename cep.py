from config import * 
import asyncio
from market_adapter import MarketAdapter, ADAPTERS_DICT
from Devset.strategies import DataHandler, TripleTimeBands

def convert_unix(timestamp):

    date = datetime.datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d %H:%M:%S")
    return date

class Logger:
    def __init__(self,ruta_logs):
        self.ruta_logs = ruta_logs 


class ComplexEventProcessing:
    def __init__(self,market_adapter):
        self.market_adapter = market_adapter
        self.symbols_usables = ["BTCUSDT","ETHUSDT"]
        self.timeframes_usables = ["kline_15m"]
        self.strategy  = TripleTimeBands()
        self.lock = threading.Lock()
        db_file = os.path.join("Databases","BinanceFutures.db")
        self.datahandler = DataHandler(db_file)
    
    def operar(self,event):
        while True:
            if event.isSet():
                time.sleep(2)
                print("Obteniendo data")
                self.lock.acquire()
                dic_data = self.datahandler.get_local("15m",10000)
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.strategy_dataset = self.strategy.math(dic_data)
                last_timestamp = self.strategy_dataset["BTCUSDT"].index[-1]
                print(last_timestamp)
                to_open_positions = self.strategy.check_entries(last_timestamp,self.strategy_dataset,[])
                # print(dic_data)
                print(to_open_positions)
                
                print(now)
                self.lock.release()
                event.clear()
            else:
                time.sleep(1)

    def stream_market(self,event):
        self.market_adapter.stream_market(event)
    def main_event(self):
        evento = threading.Event()
        thread_operar = threading.Thread(target = self.operar,args =(evento,))
        thread_market = threading.Thread(target = self.stream_market,args =(evento,))
        thread_operar.start()
        thread_market.start()


if __name__ == '__main__':
    # asyncio.run(streaming())
    ma =MarketAdapter(ADAPTERS_DICT)

    cep = ComplexEventProcessing(ma)
    cep.main_event()


