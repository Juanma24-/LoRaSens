from machine import UART
import os
import machine
import ubinascii
uart = UART(0, 115200)
os.dupterm(uart)
