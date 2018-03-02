from machine import UART
import os
import machine
import ubinascii
import network
import pycom
from network import Bluetooth
#-----------------------#
#pycom.heartbeat(False)
#-----------------------#
#UART no activa
#uart = UART(0, 115200)
#os.dupterm(uart)
#-----------------------#
#Desactiva WiFi
#wlan = network.WLAN(mode=network.WLAN.STA)
#wlan.deinit()
#-----------------------#
#Desactiva Bluetooth
bt = Bluetooth()
bt.deinit()
#-----------------------#
#Imprime version del Firmware OS
print('Version OS:' + os.uname().release)
print("Machine CPU frequency: %dMHz" %(machine.freq()/1000000))
#print("Machine ID:" + ubinascii.hexlify(machine.unique_id()))
#------------------------------------------------------------------------------#
#Archivo Main para publicación de datos con activación OTAA.
machine.main('otaa_node_deepsleep.py')
#------------------------------------------------------------------------------#
