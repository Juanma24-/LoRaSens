#OTAA Node LoRaWAN with DeepSleep
#Juan Manuel Galán Serrano
#UPC-ALSTOM 2017
#------------------------------------------------------------------------------#
from network import LoRa
import socket
import binascii
#import struct
import pycom
import time
import machine
from machine import WDT
#------------------------------------------------------------------------------#
#Librerias de Pysense y sensores
from pysense import Pysense
from SI7006A20 import SI7006A20
from LTR329ALS01 import LTR329ALS01
from MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE
WAKE_REASON_TIMER = 4
#------------------------------------------------------------------------------#
class Node:
    def __init__(self,sleep_time,data_rate,pysense):
        self.lora = None                                                        # Instancia de Lora (sin inicializar)
        self.s = None                                                           # Instancia Socket (sin inicializar)
        self.sleep_time = sleep_time                                            # Intervalo de inactividad
        self.dr = data_rate                                                     # Data Rate (defecto 5)
        self.py = pysense                                                       # Instancia de Pysense
        self.mp = MPL3115A2(self.py,mode=PRESSURE)                              # Instancia Sensor de Presión
        self.si = SI7006A20(self.py)                                            # Instancia Sensor de Humedad y tempertura
        self.lt = LTR329ALS01(self.py)                                          # Instancia Sensor de Luminosidad
#------------------------------------------------------------------------------#
    def connect(self,app_eui, app_key):
        """
        Connect device to LoRa.
        Set the socket and lora instances.
        """
        # Initialize LoRa in LORAWAN mode
        self.lora = LoRa(mode = LoRa.LORAWAN,device_class=LoRa.CLASS_A)
        # Set the 3 default channels to the same frequency (must be before
        # sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Join a network using OTAA (Over the Air Activation)
        self.lora.join(activation = LoRa.OTAA, auth = (app_eui, app_key),
                    timeout = 0, dr=5)                                                #login for TheThingsNetwork see here:
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
        if py.get_wake_reason() == WAKE_REASON_TIMER:                                   #Si despierta tras deepsleep
            # Initialize LoRa in LORAWAN mode
            self.lora = LoRa(mode = LoRa.LORAWAN,adr=True,device_class=LoRa.CLASS_A)
            # restore the LoRaWAN connection state
            try:
                self.lora.nvram_restore()
            except OSError:
                print("Error: LoRa Configuration could not be restored")
                self.connect(binascii.unhexlify('70B3D57EF00042A4'),binascii.unhexlify('3693926E05B301A502ABCFCA430DA52A'))
                print("LoRa Connection Parameters Recovered")
        # remove all the non-default channels
        for i in range(3, 16):
            self.lora.remove_channel(i)
        # Set the 3 default channels to the same frequency
        # (must be before sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Create a LoRa socket
        self.s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        print("Created LoRaWAN socket")
        # Make the socket blocking
        self.s.setblocking(True)

        try:
            self.s.send(data)
            self.s.setblocking(False)                                           # make the socket non-blocking
            rx = bytes(self.s.recv(128))                                        # (because if there's no data received it will block forever...)
            self.receive(rx=rx)
            self.lora.nvram_save()
            print('Lora Config Saved!')
        except OSError as e:
            if e.errno == 11:
                print("Caught exception while sending")
                print("errno: ", e.errno)

#------------------------------------------------------------------------------#
#Función de recepción de datos.Es activada tras la ventana de recepción
#posterior al envío.
    def receive(self,rx=None):
        if len(rx) == 0:                                                        #No hay mensaje de recepción
            print('No incoming message')
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
                pycom.nvs_set('data_rate',self.data_rate)                       #Lo guarda en NVRAM
            else:
                pass
#------------------------------------------------------------------------------#
#Función de lectura de medidas. Los sensores ya han sido inicializados al
#crear la instancia de la clase Node
    def readsens(self):
        light = int(self.lt.light()[0]).to_bytes(2,'little')                       #Primer Elemento Lista: Luminosidad (entero)
        pressure = (int(self.mp.pressure())-90000).to_bytes(2,'little')            #Segundo Elemento Lista: Presión (entero)
        humidity = int(round(self.si.humidity(),2)*100).to_bytes(2,'little')          #Tercer Elemento Lista: Humedad (dos decimales)
        temperature = int(round(self.si.temperature(),2)*100).to_bytes(2,'little')    #Cuarto Elemento Lista: Temperatura (dos decimales)
        battery = int(round(self.py.read_battery_voltage(),2)*100-300).to_bytes(2,'little')          #Quinto Elemento Lista: Voltaje (dos decimales)

        reading = light+pressure+humidity+temperature+battery
        return reading
#------------------------------------------------------------------------------#
#Codigo principal
pycom.heartbeat(False)
app_eui = binascii.unhexlify('70B3D57EF00042A4')                                #ID de la app. (Seleccionada por el usuario)
app_key = binascii.unhexlify('3693926E05B301A502ABCFCA430DA52A')                #Clave de la app para realizar el handshake. Única para cada dispositivo.
ajuste = 10                                                                      #Numero de segundos para que el intervalo sea exacto en el Network Server
py = Pysense()
#Según el modo de inicio, se realizan unas serie de acciones u otras.
if py.get_wake_reason() == WAKE_REASON_TIMER:                                   #Si despierta tras deepsleep
    print('Woke from a deep sleep R:%d'%(WAKE_REASON_TIMER))

    try:
        sleep_time = pycom.nvs_get('sleep_time')                                #Obtiene el valor de la variable sleep_time guardado en NVRAM
        data_rate = pycom.nvs_get('data_rate')
    except 0:                                                                   #No se consigue obtener el valor (ERROR INFO: https://forum.pycom.io/topic/1869/efficiency-of-flash-vs-nvram-and-some-nvs-questions/3)
        print("Error: Sleep Time / Data Rate could not be recovered. Setting default value")
        sleep_time = 300                                                       #Se le da el valor por defecto (Minimo segun Fair Acess Policy TTN)
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
    print("Sending Data")
    n.send(lecturas)                                                            #Envío de las lecturas
    print("Data Sent, sleeping ...")
    print('- ' * 20)
    n.py.setup_sleep(sleep_time-ajuste)
    n.py.go_to_sleep()                                                          #Dispositivo enviado a Deepsleep
else:                                                                           #Si viene de Boot o Hard Reset
    print('Power on or hard reset')
    sleep_time = 300                                                            #Valor por defecto de sleep_time (Minimo segun Fair Acess Policy TTN)
    data_rate = 5
    #pycom.wifi_on_boot(False)                                                  # enable WiFi on boot
    try:
        pycom.nvs_set('sleep_time', sleep_time)                                 #Guarda el valor por defecto de sleep_time en NVRAM
        pycom.nvs_set('data_rate', data_rate)
    except (None):
        print("Error: Value could not be stored")
    n = Node(sleep_time,data_rate,py)                                           #Crea una instancia de Node
    n.connect(app_eui, app_key)                                                 #Join LoRaWAN with OTAA
    lecturas = n.readsens()                                                     #Envío de las lecturas
    n.send(lecturas)
    print("Data Sent, sleeping ...")
    print('- ' * 20)
    n.py.setup_sleep(sleep_time-ajuste)                                         #Dispositivo enviado a Deepsleep
    n.py.go_to_sleep()