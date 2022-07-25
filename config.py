import pandas as pd
import pandas_ta as ta
import numpy as np
import matplotlib.pyplot as plt
import os
import json
import datetime
import time
import sqlite3
from binance import Client
import random
import requests
import sys
from PyQt5.QtWidgets import (
    QComboBox, QGridLayout, QLabel, QScrollArea, QWidget, QLineEdit, QHBoxLayout,QCheckBox,
    QVBoxLayout, QPushButton, QApplication,QGroupBox,QTableWidget,QTableWidgetItem,QTabWidget)
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal,QTimer,QRect,QThread,QObject
from PyQt5.QtGui import QMovie, QPixmap,QFont,QPainter,QColor,QPen
from PyQt5.QtCore import Qt, pyqtSignal
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import unicorn_binance_websocket_api
import threading
#Carpetas
CARPETA_APIS = "Apis"
CARPETA_DATABASES = "Databases"

#Adapters
ADAPTADORES_DISPONIBLES = ["BinanceFutures"]

#Imagenes
BACKGROUND_WALLPAPER = os.path.join("frontend","welcome_wallpaper.jpg")