
# OTAA Node LoRaWAN with DeepSleep
# Juan Manuel Galán Serrano
# UPC-ALSTOM 2018
#------------------------------------------------------------------------------#
from network import LoRa, WLAN
import socket
import binascii
import pycom
import time
import machine
from machine import WDT, Timer
from OTA import WiFiOTA
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
        self.lora = None                                                        # LoRa Instance (no Initialized)
        self.s = None                                                           # Socket Instance (no Initialized)
        self.sleep_time = sleep_time                                            # Inactivity Interval
        self.dr = data_rate                                                     # Data Rate (default 5)
        self.py = pysense                                                       # Pysense Instance
        self.lt = LTR329ALS01(self.py)                                          # Light Sensor Instance
        self.mp = MPL3115A2(self.py,mode=PRESSURE)                              # Pressure Sensor Instance
        self.si = SI7006A20(self.py)                                            # Temperature and Humidity Sensor Instance

#------------------------------------------------------------------------------#
    def connect(self,dev_eui,app_eui, app_key):
        """
        Connect device to LoRa.
        Set the socket and lora instances.
        """
        # Initialize LoRa in LORAWAN mode
        self.lora = LoRa(mode = LoRa.LORAWAN,adr=True,device_class=LoRa.CLASS_A,region=LoRa.EU868)
        # Set the 3 default channels to the same frequency (must be before
        # sending the OTAA join request)
        self.lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
        self.lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)
        # Join a network using OTAA (Over the Air Activation)
        self.lora.join(activation = LoRa.OTAA,auth = (dev_eui,app_eui, app_key),
                    timeout = 0, dr=5)                                          #login for TheThingsNetwork see here:
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
        if py.get_wake_reason() == WAKE_REASON_TIMER:                           #If the device wakes up after deepsleep
            # Initialize LoRa in LORAWAN mode
            self.lora = LoRa(mode = LoRa.LORAWAN,adr=True,device_class=LoRa.CLASS_A,region=LoRa.EU868)
            # restore the LoRaWAN connection state
            try:
                self.lora.nvram_restore()
            except OSError:
                print("Error: LoRa Configuration could not be restored")
                self.connect(binascii.unhexlify('70B3D54998EA594A'),
                            binascii.unhexlify('70B3D57EF00042A4'),
                            binascii.unhexlify('3693926E05B301A502ABCFCA430DA52A'))
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
        self.s.setblocking(True)                                                #Necessary to store counter and MAC parameters

        try:
            self.s.send(data)                                                   # Data sending
            self.s.setblocking(False)                                           # Make the socket non-blocking (necessary not to block the device)
                                                                                # (because if there's no data received it will block forever...)
            self.receive(rx=bytes(self.s.recv(128)))
            self.lora.nvram_save()
            print('Lora Config Saved!')
        except OSError as e:
            if e.errno == 11:
                print("Caught exception while sending")
                print("errno: ", e.errno)
                pass

#------------------------------------------------------------------------------#
# Data Receiving Function. It is activated after the reception windows.
    def receive(self,rx=None):
        if len(rx) == 0:                                                        # No reception message.
            print('No incoming message')
            pass
        else:
            if rx[0] == 73:                                                     # Interval Change Order (ASCII hex I=0x49 dec 73)
                print("New Interval received: %d"
                            %(int.from_bytes(rx[1:],'big')))
                self.sleep_time = int.from_bytes(rx[1:],'big')                  # Decode the new interval
                pycom.nvs_set('sleep_time',self.sleep_time)                     # Save in NVRAM
            elif rx[0] == 82:                                                   # Data Rate Change Order (ASCII hex R=0x52 dec 87)
                                                                                # It will not be necessary after ADR Firmware bug is fixed.
                print("Changing Data Rate: %d" %(int.from_bytes(rx[1:],'big')))
                self.dr = int.from_bytes(rx[1:],'big')                          # Decode new Data Rate value
                pycom.nvs_set('data_rate',self.data_rate)                       # Saves in NVRAM
            elif rx[0] == 79:                                                   #TODO: Perform OTA via Wi-Fi
                #print("Performing OTA")
                #ota.connect()
                #ota.update()
                pass
            else:
                pass
#------------------------------------------------------------------------------#
# Measurements Reading Method. Sensors have already been inicialized with Node
# instance.
    def readsens(self):
        light = int(self.lt.light()[0]).to_bytes(2,'little')                                    # First element: Light (integer)
        pressure = (int(self.mp.pressure())-90000).to_bytes(2,'little')                         # Second Element: Pressure (integer)
        humidity = int(round(self.si.humidity(),2)*100).to_bytes(2,'little')                    # Third Element: Humidity (two dec)
        temperature = int(round(self.si.temperature(),2)*100).to_bytes(2,'little')              # Fourth Element: Temperature (two dec)
        battery = int(round(self.py.read_battery_voltage(),4)*10000-33000).to_bytes(2,'little') # Fifth Element: Voltage (four dec)

        reading = light+pressure+humidity+temperature+battery                   # Bytes junction
        print("Reading obtained")
        return reading
#------------------------------------------------------------------------------#
# Main code

app_eui = binascii.unhexlify('70B3D57ED0009F73')                                # App ID. (User selection)
dev_eui = binascii.unhexlify('70B3D5499DAEC6EA')                                # Device ID. (User selection)
app_key = binascii.unhexlify('054BFCAC2632EB70D56F4BCBB8D95F02')                # App Key for handshake. Unique for every device.
ajuste = 10                                                                     # Not real time operating system
                                                                                # TODO: REAL TIME
py = Pysense()
#------------------------------------------------------------------------------#
#Depending init mode one action or another are performed.
if py.get_wake_reason() == WAKE_REASON_TIMER:                                   # Deepsleep wake up
    print('Woke from a deep sleep R:%d'%(WAKE_REASON_TIMER))

    try:
        sleep_time = pycom.nvs_get('sleep_time')                                # sleep_time variable value is recovered form NVRAM.
        data_rate = pycom.nvs_get('data_rate')
    except 0:                                                                   # Value couldn't be obtained (ERROR INFO: https://forum.pycom.io/topic/1869/efficiency-of-flash-vs-nvram-and-some-nvs-questions/3)
        print("Error: Sleep Time / Data Rate could not be recovered. Setting default value")
        sleep_time = 300                                                        # Default value
        data_rate = 5
        pycom.nvs_set('sleep_time', sleep_time)                                 # sleep_time default value is saved in NVRAM.
        pycom.nvs_set('data_rate', data_rate)
    print("SleepTime & Data Rate recovered")

    try:
        n = Node(sleep_time,data_rate,py)                                       # Node Instance created
        print("Node Instance created sucesfully")
    except Exception:
        print("Node Instance could not be cretaed. Sleeping...")
        print('- ' * 20)
        n.py.setup_sleep(sleep_time-ajuste)
        n.py.go_to_sleep(False)                                                 # Device sent to DeepSleep

    print("Sending Data")
    n.send(n.readsens())                                                        # Readings are being sent
    print("Data Sent, sleeping ...")
    print('- ' * 20)
    n.py.setup_int_wake_up(rising=1,falling=0)                                  # Button interrupt enabled
    n.py.setup_sleep(sleep_time-ajuste)
    n.py.go_to_sleep(False)                                                     # Device sent to DeepSleep

elif (py.get_wake_reason() == WAKE_REASON_PUSH_BUTTON):
    uart = UART(0, 115200)                                                      # UART ON
    os.dupterm(uart)
    wlan = WLAN()
    wlan.init(mode=WLAN.AP, ssid='lopy-pysense', auth=(WLAN.WPA2,'lopy-pysense'), channel=7,antenna=WLAN.INT_ANT) #Init FTP Server

    print("Device entered into debugging mode")
    print("Please do not connect to battery")
    pycom.heartbeat(True)                                                       # Heartbeat is ON
    while(1):
        if py.button_pressed():
            print("Exit DEBUG MODE, reseting...")
            print('- ' * 20)
            machine.reset()

else:                                                                           # Device from Boot or Hard Reset
    print('Power on or hard reset')
    sleep_time = 300                                                            # Default sleep_time value (Fair Acess Policy TTN)
    data_rate = 5
    pycom.wifi_on_boot(False)                                                   # Disable WiFi on boot.

    try:
        pycom.nvs_set('sleep_time', sleep_time)                                 # sleep_time default value is saved in NVRAM.
        pycom.nvs_set('data_rate', data_rate)
    except (None):
        print("Error: Value could not be stored")
        pass

    n = Node(sleep_time,data_rate,py)                                           # Node Instance created
    n.connect(dev_eui,app_eui, app_key)                                         # Join LoRaWAN with OTAA
    #ota = WiFiOTA(WIFI_SSID,WIFI_PW,
    #          SERVER_IP,  # Update server address
    #          8000)  # Update server port
    pycom.heartbeat_on_boot(False)                                              # Readings are being sent
    n.send(n.readsens())
    print("Data Sent, sleeping ...")
    time.sleep(10)
    print('- ' * 10)
    n.py.setup_int_wake_up(rising=1,falling=0)                                  # Enable interrupt for DEBUG button
    n.py.setup_sleep(sleep_time-ajuste)                                         # Device sent to DeepSleep
    time.sleep(1000)
    n.py.go_to_sleep(False)
