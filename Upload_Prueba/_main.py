from machine import UART
import os
import machine
import ubinascii
import network
import pycom
import time
import pysense

print("Lopy4 iniciada")
pycom.wifi_on_boot(False)
py=pysense()
# main.py -- put your code here!
while(True):
    print("Lectura de batería")
    print('Battery voltage:%f' %(py.read_battery_voltage()))
    machine.deepsleep(5000)
