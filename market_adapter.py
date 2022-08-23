from sqlite3 import adapters
from config import  * 
from adapters import * 
from order_manager import OrderManager

ADAPTERS_DICT = {"BinanceFutures":BinanceFuturesAdapter2}

class MarketAdapter:
    def __init__(self,adapters_dict):
        self.adapters_dict = adapters_dict
        self.adaptadores = {}
        self.iniciar_adaptadores()

        
    def iniciar_adaptadores(self):
        for adapter in self.adapters_dict:
            individual_adapter = self.adapters_dict[adapter]
            self.adaptadores[adapter] = individual_adapter()
            print(f"{adapter} adapter listo !")


    def update(self,timeframe):
        for adapter in self.adaptadores:
            self.adaptadores[adapter].full_update(timeframe )

    def set_restart(self):
        self.reconnect_client()
        for adapter in self.adaptadores:
            self.adaptadores[adapter].set_restart()

        print("Restart setted")
    def stream_market(self,symbols_usables,klines,event):
        
        self.adaptadores["BinanceFutures"].full_update("15m")
        self.adaptadores["BinanceFutures"].full_update("15m")
        self.adaptadores["BinanceFutures"].stream_market(symbols_usables,klines,event)


    def get_local(self,symbols,n,timeframe):
        for adapter in self.adaptadores:
            dic_data = self.adaptadores[adapter].get_local(symbols,n,timeframe)
        return dic_data
    
    def reconnect_client(self):
        for adapter in self.adaptadores:
            self.adaptadores[adapter].reconnect_client()

    def get_margin(self,broker):
        adaptador = self.adaptadores[broker]
        balance = adaptador.get_balance_total()
        disponible = adaptador.get_balance_disponible()
        return disponible/balance

    def calculate_margin_after_trade(self,broker,amount):
        adaptador = self.adaptadores[broker]
        balance = adaptador.get_balance_total()
        disponible = adaptador.get_balance_disponible()
        margin_after_trade = (disponible-amount)/balance
        return margin_after_trade
    
    def verify_contract_space(self,broker,symbol):
        adaptador = self.adaptadores[broker]
        portafolio = adaptador.get_portafolio()
        posiciones = [pos["symbol"] for pos in portafolio]
        if symbol in posiciones:
            return False
        else:
            return True
        
    def put_contract(self,broker,actual_portfolio,to_close_contracts):
        
        adaptador = self.adaptadores[broker]

        pass

    def call_contract(self,broker,actual_portfolio,to_open_contracts):

        adaptadores = self.adaptadores[broker]

        pass




if  __name__=='__main__':

    ma =MarketAdapter(ADAPTERS_DICT)
    ma.update()
    


