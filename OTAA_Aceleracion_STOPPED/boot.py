from machine import UART
import os
import machine
import ubinascii

uart = UART(0, 115200)
os.dupterm(uart)
#------------------------------------------------------------------------------#
#Imprime version del Firmware OS
print('Version OS:' + os.uname().release)
print("Machine CPU frequency: %dMHz" %(machine.freq()/1000000))
print("Machine ID:%s"  %ubinascii.hexlify(machine.unique_id()))
#------------------------------------------------------------------------------#
#Archivo Main para publicación de datos.
machine.main('otaa_node_acc_deepsleep.py')
#------------------------------------------------------------------------------#
