#OTAA Node LoRaWAN with DeepSleep
#Juan Manuel Galán Serrano
#UPC-ALSTOM 2017
#------------------------------------------------------------------------------#
from network import LoRa, WLAN
import socket
import binascii
import pycom
import time
import machine
#from OTA import WiFiOTA
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
    def connect(self,dev_eui,app_eui, app_key):
        """
        Connect device to LoRa.
        Set the socket and lora instances.
        """
        # Initialize LoRa in LORAWAN mode
        self.lora = LoRa(mode = LoRa.LORAWAN,device_class=LoRa.CLASS_A,region=LoRa.EU868)
        # Set the 3 default channels to the same frequency (must be before
        # sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Join a network using OTAA (Over the Air Activation)
        self.lora.join(activation = LoRa.OTAA, auth = (dev_eui,app_eui, app_key),
                    timeout = 0, dr=self.dr)                                                #login for TheThingsNetwork see here:
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
        if py.get_wake_reason() == WAKE_REASON_TIMER:                           #Si despierta tras deepsleep
            # Initialize LoRa in LORAWAN mode
            self.lora = LoRa(mode = LoRa.LORAWAN,adr=True,device_class=LoRa.CLASS_A,region=LoRa.EU868)
            # restore the LoRaWAN connection state
            try:
                self.lora.nvram_restore()
            except OSError:
                print("Error: LoRa Configuration could not be restored")
                self.connect(dev_eui,app_eui,app_key)
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
        self.s.setblocking(True)                                                #Necesario para gurdar el contador de mensajes

        try:
            self.s.send(data)                                                   #Envio de datos
            self.s.setblocking(False)                                           # make the socket non-blocking (necesario para no dejar colgado el dispositivo)
            rx = bytes(self.s.recv(128))                                        # (because if there's no data received it will block forever...)
            self.receive(rx=rx)
            self.lora.nvram_save()
            print('Lora Config Saved!')
        except OSError as e:
            if e.errno == 11:
                print("Caught exception while sending")
                print("errno: ", e.errno)
                pass

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
            elif rx[0] == 79:
                print("Performing OTA")
                #ota.connect()
                #ota.update()
                pass
            else:
                pass
#------------------------------------------------------------------------------#
#Función de lectura de medidas. Los sensores ya han sido inicializados al
#crear la instancia de la clase Node
    def readsens(self):
        pressure = (int(self.mp.pressure())-90000).to_bytes(2,'little')                     #Segundo Elemento Lista: Presión (entero)
        humidity = int(round(self.si.humidity(),2)*100).to_bytes(2,'little')                #Tercer Elemento Lista: Humedad (dos decimales)
        temperature = int(round(self.si.temperature(),2)*100).to_bytes(2,'little')          #Cuarto Elemento Lista: Temperatura (dos decimales)
        battery = int(round(self.py.read_battery_voltage(),4)*10000-33000).to_bytes(2,'little') #Quinto Elemento Lista: Voltaje (cuatro decimales)
        light = int(self.lt.light()[0]).to_bytes(2,'little')                                #Primer Elemento Lista: Luminosidad (entero)
        reading = light+pressure+humidity+temperature+battery                   #Union de tipos bytes
        return reading
#------------------------------------------------------------------------------#
#Codigo principal
                                                         #Desactiva el heartbeat
app_eui = binascii.unhexlify('BE7A000000000906')                                #ID de la app. (Seleccionada por el usuario)
dev_eui = binascii.unhexlify('BE7A000000002455')
app_key = binascii.unhexlify('61F0D7D0112265B4705D44E80E7F0694')                #Clave de la app para realizar el handshake. Única para cada dispositivo.
ajuste = 5                                                                    #Numero de segundos para que el intervalo sea exacto en el Network Server
                                                                                #TODO: REAL TIME
py = Pysense()
#------------------------------------------------------------------------------#
#Según el modo de inicio, se realizan unas serie de acciones u otras.
if py.get_wake_reason() == WAKE_REASON_TIMER:                                   #Si despierta tras deepsleep
    print('Woke from a deep sleep R:%d'%(WAKE_REASON_TIMER))

    try:
        sleep_time = pycom.nvs_get('sleep_time')                                #Obtiene el valor de la variable sleep_time guardado en NVRAM
        data_rate = pycom.nvs_get('data_rate')
    except Exception:                                                                   #No se consigue obtener el valor (ERROR INFO: https://forum.pycom.io/topic/1869/efficiency-of-flash-vs-nvram-and-some-nvs-questions/3)
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
    print("Sending Data")
    n.send(lecturas)                                                            #Envío de las lecturas
    print("Data Sent, sleeping ...")
    print('- ' * 20)
    n.py.setup_int_wake_up(rising=1,falling=0)                                  #Activa la interrupcion por Botón
    n.py.setup_sleep(sleep_time-ajuste)
    n.py.go_to_sleep(False)                                                          #Dispositivo enviado a Deepsleep

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
    pycom.heartbeat_on_boot(False)
    try:
        pycom.nvs_set('sleep_time', sleep_time)                                 #Guarda el valor por defecto de sleep_time en NVRAM
        pycom.nvs_set('data_rate', data_rate)
    except (Exception):
        print("Error: Value could not be stored")
        pass

    n = Node(sleep_time,data_rate,py)                                           #Crea una instancia de Node
    n.connect(dev_eui,app_eui, app_key)                                                 #Join LoRaWAN with OTAA
    #ota = WiFiOTA(WIFI_SSID,WIFI_PW,
    #          SERVER_IP,  # Update server address
    #          8000)  # Update server port
    #Envío de las lecturas
    n.send(n.readsens())
    print("Data Sent, sleeping ...")
    print('- ' * 20)
    n.py.setup_int_wake_up(rising=1,falling=0)                                  # Activa la interrupcion para el boton DEBUG
    n.py.setup_sleep(sleep_time-ajuste)                                         #Dispositivo enviado a Deepsleep
    n.py.go_to_sleep(False)
