from machine import UART
import os
#-----------------------#
#UART no activa
uart = UART(0, 115200)
os.dupterm(uart)
