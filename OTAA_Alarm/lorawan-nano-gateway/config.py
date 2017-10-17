""" LoPy LoRaWAN Nano Gateway configuration options """

import machine
import binascii

WIFI_MAC = binascii.hexlify(machine.unique_id()).upper()
# Set  the Gateway ID to be the first 3 bytes of MAC address + 'FFFE' + last 3 bytes of MAC address
#Para TTN
GATEWAY_ID = WIFI_MAC[:6] + "FFFE" + WIFI_MAC[6:12]
#Para Loriot
#GATEWAY_ID = WIFI_MAC[:6] + "FFFF" + WIFI_MAC[6:12]

#Para TTN
SERVER = 'router.eu.thethings.network'
PORT = 1700
#Para Loriot
#SERVER = 'eu1.loriot.io'
#PORT = 1780
NTP = "pool.ntp.org"
NTP_PERIOD_S = 3600

WIFI_SSID = 'MOVISTAR_1B6D'
WIFI_PASS = 'YB5QYVgvkh2HvNSriVUT'

LORA_FREQUENCY = 868100000
LORA_DR = "SF7BW125" # DR_5
