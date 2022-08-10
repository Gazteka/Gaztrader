# Gaztrader

[Este proyecto es netamente educativo y su propósito no es lucrar, úselo bajo su propia responsabilidad ]
*Cualquier comentario, feedback o reseña positiva es más que bien recibida


Gaztrader es un software creado en python, para desarrollar sistemas de inversion en criptomonedas, especificamente en los futuros de Binance, aunque puede sser extendido a otros brókers tanto de acciones y forex, siempre y cuando se pueda obtener datos de los instrumentos financieros que se deseen operar y una API (o algún otro método) que permita enviar órdenes al bróker respectivo.



<h2> Clases y funcionalidades <\h2>

  <h3> Complex Event Processing(CEP) <\h3>
    
Esta clase se encarga de gestionar a todas las demas, es la base sobre la que funcionan las otras clases, se encarga de gestionar los datos en vivo,  recibidos a traves del Market Adapter, cuando se cierra una vela, se encarga de ejecutar la/s estrategia/s para verificar si existen señales de compra y/o venta.Por otro lado la informacion es extraida de la base de datos y entregada a la estrategia a través de un DataHandler, esto ya que es posible que una estrategia necesite informacion adicional a la de las velas, como la capitalizacion de mercado o de otros indicadores como el Fear & Greed Index.
    
    
