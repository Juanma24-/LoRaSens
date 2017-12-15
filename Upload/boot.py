from machine import UART
import os
import machine
import ubinascii
import network
from network import Bluetooth
#-----------------------#
#UART no activa
#uart = UART(0, 115200)
#os.dupterm(uart)
#-----------------------#
#Desactiva WiFi
wlan = network.WLAN(mode=network.WLAN.STA)
wlan.deinit()
#-----------------------#
#Desactiva Bluetooth
bt = Bluetooth()
bt.deinit()
#-----------------------#
#Imprime version del Firmware OS
print('Version OS:' + os.uname().release)

#------------------------------------------------------------------------------#
#Archivo Main para publicación de datos con activación OTAA.
machine.main('otaa_node_deepsleep_C.py')
#------------------------------------------------------------------------------#
