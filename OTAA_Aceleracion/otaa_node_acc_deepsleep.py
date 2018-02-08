#OTAA Node LoRaWAN Accelerometer
#Juan Manuel Galán Serrano
#UPC-ALSTOM 2018
#------------------------------------------------------------------------------#
from network import LoRa
import socket
import binascii
import struct
import pycom
import time
import machine
import _thread
from machine import Timer
from network import WLAN
#------------------------------------------------------------------------------#
#Librerias de Pysense y sensores
from pysense import Pysense
from LIS2HH12 import LIS2HH12

WAKE_REASON_PUSH_BUTTON = 2
WAKE_REASON_ACCELEROMETER = 1

FULL_SCALE_4G = const(2)
ODR_800_HZ = const(6)
#------------------------------------------------------------------------------#
class Node:
    def __init__(self,data_rate,py):
        self.lora = None                                                        # Instancia de Lora (sin inicializar)
        self.s = None                                                           # Instancia Socket (sin inicializar)
        self.dr = data_rate                                                     # Data Rate (defecto 5)
        self.py = py                                                            # Instancia de Pysense
        self.acc = LIS2HH12(self.py)                                            # Instancia del Acelerometro
        self.last = [0,0,0]                                                     # Último valor leído de aceleracion
        self.raw = [0,0,0]                                                      # Valor leído actual de aceleracion
        self.busy = 0                                                           # Value has passed limit
        self.interval = 10                                                      # Intervalo de toma de datos
        self.battery = None                                                     # Valor de la tensión de batería
        self.s_lock = _thread.allocate_lock()                                   # Semaforo para envío
#------------------------------------------------------------------------------#
    def connect(self,dev_eui,app_eui, app_key):
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
        self.lora.join(activation = LoRa.OTAA, auth = (dev_eui,app_eui, app_key),
                    timeout = 0, dr=5)                                                #login for TheThingsNetwork see here:
                                                                                #https://www.thethingsnetwork.org/forum/t/lopy-otaa-example/4471
        # Wait until the module has joined the network
        while not self.lora.has_joined():
            print("Trying to join LoraWAN with OTAA")
            time.sleep(2.5)
        print ("LoraWAN joined! ")
        #Handler de Recepción
        #self.lora.callback(trigger=(LoRa.RX_PACKET_EVENT),handler=self.lora_cb)
        # save the LoRaWAN connection state
        self.lora.nvram_save()
#------------------------------------------------------------------------------#
    def send(self,data):
        """
        Send data over the network.
        """

        self.s_lock.acquire()                                                   # Espera a que el semáforo esté disponible (tiempo indefinido)

        if py.get_wake_reason() == WAKE_REASON_ACCELEROMETER:                           #Si despierta tras deepsleep
            # Initialize LoRa in LORAWAN mode
            self.lora = LoRa(mode = LoRa.LORAWAN,adr=True,device_class=LoRa.CLASS_A)
            # restore the LoRaWAN connection state
            try:
                self.lora.nvram_restore()
            except OSError:
                print("Error: LoRa Configuration could not be restored")
                self.connect(binascii.unhexlify('006A76B0778AEDA7'),
                            binascii.unhexlify('70B3D57ED0009ABB'),
                            binascii.unhexlify('08D62712D816F1C28B7E6EA39E711209'))
                print("LoRa Connection Parameters Recovered")
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
        # Make the socket non-blocking
        self.s.setblocking(True)

        try:
            self.s.send(data)
            self.s.setblocking(False)                                           #Espera para posible recepción
            rx = bytes(self.s.recv(128))                                               #Recepción de datos
            self.receive(rx=rx)
            self.lora.nvram_save()
        except OSError as e:
            if e.errno == 11:
                print("Caught exception while sending")
                print("errno: ", e.errno)

        self.s_lock.release()                                                   #Libera el semáforo
        _thread.exit()                                                          #Cierra el hilo

#------------------------------------------------------------------------------#
#Función de recpeción de datos.Es activada tras la ventana de recepción
#posterior al envío.
    def receive(self,rx=None):
        if len(rx) == 0:                                                          #No hay mensaje de recepción
            pass
        else:
            if rx[0] == 82:                                                     #Orden de Cambio Data Rate (ASCII hex R=0x52 dec 87)
                print("Cambiando Data Rate %d" %(int.from_bytes(rx[1:],'big')))
                self.dr = int.from_bytes(rx[1:],'big')                          #Decodifica el valor del nuevo data Rate
                pycom.nvs_set('data_rate',self.data_rate)                       #Lo guarda en NVRAM
            else:
                pass
#------------------------------------------------------------------------------#
#Función de lectura de medidas. Los sensores ya han sido inicializados al
#crear la instancia de la clase Node
    def readsens(self):
        self.raw = self.acc.acceleration()                                      # Devuelve tuple con aceleracion en tres ejes (G)
        print("Aceleracion-> X:%fG Y:%fG Z:%fG"%(self.raw[0],self.raw[1],self.raw[2]))
        #Cálculos
        #if (self.raw[0] > 2.1) or (self.raw[1] > 2.1) or (self.raw[2] > 2.1):
        #        print("Enviando datos")
        #        XR=int(self.raw[0]*10000).to_bytes(2,'little')
        #        YR=int(self.raw[1]*10000).to_bytes(2,'little')
        #        ZR=int(self.raw[2]*10000).to_bytes(2,'little')
        #        XL=int(self.last[0]*10000).to_bytes(2,'little')
        #        YL=int(self.last[1]*10000).to_bytes(2,'little')
        #        ZL=int(self.last[2]*10000).to_bytes(2,'little')
        #        data = XR+YR+ZR+XL+YL+ZL
        #        _thread.start_new_thread(self.send,data)                        # Se crea un hilo para el envío de valores
        self._compare_update()
        alarmaPub = Timer.Alarm(self.readsens(),10, periodic=False)
        #if (self.raw[0] < 1.5) and (self.raw[1] < 1.5) and (self.raw[2] < 1.5):
        #    alarmaPub.cancel();
        #    n.py.setup_int_wake_up(rising=True,falling=False)                   #Activa la interrupcion para el boton DEBUG
        #    print('Activada Interrupccion de Actividad')
        #    n.acc.enable_activity_interrupt(1500,100)                           #Threshold= 1,5G, Min Time = 100ms
        #    print("Going to Sleep")
        #    n.py.setup_sleep(300)
        #    n.py.go_to_sleep()

        #self.battery = round(self.py.read_battery_voltage(),2)
        #print("Battery: %f",%(self.battery))
        #if (self.battery < 3.4):
        #    print("Batería Crítica")
        #    _thread.start_new_thread(self.send,("Batería"," Crítica"))          # Se crea un hilo para el envío de alarma de batería

#------------------------------------------------------------------------------#
    def _compare_update(self):
        if self.raw is not self.last:
            self.last = self.raw
        else:
            pass
#------------------------------------------------------------------------------#

#Codigo principal
dev_eui = binascii.unhexlify('006A76B0778AEDA7')
app_eui = binascii.unhexlify('70B3D57ED0009ABB')                                #ID de la app. (Seleccionada por el usuario)
app_key = binascii.unhexlify('08D62712D816F1C28B7E6EA39E711209')                #Clave de la app para realizar el handshake. Única para cada dispositivo.
py = Pysense()

#Según el modo de inicio, se realizan unas serie de acciones u otras.
if (py.get_wake_reason() == WAKE_REASON_ACCELEROMETER):
    print('Accelerometer Interrupt.')
    try:
        data_rate = pycom.nvs_get('data_rate')
    except (0):
        print("Error: Value could not be restore")
        data_rate = 5
        pycom.nvs_set('data_rate', data_rate)
        pass
    n = Node(data_rate,py)                                                      #Crea una instancia de Node
    n.readsens()


elif (py.get_wake_reason() == WAKE_REASON_PUSH_BUTTON):
    uart = UART(0, 115200)                                                      #Se activa la UART
    os.dupterm(uart)
    wlan = WLAN()
    wlan.init(mode=WLAN.AP, ssid='lopy-pysense', auth=(WLAN.WPA2,'lopy-pysense'),
                    channel=7,antenna=WLAN.INT_ANT)                             #Inicia el servidor FTP

    print("Device entered into debugging mode")
    print("Please do not connect to battery")
    pycom.heartbeat(True)                                                       #Se activa el Heartbeat
    while(1):
        if py.button_pressed():
            print("Exit DEBUG MODE, reseting...")
            print('- ' * 20)
            machine.reset()
else:                                                                           #Si viene de Boot o Hard Reset
    print('Power-On or Hard Reset')
    data_rate = 5
    try:
        pycom.nvs_set('data_rate', data_rate)
    except (None):
        print("Error: Value could not be stored")
        pass
    pycom.wifi_on_boot(False)                                                   #disable WiFi on boot TODO: Intentar en versiones posteriores, da un Core Error.
    print('Desactivado Wifi On Boot')
    n = Node(data_rate,py)                                                      #Crea una instancia de Node
    #n.connect(dev_eui,app_eui, app_key)                                        #Join LoRaWAN with OTAA
    n.acc.set_full_scale(FULL_SCALE_4G)
    print('Escala Acelerometro 4G')
    n.acc.set_odr(ODR_800_HZ)
    print('ODR 50Hz')
    n.py.setup_int_wake_up(rising=True,falling=False)                           #Activa la interrupcion para el boton DEBUG
    print('Activada Interrupccion de Actividad')
    n.acc.enable_activity_interrupt(1500,100)                                   #Threshold= 1G, Min Time = 100ms
    print('Set Acc Interrupt.')
    n.py.setup_sleep(300)
    n.py.go_to_sleep()
