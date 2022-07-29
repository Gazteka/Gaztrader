from sqlite3 import adapters
from config import  * 
from adapters import * 
from order_manager import OrderManager

ADAPTERS_DICT = {"BinanceFutures":BinanceFuturesAdapter}

class MarketAdapter:
    def __init__(self,adapters_dict):
        self.adapters_dict = adapters_dict
        self.adaptadores = {}
        self.iniciar_adaptadores()
        cliente  = self.adaptadores["BinanceFutures"].binance_client
        self.order_manager = OrderManager(cliente)
        
    def iniciar_adaptadores(self):
        for adapter in self.adapters_dict:
            individual_adapter = self.adapters_dict[adapter]
            self.adaptadores[adapter] = individual_adapter()
            print(f"{adapter} adapter listo !")


    def update(self):
        for adapter in self.adaptadores:
            self.adaptadores[adapter].actualizacion_completa()

    def set_restart(self):
        self.reconnect_client()
        for adapter in self.adaptadores:
            self.adaptadores[adapter].set_restart()

        print("Restart setted")
    def stream_market(self,event):
        self.adaptadores["BinanceFutures"].stream_15m(event)
    def get_local(self,symbols,n,timeframe):
        for adapter in self.adaptadores:
            dic_data = self.adaptadores[adapter].get_local(symbols,n,timeframe)
        return dic_data
    
    def reconnect_client(self):
        for adapter in self.adaptadores:
            self.adaptadores[adapter].reconnect_client()
        cliente  = self.adaptadores["BinanceFutures"].binance_client
        self.order_manager = OrderManager(cliente)
    
if  __name__=='__main__':

    ma =MarketAdapter(ADAPTERS_DICT)
    ma.update()
    


