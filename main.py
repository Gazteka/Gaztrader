from config import * 
from frontend.frontend_base import FrontendLogin,FrontendInicio
from backend import BackendLogin,BackendInicio
from market_adapter import MarketAdapter,ADAPTERS_DICT
def hook(type_error, traceback):
    print(type_error)
    print(traceback)




if __name__ == '__main__':
    sys.__excepthook__ = hook   
    app = QApplication(sys.argv)
    login = BackendLogin()
    inicio = BackendInicio(MarketAdapter(ADAPTERS_DICT))
    login.signal_ingresar.connect(inicio.abrir)
    sys.exit(app.exec())


