#ABP Node LoRaWAN with DeepSleep
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
        self.lora = None                                                        # Instancia LoRa (sin inicializar)
        self.s = None                                                           # Instancia de Socket (sin inicializar)
        self.sleep_time = sleep_time                                            # Intervalo de inactividad
        self.dr = 5                                                             # Data Rate (defecto 5)
        self.py = Pysense()                                                     # Instancia de Pysense
        self.mp = MPL3115A2(self.py,mode=PRESSURE)                              # Instancia Sensor de Presión
        self.si = SI7006A20(self.py)                                            # Instancia Sensor de Humedad y tempertura
        self.lt = LTR329ALS01(self.py)                                          # Instancia Sensor de Luminosidad
#------------------------------------------------------------------------------#
    def connect(self,dev_addr,nwk_swkey,app_swkey):
        """
        Connect device to LoRa.
        Set the socket and lora instances.
        """
        pycom.heartbeat(False)                                                  # Disable blue blinking

        self.lora = LoRa(mode = LoRa.LORAWAN)                                   # Initialize LoRa in LORAWAN mode
        # Remove all the non-default channels
        for i in range(3, 16):
            self.lora.remove_channel(i)
        # Set the 3 default channels to the same frequency
        # (must be before sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # join a network using ABP (Activation By Personalization)
        self.lora.join(activation=LoRa.ABP, auth=(dev_addr,
                        nwk_swkey, app_swkey))
        self.s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        # Set the LoRaWAN data rate
        self.s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)
        # Make the socket non-blocking
        self.s.setblocking(False)
        self.s.send(bytes([0x01,0x02,0x03]))
        # save the LoRaWAN connection state
        self.lora.nvram_save()
        print("Estado guardado en NVRAM")
#------------------------------------------------------------------------------#
    def send(self,data):
        """
        Send data over the network.
        """
        # Initialize LoRa in LORAWAN mode
        self.lora = LoRa(mode = LoRa.LORAWAN)
        # restore the LoRaWAN connection state
        self.lora.nvram_restore()
        # remove all the non-default channels
        for i in range(3, 16):
            self.lora.remove_channel(i)
        # Set the 3 default channels to the same frequency
        # (must be before sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Create a LoRa socket
        print("Create LoRaWAN socket")
        self.s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        # Set the LoRaWAN data rate
        self.s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)
        # Make the socket non-blocking
        self.s.setblocking(False)

        try:
            self.s.send(str(data))                                              #Envía los datos
            time.sleep(2)                                                       #Espera para posible recepción
            rx = self.s.recv(128)                                               #Recepción de datos
            self.receive(rx=rx)
            self.lora.nvram_save()                                              #Guarda los datos de la conexión LoRaWAN
        except OSError as e:
            if e.errno == 11:
                print("Caught exception while sending")
                print("errno: ", e.errno)
#------------------------------------------------------------------------------#
#Función de recpeción de datos.Es activada tras la ventana de recepción
#posterior al envío.
    def receive(self,rx=None):
        if rx == None:                                                          #No hay mensaje de recepción
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
#Funcion de lectura de sensores
    def readsens(self):
        reading = [0,0,0,0,0]
        reading[0] = int(self.lt.light()[0])                                    #Primer Elemento Lista: Luminosidad (entero)
        reading[1] = int(self.mp.pressure())                                    #Segundo Elemento Lista: Presión (entero)
        reading[2] = round(self.si.humidity(),2)                                #Tercer Elemento Lista: Humedad (dos decimales)
        reading[3] = round(self.si.temperature(),2)                             #Cuarto Elemento Lista: Temperatura (dos decimales)
        reading[4] = round(self.py.read_battery_voltage(),2)                    #Quinto Elemento Lista: Voltaje (dos decimales)
        return reading

#==============================================================================#
#Codigo principal
dev_addr = struct.unpack(">l", binascii.unhexlify('260110F2'))[0]               #Device Adress
nwk_swkey = binascii.unhexlify('BC8A246BFEBE7F57787B20E991D24CD3')              #Application Session Key
app_swkey = binascii.unhexlify('7E3B0CBD72FF38937B3FBA6CEB96B2D6')              #Network Session Key

if machine.reset_cause() == machine.DEEPSLEEP_RESET:                            #Si vuelve de DeepSleep
    print('woke from a deep sleep')
    sleep_time = pycom.nvs_get('sleep_time')                                    #Obtiene el valor de la variable sleep_time guardado en NVRAM
    n = Node(sleep_time)                                                        #Crea una instancia de Node
    lecturas = n.readsens()                                                     #Lee los valores de los diferentes sensores
    print (str(lecturas).strip('[]'))
    n.send(lecturas)                                                            #Envia el valor de las lecturas
    print("Lecturas Enviadas")
    # put the device to sleep
    machine.deepsleep(n.sleep_time*1000)                                        #Vuelve a deepsleep
else:                                                                           #Primer Boot o Hard Reset
    print('power on or hard reset')
    # Join LoRaWAN with ABP
    sleep_time = 30                                                             #Valor por defecto de sleep_time
    pycom.nvs_set('sleep_time', 30)                                             #Guarda el valor por defecto de sleep_time en NVRAM
    n = Node(sleep_time)                                                        #Crea una instancia de Node
    n.connect(dev_addr,nwk_swkey,app_swkey)                                     #Conecta mediante ABP LoRaWAN
    print("Conectado mediante ABP")
    machine.deepsleep(sleep_time*1000)                                          #Entra en DeepSleep