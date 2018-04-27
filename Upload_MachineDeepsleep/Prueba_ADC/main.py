#Juan Manuel Galán Serrano
#ALSTOM 2018
#------------------------------------------------------------------------------#
from network import LoRa, WLAN
import socket
import binascii
import pycom
import time
import machine
from machine import Timer
#------------------------------------------------------------------------------#

#Init adc
adc = machine.ADC()
adc.vref(1300)
batteryValue = adc.channel(pin='P16',attn=2)
#Infinite Loop
while(1):
    battery = batteryValue.voltage()/327.5
    print("ADC Read Value: %d" %batteryValue())
    print("Battery Level: %fV" %battery)
    batteryBytes = bytes([0x00, 0x00, 0x00,0x00, 0x00, 0x00,0x00, 0x00, 0x00,0x00, 0x00])+int(round(battery,4)*10000-33000).to_bytes(2,'little')

    print("BatteryBytes:%s" %batteryBytes )
    time.sleep(5)
