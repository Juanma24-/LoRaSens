#OTAA Node LoRaWAN with DeepSleep
#Juan Manuel Galán Serrano
#UPC-ALSTOM 2017
#------------------------------------------------------------------------------#
from network import LoRa, WLAN
import network
import socket
import binascii
import pycom
import time
import machine
from machine import Timer
from OTA import WiFiOTA
#------------------------------------------------------------------------------#
#------------------------------------------------------------------------------#
class Node:
    def __init__(self,sleep_time,data_rate):
        self.lora = None                                                        # Instancia de Lora (sin inicializar)
        self.s = None                                                           # Instancia Socket (sin inicializar)
        self.sleep_time = sleep_time                                            # Intervalo de inactividad
        self.dr = data_rate                                                     # Data Rate (defecto 5)
        self.adc = machine.ADC()                                                #ADC for battery measurement
        self.adc.vref(1200)
        self.batteryValue = self.adc.channel(pin='P16',attn=2)
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
                    timeout = 0, dr=self.dr)                                    #login for TheThingsNetwork see here:
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
        if machine.reset_cause() == machine.DEEPSLEEP_RESET:                    #Si despierta tras deepsleep
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
                                                                                # (because if there's no data received it will block forever...)
            self.receive(rx=bytes(self.s.recv(128)) )
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
                ota = WiFiOTA('MBP_JuanMa','MBP_JuanMa',"54.154.225.138",8000)  #Amazon Web Services Server
                print("Updating via OTA...")
                print('- ' * 20)
                ota.connect()
                ota.update()
            else:
                pass
#------------------------------------------------------------------------------#
#Función de lectura de medidas. Los sensores ya han sido inicializados al
#crear la instancia de la clase Node
    def readsens(self):

        battery = self.batteryValue.voltage()/327.5
        reading = bytes([0x00, 0x00, 0x00,0x00, 0x00, 0x00,0x00, 0x00])+int(round(battery,4)*10000-33000).to_bytes(2,'little')
        return reading
#------------------------------------------------------------------------------#
#Codigo principal

app_eui = binascii.unhexlify('70B3D57ED0009F73')                                #ID de la app. (Seleccionada por el usuario)
dev_eui = binascii.unhexlify('70B3D5499CE967FB')                                #ID del dispositivo. (Seleccionada por el usuario)
app_key = binascii.unhexlify('054BFCAC2632EB70D56F4BCBB8D95F02')                #Clave de la app para realizar el handshake. Única para cada dispositivo.
ajuste = 3                                                                      #Numero de segundos para que el intervalo sea exacto en el Network Server

#------------------------------------------------------------------------------#
#Según el modo de inicio, se realizan unas serie de acciones u otras.
if machine.reset_cause() == machine.DEEPSLEEP_RESET:                            #Si despierta tras deepsleep
    print('Woke from a deep sleep R:%d'%(machine.DEEPSLEEP_RESET))

    try:
        sleep_time = pycom.nvs_get('sleep_time')                                #Obtiene el valor de la variable sleep_time guardado en NVRAM
        data_rate = pycom.nvs_get('data_rate')
    except Exception:                                                           #No se consigue obtener el valor (ERROR INFO: https://forum.pycom.io/topic/1869/efficiency-of-flash-vs-nvram-and-some-nvs-questions/3)
        print("Error: Sleep Time / Data Rate could not be recovered. Setting default value")
        sleep_time = 60                                                         #Se le da el valor por defecto
        data_rate = 5
        pycom.nvs_set('sleep_time', sleep_time)                                 #Guarda el valor por defecto de sleep_time en NVRAM
        pycom.nvs_set('data_rate', data_rate)
    print("SleepTime & Data Rate recovered")

    try:
        n = Node(sleep_time,data_rate)                                          #Crea una instancia de Node
        print("Node Instance created sucesfully")
    except Exception:
        print("Node Instance could not be cretaed. Sleeping...")
        print('- ' * 20)
        machine.deepsleep((sleep_time-ajuste)*1000)                             #Dispositivo enviado a Deepsleep

    print("Sending Data")
    n.send(n.readsens())                                                        #Envío de las lecturas
    print("Data Sent, sleeping ...")
    print('- ' * 20)
    machine.deepsleep((sleep_time-ajuste)*1000)                                 #Dispositivo enviado a Deepsleep

elif (machine.wake_reason() == machine.PIN_WAKE):
    uart = UART(0, 115200)                                                      #Se activa la UART
    os.dupterm(uart)
    wlan = WLAN()
    wlan.init(mode=WLAN.AP, ssid='lopy-pysense',
                auth=(WLAN.WPA2,'lopy-pysense'),
                 channel=7,antenna=WLAN.INT_ANT)                                #Inicia Wi-Fi
    server = network.Server()                                                   #Init FTP Server
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
    sleep_time = 60                                                             #Valor por defecto de sleep_time (Minimo segun Fair Acess Policy TTN)
    data_rate = 5
    pycom.wifi_on_boot(False)                                                   #Disable WiFi on boot
    pycom.heartbeat_on_boot(False)
    try:
        pycom.nvs_set('sleep_time', sleep_time)                                 #Guarda el valor por defecto de sleep_time en NVRAM
        pycom.nvs_set('data_rate', data_rate)
    except Exception:
        print("Error: Value could not be stored")
        pass

    n = Node(sleep_time,data_rate)                                              #Crea una instancia de Node
    n.connect(dev_eui,app_eui, app_key)                                         #Join LoRaWAN with OTAA

    n.send(n.readsens())
    print("Data Sent, sleeping ...")
    print('- ' * 20)
    machine.deepsleep((sleep_time-ajuste)*1000)                                 #Dispositivo enviado a Deepsleep
