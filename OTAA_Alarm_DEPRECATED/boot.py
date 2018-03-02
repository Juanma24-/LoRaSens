from machine import UART
import os
import machine
import ubinascii

uart = UART(0, 115200)
os.dupterm(uart)
#Imprime version del Firmware OS
print('Version OS:' + os.uname().release)
#------------------------------------------------------------------------------#
#Archivo Main para publicación de datos.
machine.main('otaa_node_0.py')
#Archivo Main para realización de pruebas en sensores.
#machine.main('Lectura_Sensores_0.py')
#------------------------------------------------------------------------------#
