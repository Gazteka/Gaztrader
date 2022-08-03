from config import  * 

class OrderManager:

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
   

    def close_position(self,symbol,amount,side = "SELL"):
        if side == 1:
            side = "BUY"
        elif side == -1:
            side = "SELL"
        

        amount = self.calculate_amount(amount*2,symbol,3)
        self.binance_client.futures_create_order(symbol = symbol,type = "MARKET",side = side,quantity = amount,reduceOnly = "true")
        pass



    

if __name__ =="__main__":
    pass