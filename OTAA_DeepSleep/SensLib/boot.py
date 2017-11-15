from machine import UART
import os
import machine
import ubinascii

uart = UART(0, 115200)
os.dupterm(uart)
#Imprime version del Firmware OS
print('Version OS:' + os.uname().release)
#------------------------------------------------------------------------------#
#Archivo Main para publicación de datos con activación OTAA.
machine.main('otaa_node_deepsleep.py')
#Archivo Main para publicación de datos con activación ABP.
#machine.main('abp_node_deepsleep.py')
#------------------------------------------------------------------------------#
