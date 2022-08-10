# Gaztrader

[Este proyecto es netamente educativo y su propósito no es lucrar, úselo bajo su propia responsabilidad ]
*Cualquier comentario, feedback o reseña positiva es más que bien recibida


Gaztrader es un software creado en python, para desarrollar sistemas de inversion en criptomonedas, especificamente en los futuros de Binance, aunque puede sser extendido a otros brókers tanto de acciones y forex, siempre y cuando se pueda obtener datos de los instrumentos financieros que se deseen operar y una API (o algún otro método) que permita enviar órdenes al bróker respectivo.



<h2> Clases y funcionalidades </h2>

  <h3> Complex Event Processing(CEP) </h3>
https://raw.githubusercontent.com/Gazteka/Gaztrader/main/Diagrams/cep.png
[Diagrama de clases de cep]

Esta clase se encarga de gestionar a todas las demas, es la base sobre la que funcionan las otras clases, se encarga de gestionar los datos en vivo,  recibidos a traves del Market Adapter, cuando se cierra una vela, se encarga de ejecutar la/s estrategia/s para verificar si existen señales de compra y/o venta.Por otro lado la informacion es extraida de la base de datos y entregada a la estrategia a través de un DataHandler, esto ya que es posible que una estrategia necesite informacion adicional a la de las velas, como la capitalizacion de mercado o de otros indicadores como el Fear & Greed Index.

<h3> Market Adapter </h3>
https://raw.githubusercontent.com/Gazteka/Gaztrader/main/Diagrams/market_adapter.png

[Diagrama de clases de market adapter]
El market adapter como lo menciona su nombre se encarga de ser un adaptador para el mercado, sin embargo se utiliza un patrón de observer respecto a los adaptadores, en realidad son los adaptadores los que procesan y ajustan la infomacion recibida para poder ser utlizada, el market adapter simplemente se encarga de actualiar y enviar los requerimientos necesarios al/los adaptador/es.Los adaptadores por su parte se encargan de descargar datos históricos y stremear datos en vivo 


<h3>Order Manager</h3>
El gestor de ordenes se encarga de gestionar el riesgo tanto individual de las estrategias como el riesgo conjunto debido a la correlación, calcula el monto a comprar en base al apalancamiento y el precio actual.Junto con esto establece las ordenes de stop loss y take profit para cada operacion.

<h3>Estrategias</h3>
Las estrategias son bastante sencillas, solo tienen 3 funciones, chequear las entradas, las salidas y establecer el riesgo en porcentaje, además de calcular los indicadores necesarios para establecer las señales de compra y venta.


<h2> Extras </h2>
<h3>Devset </h3>
Esta carpeta contiene una clase de Backtester para probar y crear estrategias.La estrategia de muestra llamada TripleTimeBands,es una estrategia bastante simple que utiliza 3 timeframes,12h, 2h y 15m, clasifica el mercado en 4 fases en base a la media movil y la volatilidad de los ultimos 50 días.Estos indicadores permiten clasificar el mercado primero en 2 fases, alcista si el cierre esta por sobre la media movil y bajista en otro caso. A partir de esto la volatilidad nos permite generar 4 estados , Tendencia alcista (Alcista + volatilidad) , Rango Alcista (alcista sin volatilidad), tendencia Bajista (bearish trend) y bajista no volatil.(Bearish range)



A partir de esto la estrategia es simple, si el mercado se encuentra en una tendencia alcista o bajista, se espera a que en el timeframe de 2h el cierre sea fuera de las bandas de bollinger, establenciendo posiciones a favor de la tendencia cuando el cierre se sale de las bandas.
Esto nos permite aprovechar la alta volatilidad y fuertes y marcados ciclos generados en las criptomonedas.
