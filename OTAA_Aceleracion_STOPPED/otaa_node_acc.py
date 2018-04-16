#OTAA LoRaWAN Accelerometer
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
from machine import Timer
import _thread
#------------------------------------------------------------------------------#
#Librerias de Pysense y sensores
from pysense import Pysense
from LIS2HH12 import LIS2HH12
#------------------------------------------------------------------------------#
class Node:
    _thread = None
    def __init__(self):
        self.lora = None
        self.s = None
        self.py = Pysense()                                                     # Instancia de Pysense
        self.acc = LIS2HH12(self.py)                                            # Instancia del Acelerometro
        self.last = [0,0,0]                                                     # Último valor leído de aceleracion
        self.raw = [0,0,0]                                                      # Valor leído actual de aceleracion
        self.busy = 0                                                           # Value has passed limit
        self.interval = 10                                                      # Intervalo de toma de datos
        self.battery = None                                                     # Valor de la tensión de batería
        self.alarma = None                                                      # Alarma de toma de datos de aceleracion
        self.s_lock = _thread.allocate_lock()                                   # Semaforo para envío
#------------------------------------------------------------------------------#
    def connect(self,dev_eui,app_eui,app_key,dr=5):
        """
        Connect device to LoRa.
        Set the socket and lora instances.
        """
        # Disable blue blinking and turn LED off
        pycom.heartbeat(False)
        # Initialize LoRa in LORAWAN mode
        self.lora = LoRa(mode = LoRa.LORAWAN,device_class=LoRa.CLASS_A,region=LoRa.EU868)
        # Set the 3 default channels to the same frequency (must be before sending the
        # OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Join a network using OTAA (Over the Air Activation)
        self.lora.join(activation = LoRa.OTAA, auth=(dev_eui,app_eui, app_key),
                        timeout = 0)                                            #login for TheThingsNetwork see here:
                                                                                #https://www.thethingsnetwork.org/forum/t/lopy-otaa-example/4471
        # Wait until the module has joined the network
        while not self.lora.has_joined():
            print("Trying to join LoraWAN with OTAA")
            time.sleep(2.5)
        print ("LoraWAN joined! ")
        print("Create LoRaWAN socket")
        self.s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        # Set the LoRaWAN data rate
        self.s.setsockopt(socket.SOL_LORA, socket.SO_DR, dr)
        # selecting confirmed type of messages
        self.s.setsockopt(socket.SOL_LORA, socket.SO_CONFIRMED, True)
        # Make the socket non-blocking
        self.s.setblocking(False)
        #Crea la alarma tras la conexion
        self.alarma = Timer.Alarm(self.readsens,self.interval, periodic=True)   #Alarma de toma de datos de aceleracion


#------------------------------------------------------------------------------#
    def send(self,datalast,dataraw):
        """
        Send data over the network.
        """
        self.s_lock.acquire()                                                   # Espera a que el semáforo esté disponible (tiempo indefinido)
        try:
            data = datalast,dataraw
            self.s.send(str(data))
            time.sleep(2)                                                       #Espera para posible recepción
            rx = self.s.recv(128)                                               #Recepción de datos
            self.receive(rx=rx)
        except OSError as e:
            if e.errno == 11:
                print("Caught exception while sending")
                print("errno: ", e.errno)
        self.s_lock.release()                                                   #Libera el semáforo
        _thread.exit()                                                          #Cierra el hilo
#------------------------------------------------------------------------------#
    def receive(self,rx=None):
        if rx == None:
            pass
        else:
            if rx[0] == 73:                                                     #Orden de Cambio de intervalo (ASCII hex I=0x49 dec 73)
                print("Recibido cambio de intervalo %d"
                            %(int.from_bytes(rx[1:],'big')))
                self.interval = int.from_bytes(rx[1:],'big')                    #Decodifica el valor del nuevo intervalo
                self.alarma.cancel()                                            #Cancela la alarma
                self.alarma = Timer.Alarm(self.readsens,
                                            self.interval, periodic=True)       #Vuelve a crear una alarma para el nuevo intervalo
            elif rx[0] == 67:                                                   #Orden de Cancelación de Lecturas (ASCII hex C=0x43 dec 67)
                print('Cancela las lecturas')
                self.alarma.cancel()
            elif rx[0] == 82:                                                   #Orden de Cambio Data Rate (ASCII hex R=0x52 dec 87)
                dr = int.from_bytes(rx[1:],'big')                               #Decodifica el valor del nuevo data Rate
                self.connect(dr=dr)
            else:
                pass
#------------------------------------------------------------------------------#
    #Función de lectura de medidas. El Acelerometro ya ha sido inicializado al
    #crear la instancia de la clase
    def readsens(self,alarma):
        self.raw = self.acc.acceleration()                                      # Devuelve tuple con aceleracion en tres ejes (G)
        print("Aceleracion-> X:%fG Y:%fG Z:%fG"
                %(self.raw[0],self.raw[1],self.raw[2]))
        #Cálculos
        if (self.raw[2] > 1):
                print("Enviando datos")
                _thread.start_new_thread(self.send,(self.last,self.raw))        # Se crea un hilo para el envío de valores
        self._compare_update()
        self.battery = round(self.py.read_battery_voltage(),2)
        if (self.battery < 3.3):
            print("Batería Crítica")
            _thread.start_new_thread(self.send,("Batería"," Crítica"))          # Se crea un hilo para el envío de alarma de batería
#------------------------------------------------------------------------------#
    def _compare_update(self):
        if self.raw is not self.last:
            self.last = self.raw
        else:
            pass
#------------------------------------------------------------------------------#
#Codigo principal
dev_eui = binascii.unhexlify('70B3D5499DAEC6FF')                                # ID del dispositivo. Es la dirección LORA_MAC (puede ser cualquier número)
app_eui = binascii.unhexlify('70B3D57EF00042A4')                                # ID de la app. (Seleccionada por el usuario)
app_key = binascii.unhexlify('8258C36174C05925FF56008D24FEAB93')                # Clave de la app para realizar el handshake. Única para cada dispositivo.
acc = Node()                                                                    # Crea una instancia de Acelerometro
acc.connect(dev_eui,app_eui,app_key)                                            # Conecta vía OTAA con el Network Server
#---------------------------FIN PROGRAMA---------------------------------------#
