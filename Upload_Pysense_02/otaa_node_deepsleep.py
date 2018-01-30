#OTAA Node LoRaWAN with DeepSleep
#Juan Manuel Galán Serrano
#UPC-ALSTOM 2017
#------------------------------------------------------------------------------#
from network import LoRa
import socket
import binascii
import pycom
import time
import machine
from machine import WDT
from machine import Timer
from network import WLAN

#------------------------------------------------------------------------------#
#Librerias Pysense y sensores
from pysense import Pysense
from SI7006A20 import SI7006A20                                                 #Sensor Humedad y Temperatura
from LTR329ALS01 import LTR329ALS01                                             #Sensor Luminosidad
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE                               #Sensor Presión
#------------------------------------------------------------------------------#
#Codigos razon de inicio
WAKE_REASON_TIMER = 4
WAKE_REASON_PUSH_BUTTON = 2
#------------------------------------------------------------------------------#
class Node:
    def __init__(self,sleep_time,data_rate,pysense):
        self.lora = None                                                        # Instancia de Lora (sin inicializar)
        self.s = None                                                           # Instancia Socket (sin inicializar)
        self.sleep_time = sleep_time                                            # Intervalo de inactividad
        self.dr = data_rate                                                     # Data Rate (defecto 5)
        self.py = pysense                                                       # Instancia de Pysense
        self.lt = LTR329ALS01(self.py)                                          # Instancia Sensor de Luminosidad
        self.mp = MPL3115A2(self.py,mode=PRESSURE)                              # Instancia Sensor de Presión
        self.si = SI7006A20(self.py)                                            # Instancia Sensor de Humedad y tempertura

#------------------------------------------------------------------------------#

#------------------------------------------------------------------------------#
#Función de lectura de medidas. Los sensores ya han sido inicializados al
#crear la instancia de la clase Node
    def readsens(self):
        pressure = (int(self.mp.pressure())-90000).to_bytes(2,'little')                     #Segundo Elemento Lista: Presión (entero)
        humidity = int(round(self.si.humidity(),2)*100).to_bytes(2,'little')                #Tercer Elemento Lista: Humedad (dos decimales)
        temperature = int(round(self.si.temperature(),2)*100).to_bytes(2,'little')          #Cuarto Elemento Lista: Temperatura (dos decimales)
        battery = int(round(self.py.read_battery_voltage(),2)*100-300).to_bytes(2,'little') #Quinto Elemento Lista: Voltaje (dos decimales)
        light = int(self.lt.light()[0]).to_bytes(2,'little')                                #Primer Elemento Lista: Luminosidad (entero)
        reading = light+pressure+humidity+temperature+battery                   #Union de tipos bytes
        print(reading)
        return reading
#------------------------------------------------------------------------------#
#Codigo principal
                                                         #Desactiva el heartbeat
app_eui = binascii.unhexlify('70B3D57EF00042A4')                                #ID de la app. (Seleccionada por el usuario)
dev_eui = binascii.unhexlify('0032140A05C8D228')
app_key = binascii.unhexlify('1BCB628F002E926C77E9FDED7EB2C87C')                #Clave de la app para realizar el handshake. Única para cada dispositivo.
ajuste = 10                                                                     #Numero de segundos para que el intervalo sea exacto en el Network Server
                                                                                #TODO: REAL TIME
py = Pysense()
#------------------------------------------------------------------------------#
#Según el modo de inicio, se realizan unas serie de acciones u otras.
if py.get_wake_reason() == WAKE_REASON_TIMER:                                   #Si despierta tras deepsleep
    print('Woke from a deep sleep R:%d'%(WAKE_REASON_TIMER))

    try:
        sleep_time = pycom.nvs_get('sleep_time')                                #Obtiene el valor de la variable sleep_time guardado en NVRAM
        data_rate = pycom.nvs_get('data_rate')
    except 0:                                                                   #No se consigue obtener el valor (ERROR INFO: https://forum.pycom.io/topic/1869/efficiency-of-flash-vs-nvram-and-some-nvs-questions/3)
        print("Error: Sleep Time / Data Rate could not be recovered. Setting default value")
        sleep_time = 300                                                        #Se le da el valor por defecto
        data_rate = 5
        pycom.nvs_set('sleep_time', sleep_time)                                 #Guarda el valor por defecto de sleep_time en NVRAM
        pycom.nvs_set('data_rate', data_rate)
    print("SleepTime & Data Rate recovered")

    try:
        n = Node(sleep_time,data_rate,py)                                       #Crea una instancia de Node
        print("Node Instance created sucesfully")
    except Exception:
        print("Node Instance could not be cretaed. Sleeping...")
        print('- ' * 20)
        n.py.setup_sleep(sleep_time-ajuste)
        n.py.go_to_sleep()                                                      #Dispositivo enviado a Deepsleep

    lecturas = n.readsens()
    n.py.setup_int_wake_up(rising=1,falling=0)                                  #Activa la interrupcion por Botón
    n.py.setup_sleep(sleep_time-ajuste)
    n.py.go_to_sleep()                                                          #Dispositivo enviado a Deepsleep

elif (py.get_wake_reason() == WAKE_REASON_PUSH_BUTTON):
    uart = UART(0, 115200)                                                      #Se activa la UART
    os.dupterm(uart)
    wlan = WLAN()
    wlan.init(mode=WLAN.AP, ssid='lopy-pysense', auth=(WLAN.WPA2,'lopy-pysense'), channel=7,antenna=WLAN.INT_ANT) #Inicia el servidor FTP

    print("Device entered into debugging mode")
    print("Please do not connect to battery")
    pycom.heartbeat(True)                                                       #Se activa el Heartbeat
    while(1):
        if py.button_pressed():
            print("Exit DEBUG MODE, reseting...")
            print('- ' * 20)
            machine.reset()

else:                                                                           #Si viene de Boot o Hard Reset
    print('Power on or hard reset')
    sleep_time = 300                                                            #Valor por defecto de sleep_time (Minimo segun Fair Acess Policy TTN)
    data_rate = 5
    pycom.wifi_on_boot(False)                                                   # disable WiFi on boot TODO: Intentar en versiones posteriores, da un Core Error.

    try:
        pycom.nvs_set('sleep_time', sleep_time)                                 #Guarda el valor por defecto de sleep_time en NVRAM
        pycom.nvs_set('data_rate', data_rate)
    except (None):
        print("Error: Value could not be stored")
        pass

    n = Node(sleep_time,data_rate,py)                                           #Crea una instancia de Node
    lecturas = n.readsens()                                                     #Envío de las lecturas
    n.py.setup_int_wake_up(rising=1,falling=0)                                  # Activa la interrupcion para el boton DEBUG
    n.py.setup_sleep(sleep_time-ajuste)                                         #Dispositivo enviado a Deepsleep
    n.py.go_to_sleep()
