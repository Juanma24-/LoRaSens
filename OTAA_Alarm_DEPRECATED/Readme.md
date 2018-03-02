README (DEPRECATED)
================================================================================
Esta carpeta contiene una app desarrollada para Lopy + Pysense, en la cual se leen los
sensores disponibles en la placa de forma períodica y se publican en formato
RAW vía LoRaWAN a un network server.  
Para conseguir la conectividad vía LoRaWan se ha hecho uso de otro dispositivo
Lopy con el software lorananogateway también disponible en este repositorio.  
El objetivo de este archivo es explicar la estructura de esta app y dar las
instrucciones necesarias para configurar el dispositivo Lopy para realizar la
conexión con éxito primero con el Network Server TTN y posteriormente con el
cloud vía MQTT.

__IMPORTANTE__

Tutoriales de inicio:
* https://github.com/ttn-liv/devices/wiki/Getting-started-with-the-PyCom-LoPy  
* https://docs.pycom.io/pycom_esp32/index.html

Compilación sin placa
--------------------------------------------------------------------------------
Para compilar una aplicación sin necesidad de tener conectada un dispositivo
LoPy al ordenador, es necesario instalar [pycom-micropython-sigfox](https://github.com/pycom/pycom-micropython-sigfox)
(pasos a seguir al final de este documento), introducir los archivos de la app
dentro de la carpeta _esp32/frozen_ y compilar de la siguiente forma:  
~~~
cd esp32
make BOARD=LOPY LORA_BAND=USE_BAND_868 BTYPE=release TARGET=boot clean
make BOARD=LOPY LORA_BAND=USE_BAND_868 BTYPE=release TARGET=boot
make BOARD=LOPY LORA_BAND=USE_BAND_868 BTYPE=release TARGET=app
~~~
Arquitectura de la app
--------------------------------------------------------------------------------
La app se puede dividir en dos grupos, archivos de programa y librerías de
control de sensores. El árbol de archivos es el siguiente:  
* OTAA->  
    * boot.py (Inicia y selecciona el archivo main)  
    * Lectura_Sensores_0.py (Pruebas de Sensores)  
    * otaa_node_0.py (conexión con TTN)  
    * LibreríaSensores ->
      * GestionSensores.py
      * Acelerometro.py
      * LIS2HH12.py
      * HumedadSensor.py  
      * SI7006A20.py
      * LuzSensor.py  
      * LTR329ALS01.py
      * PresionSensor.py  
      * MPL3115A2.py

Los tres primeros archivos deben ir colocados en la raíz del sistema de archivos
del módulo LoPy (/flash). Los archivos de la carpeta "Librería Sensores" serán
colocados en la ruta /flash/lib (Método de transferencia de archivos al final).  
El archivo boot.py selecciona cuál será el archivo que contenga el código
principal del programa. Se puede seleccionar _otaa\_node\_0.py_
(programa principal) o _Lectura\_Sensores\_0.py_ (código prueba)
comentando/descomentando un par de líneas.  
Dada la arquitectura de las librerías, el usuario solo puede tener acceso libre
a las funciones alojadas en el archivo _GestionSensores.py_. Desde este archivo
se pueden realizar las siguientes tareas:  
* Obtener las últimas lecturas de los distintos sensores.  
  ~~~
  crearjson(self)
  ~~~
  Mediante la función _crearjson_ se obtiene un tupple con los valores de los
  diferentes sensores si son diferentes a la última medida realizada. El tuple
  contiene los valores en el siguiente orden:  
  Luz, Presión, Humedad, Temperatura, Batería  
* Calcular el intervalo de Publicacion  
  ~~~
  intervaloMinimo(self)
  ~~~
  Calcula el intervalo de publicación mínimo a partir de los valores de los
  intervalos de los diferentes sensores.
* Modificar intervalos de toma de datos
  ~~~
  modificarIntervalo(self,intervalo,sensor='')
  ~~~
  Se puede modificar el intervalo de toma de datos de cualquier sensor
  introduciendo el nuevo intervalo (segundos) y la inicial del sensor a
  modificar según la siguiente lista:  
    * L: Luminosidad  
    * P: Presión  
    * H: Humedad  
    * T: Temperatura  
    * A: Aceleración  
    * G: Giro  
* Activar/Desactivar Sensor  
  ~~~
  activarSensor(self,sensor='',en=0)
  ~~~
  Se puede activar o desactivar cualquier sensor solo enviando 0|1 y la inicial
  del sensor sobre el que se actuará (según la lista anterior).  

Uso de la app (envío/recepción de datos)
--------------------------------------------------------------------------------
El envío/recepción de datos desde/hacia el nodo de la red se realiza mediante el
protocolo LoRaWAN, por lo que para optimizar el consumo de energía, el uso del
gateway y no sobrepasar las limitaciones que imponen algunos Network Servers, se
 hace necesario reducir el tamaño de los mensajes al máximo.  
### Envío
El envío se realiza mediante el método _send_ de un socket previamente creado.
En el archivo _ota\_node\_0.py_ el envío de datos está programado para enviar un
 tuple que contiene unicamente los valores de los sensores en un orden
 especifico. Este tuple es la minima cantidad de información que se puede
 enviar, conteniendo el payload del mensaje LoRaWAN solo la información
 necesaria.
### Recepeción
La recepción de datos se realiza mediante un procedimiento más complejo que el
envío. Para la recepción se ha diseñado un handler que es activado cada vez que
se detecta un evento de recepción. Este handler gestiona el mensaje de la
siguiente forma:
* Mensaje de activación/desactivación de sensores  
  El mensaje cosnta unicamente de 2 bytes. El primero de ellos corresponde al
  código ASCII de la letra 'A' en hexadecimal (0x41). Este primer byte se usará
  para saber que acción debe ser llevada a cabo, pero también como "paridad"
  evitando mensajes corruptos.  
  El segundo byte corresponde a los sensores que deben ser activados o
  desactivados, en el siguiente orden:
     No Usado - No Usado - Luminosidad - Presión - Humedad - Temperatura -
     Aceleración - Giro
  Un 1 significará activo y un 0 significará desactivado.
  E.g: `41 18` =  L= P= H= T= A= G=
* Mensaje de modificación de intervalo  
  Este mensaje no tiene una longitud máxima definida, ya que depende del numero
  de segundos del intervalo en representación hexadecimal. La longitud mínima es
  de 3 bytes, correspondiendo el primer byte al código ASCII de la letra 'I' en
  hexadecimal (0x49). El segundo byte selecciona el sensor cuyo intervalo será
  modificado. Al igual que con el primero, mediante el código ASCII de la letra
  del sensor (L=0x4C P=0x50 H=0x48 T=0x54 A=0x41 G=0x47). El resto del payload
  corresponde al numero de segundos del intervalo en formato hexadecimal.  
  E.g: `49 4C 64`= I L 100

__IMPORTANTE__
Aunque las codificaciones estan realizadas en formato hexadecimal, el
dispositivo las convierte a decimal, por lo que hay que tener cuidado si se
comparan cadenas de números.



MQTT
--------------------------------------------------------------------------------
Para comprobar si el dispositivo y el Network Server están enviando los mensajes
 de forma corrrecta así como enviar mensajes downlink, se puede configurar
 Mosquitto de la siguiente forma:

__ATENCIÓN!! TODAS ESTAS ÓRDENES ESTÁN CONFIGURADAS PARA USAR THETHINGSNETWORK
COMO NETWORK SERVER__

### Subscripción
```
mosquitto_sub -h eu.thethings.network:1883 -t '<AppId/devices/<DevID>/up' -u
'<AppID>' -P '<AppKey>' -v
```
Todos los campos a rellenar pueden ser encontrados en la descripción de la app
creada en TTN.

### Publicación
La publicación se realizará a través del broker privado hacia el Network Server.
A partir de Network Server o más concretamente desde el Gateway, el protocolo
MQTT será sustituido a LoRaWAN, disminuyendo el payload a un vector de números
con un orden y un significado concreto y conocido.
Para enviar un comando de los definidos en el apartado anterior, se debe mandar
la siguiente orden (ejemplo relaizado en Mosquitto):
~~~
mosquitto_pub -h <Region>.thethings.network -t '<AppID>/devices/<DevID>/down' -u
 '<AppID>' -P '<AppKey>' -m '{"payload_raw":""}'
~~~
El campo `payload_raw`debe estar codificado en Base64. Dado que las órdenes han
sido diseñada en formato bytes (hexadecimal), se deben convertir utilizando una
herramienta como [esta](http://tomeko.net/online_tools/hex_to_base64.php?lang=en)
CONFIGURACIÓN NANOGATEWAY
-------------------------------------------------------------------------------
Para configurar el dispositivo LoPy que actuará como NanoGateway, solo hay que
comentar/descomentar algunas líneas del archivo _config.py_. Las líneas
corresponden a la configuración de ID Gateway, dirección del Network Server y
puerto de entrada/salida del Netwoek Server, para los dos servidores utilizados:
 The Things Network y Loriot.
Es importante mencionar que dado que el gateway hace uso de la conexión Wifi del
dispositivo, una vez configurado ya no se estará accesible esta red y por lo
tanto el servidor FTP tampoco. Para accerlo accesible de nuevo se ha de conectar
el pin P12(G28) a 3V3 al durante los 1-3 primeros segundos del inicio del
dispositivo, y luego retirar el puente hecho. Esta acción cargará la
configuración del firmware base del dispositivo.

USO SEVER FTP (Paso archivos a LoPy)
--------------------------------------------------------------------------------
Para pasar archivos a LoPy solo hay que conectarse a su punto WiFy propio y
configurar un cliente FTP (e.g Filezilla) con las siguientes propiedades:  
* Host : 192.168.4.1
* User: micro
* Password: python
* Only use plain FTP (insecure)
* Transfer Mode: Passive

Si no aparece el punto WiFy se tiene que poner la placa en modo seguro llevando
la entrada G28 a 3V3 (solo con expansion Board).

INSTALAR SOFTWARE DE COMPILACIÓN
--------------------------------------------------------------------------------
1.-  __Obtener pycom-micropython-sigfox__
~~~
git clone https://github.com/pycom/pycom-micropython-sigfox.git
cd pycom-micropython-sigfox
git submodule update --init
~~~
2.- __Instalar Toolchain__
~~~
sudo easy_install pip
sudo pip install pyserial
~~~
Descargar:
https://dl.espressif.com/dl/xtensa-esp32-elf-osx-1.22.0-61-gab8375a-5.2.0.tar.gz
~~~
mkdir -p ~/esp
cd ~/esp
tar -xzf ~/Downloads/xtensa-esp32-elf-osx-1.22.0-61-gab8375a-5.2.0.tar.gz
~~~
3.- __Fijar Variables de Entorno__  
Modificar el archivo .profile (dentro de la carpeta raíz ~) y añadir la
siguiente línea:
~~~
export PATH=$PATH:$HOME/esp/xtensa-esp32-elf/bin
export IDF_PATH=~/esp/pycom-esp-idf
~~~
4.- __Obtener Espressif__
~~~
cd ~/esp
git clone https://github.com/pycom/pycom-esp-idf.git
cd ~/esp/esp-idf
git submodule update --init
~~~
5.- __Compilar mpy-cross__  
~~~
cd pycom-micropython-sigfox/mpy-cross
make all
~~~
