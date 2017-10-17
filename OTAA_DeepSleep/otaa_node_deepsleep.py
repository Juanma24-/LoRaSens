#OTAA Node LoRaWAN with DeepSleep
#Juan Manuel Galán Serrano
#UPC-ALSTOM 2017
#------------------------------------------------------------------------------#
from network import LoRa
import socket
import binascii
import struct
import pycom
import time
import machine
#------------------------------------------------------------------------------#
#Librerias de Pysense y sensores
from pysense import Pysense
from SI7006A20 import SI7006A20
from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE
#------------------------------------------------------------------------------#
class Node:
    def __init__(self,sleep_time):
        self.lora = None                                                        # Instancia de Lora (sin inicializar)
        self.s = None                                                           # Instancia Socket (sin inicializar)
        self.sleep_time = sleep_time                                            # Intervalo de inactividad
        self.dr = 5                                                             # Data Rate (defecto 5)
        self.py = Pysense()                                                     # Instancia de Pysense
        self.mp = MPL3115A2(self.py,mode=PRESSURE)                              # Instancia Sensor de Presión
        self.si = SI7006A20(self.py)                                            # Instancia Sensor de Humedad y tempertura
        self.lt = LTR329ALS01(self.py)                                          # Instancia Sensor de Luminosidad
#------------------------------------------------------------------------------#
    def connect(self,app_eui, app_key):
        """
        Connect device to LoRa.
        Set the socket and lora instances.
        """
        # Disable blue blinking and turn LED off
        pycom.heartbeat(False)
        # Initialize LoRa in LORAWAN mode
        self.lora = LoRa(mode = LoRa.LORAWAN)
        # Set the 3 default channels to the same frequency (must be before
        # sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Join a network using OTAA (Over the Air Activation)
        self.lora.join(activation = LoRa.OTAA, auth = (app_eui, app_key),
                    timeout = 0)                                                #login for TheThingsNetwork see here:
                                                                                #https://www.thethingsnetwork.org/forum/t/lopy-otaa-example/4471
        # Wait until the module has joined the network
        while not self.lora.has_joined():
            print("Trying to join LoraWAN with OTAA")
            time.sleep(2.5)
        print ("LoraWAN joined! ")
        # save the LoRaWAN connection state
        self.lora.nvram_save()
#------------------------------------------------------------------------------#
    def send(self,data):
        """
        Send data over the network.
        """
        # Initialize LoRa in LORAWAN mode
        self.lora = LoRa(mode = LoRa.LORAWAN)
        # restore the LoRaWAN connection state
        self.lora.nvram_restore()
        # Create a LoRa socket
        print("Create LoRaWAN socket")
        self.s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        for i in range(3, 16):
            self.lora.remove_channel(i)
        # Set the 3 default channels to the same frequency
        # (must be before sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Set the LoRaWAN data rate
        self.s.setsockopt(socket.SOL_LORA, socket.SO_DR,self.dr)
        # selecting confirmed type of messages
        self.s.setsockopt(socket.SOL_LORA, socket.SO_CONFIRMED, True)
        # Make the socket non-blocking
        self.s.setblocking(False)

        try:
            self.s.send(str(data))
            time.sleep(2)                                                       #Espera para posible recepción
            rx = bytes(self.s.recv(128))                                        #Recepción de datos
            self.receive(rx=rx)
            self.lora.nvram_save()
        except OSError as e:
            if e.errno == 11:
                print("Caught exception while sending")
                print("errno: ", e.errno)
#------------------------------------------------------------------------------#
#Función de recepción de datos.Es activada tras la ventana de recepción
#posterior al envío.
    def receive(self,rx=None):
        if len(rx) == 0:                                                            #No hay mensaje de recepción
            pass
        else:
            if rx[0] == 73:                                                     #Orden de Cambio de intervalo (ASCII hex I=0x49 dec 73)
                print("Recibido cambio de intervalo %d"
                            %(int.from_bytes(rx[1:],'big')))
                self.sleep_time = int.from_bytes(rx[1:],'big')                  #Decodifica el valor del nuevo intervalo
                pycom.nvs_set('sleep_time',self.sleep_time)                     #Lo guarda en NVRAM
            elif rx[0] == 82:                                                   #Orden de Cambio Data Rate (ASCII hex R=0x52 dec 87)
                print("Cambiando Data Rate %d" %(int.from_bytes(rx[1:],'big')))
                self.dr = int.from_bytes(rx[1:],'big')                          #Decodifica el valor del nuevo data Rate
            else:
                pass
#------------------------------------------------------------------------------#
#Función de lectura de medidas. Los sensores ya han sido inicializados al
#crear la instancia de la clase Node
    def readsens(self):
        reading = [0,0,0,0,0]
        reading[0] = int(self.lt.light()[0])                                    #Primer Elemento Lista: Luminosidad (entero)
        reading[1] = int(self.mp.pressure())                                    #Segundo Elemento Lista: Presión (entero)
        reading[2] = round(self.si.humidity(),2)                                #Tercer Elemento Lista: Humedad (dos decimales)
        reading[3] = round(self.si.temperature(),2)                             #Cuarto Elemento Lista: Temperatura (dos decimales)
        reading[4] = round(self.py.read_battery_voltage(),2)                    #Quinto Elemento Lista: Voltaje (dos decimales)
        return reading
#------------------------------------------------------------------------------#
#Codigo principal
app_eui = binascii.unhexlify('70B3D57EF00042A4')                                #ID de la app. (Seleccionada por el usuario)
app_key = binascii.unhexlify('3693926E05B301A502ABCFCA430DA52A')                #Clave de la app para realizar el handshake. Única para cada dispositivo.
ajuste = 6                                                                      #Numero de segundos para que el intervalo sea exacto en el Network Server
#Según el modo de inicio, se realizan unas serie de acciones u otras.
if machine.reset_cause() == machine.DEEPSLEEP_RESET:                            #Si despierta tras deepsleep
    print('woke from a deep sleep')
    sleep_time = pycom.nvs_get('sleep_time')                                    #Obtiene el valor de la variable sleep_time guardado en NVRAM
    n = Node(sleep_time)                                                        #Crea una instancia de Node
    lecturas = n.readsens()
    print("Enviando lecturas")
    n.send(lecturas)                                                            #Envío de las lecturas
    print("Lecturas Enviadas")
    machine.deepsleep((sleep_time-ajuste)*1000)                                #Dispositivo enviado a Deepsleep
    #n.py.setup_sleep(sleep_time-ajuste)
    #n.py.go_to_sleep()
else:                                                                           #Si viene de Boot o Hard Reset
    print('power on or hard reset')
    sleep_time = 30                                                             #Valor por defecto de sleep_time
    pycom.nvs_set('sleep_time', 30)                                             #Guarda el valor por defecto de sleep_time en NVRAM
    n = Node(sleep_time)                                                        #Crea una instancia de Node
    n.connect(app_eui, app_key)                                                 #Join LoRaWAN with OTAA
    machine.deepsleep((sleep_time-ajuste)*1000)                                #Dispositivo enviado a Deepsleep
    #n.py.setup_sleep(sleep_time-ajuste)
    #n.py.go_to_sleep()
