from machine import UART
import os
import machine
import ubinascii

uart = UART(0, 115200)
os.dupterm(uart)
#Imprime version del Firmware OS
print('Version OS:' + os.uname().release)
#print('Frecuencia de CPU:' + machine.freq())
#print('Lopy´s WIFI MAC Adress' + machine.unique_id())
#------------------------------------------------------------------------------#
#Archivo Main para publicación de datos.
machine.main('otaa_node_acc.py')
#------------------------------------------------------------------------------#
