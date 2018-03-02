""" OTAA Node example compatible with the LoPy Nano Gateway """
#JUAN MANUEL GALÁN SERRANO
#ALSTOM-UPC 2017
#==============================================================================#
# Firmware de nodo LoPy+pysense.
# El software conecta con el Network Server vía LoRaWAN (pasando por el Gateway)
# Una vez conectado se pasa a establecer todos los parámetros necesarios para el
# funcionamiento correctos de los sensores de la placa PySense.
# Es posible modificar los parámetros de funcionamiento vía remota enviando un
# mensjae downlink desde el server hacia el nodo.
# TODO: Estudiar los modos de bajo consumo
#==============================================================================#

from network import LoRa
import socket
import binascii
import struct
import time
import pycom
from pysense import Pysense
from GestionSensores import Gestion
import machine
from machine import Timer
#------------------------------------------------------------------------------#
# Función encargada de obtener los datos de los sensores actualizados desde la
# última comprobación y publicarla vía LoRaWAN a TTN.
def publicarJSON(alarmaPub):
    try:
        print("Creando mensaje UPLINK")
        json = gestion.crearjson()                                             #Obtiene un tuple con los datos de los sensores
    except 0:
        return
    pycom.rgbled(0x00FF00)                                                      #Se enciende el led tricolor en verde
    s.send(str(json))
    pycom.rgbled(0x000000)                                                      #Se apaga el led tricolor
    #machine.deepsleep([(intervalopub-1)*1000])
#------------------------------------------------------------------------------#

#------------------------------------------------------------------------------#
# Handler de recepción y procesamiento de los datos recibidos
def lora_cb(lora):
    events = lora.events()                                                      #Obtiene la info del evento recibido
    if events & LoRa.RX_PACKET_EVENT:                                           #Si se detecta un evento de recepción de paquete
        print('Lora packet received')
        data = s.recv(128)                                                      #Obtiene los datos recibidos y los pasa a formato bytes para poder ser tratados
        print(data[1])
        # Supongo que los datos recibidos vienen en formato bytes
        # (han podido ser convertidos de forma correcta)
        #### ACTIVAR/DESACTIVAR SENSORES
        if data[0] == 65:                                                       #Si recibe el comando ACTIVAR (ASCII hex A=0x41)
            for i in range(0,6):                                                #Evalúa cada uno de los sensores en el siguiente orden (G,A,T,H,P,L)
                en = data[1] & (1<<i)                                           #Extrae el bit correspondiente a cada sensor en cada caso
                if i == 0:                                                      #Giróscopo (G)
                    gestion.activarSensor(sensor='G',en=en)                     #Activar/desactiva el sensor dependiendo de la variable en (enable)
                elif i == 1:                                                    #Acelerómetro (A)
                    gestion.activarSensor(sensor='A',en=en)
                elif i == 2:                                                    #Sensor de Temperatura (T)
                    gestion.activarSensor(sensor='T',en=en)
                elif i == 3:                                                    #Sensor de Humedad (H)
                    gestion.activarSensor(sensor='H',en=en)
                elif i == 4:                                                    #Sensor de Presión (P)
                    gestion.activarSensor(sensor='P',en=en)
                elif i == 5:                                                    #Sensor de Luminosidad (L)
                    gestion.activarSensor(sensor='L',en=en)
                    #### MODIFICAR INTERVALOS
        elif data[0] == 73:                                                     #Si recibe el comando INTERVALO (ASCII hex I=0x49)
            if data[1] == 76:                                                   #LUMINOSIDAD (el segundo byte es L = 0x4C)
                print("Cambiando Intervalo Sensor de Luminosidad")
                gestion.modificarIntervalo(int.from_bytes(data[2:],'big')
                                            ,sensor='L')                        #Modifica el intervalo con el valor almacenado en el resto del payload
            elif data[1] == 80:                                                 #PRESION (el segundo byte es P = 0x50)
                print("Cambiando Intervalo Sensor de Presion")
                gestion.modificarIntervalo(int.from_bytes(data[2:],'big')
                                            ,sensor='P')
            elif data[1] == 72:                                                 #HUMEDAD (el segundo byte es H = 0x48)
                print("Cambiando Intervalo Sensor de Humedad")
                gestion.modificarIntervalo(int.from_bytes(data[2:],'big')
                                            ,sensor='H')
            elif data[1] == 84:                                                 #TEMPERATURA (el segundo byte es T = 0x54)
                print("Cambiando Intervalo Sensor de Temperatura")
                gestion.modificarIntervalo(int.from_bytes(data[2:],'big')
                                            ,sensor='T')
            elif (data[1] == 65)or(data[1] == 71):                              #ACELERÓMETRO Y GIRÓSCOPO (el segundo byte es A = 0x41 o G= 0x47) comparten intervalo
                print("Cambiando Intervalo Acelerómetro/Giroscopo")
                gestion.modificarIntervalo(int.from_bytes(data[2:],'big')
                                            ,sensor='A')
            else:
                print("Sensor no reconocido")
                return
                # Cancela la alarma de publicacion actual, calcula el nuevo intervalo minimo y
                # vuelve a activar la alarma.
            global alarmaPub
            alarmaPub.cancel()
            intervalopub = gestion.intervaloMinimo()
            alarmaPub = Timer.Alarm(publicarJSON, intervalopub, periodic=True)
        else:
            print("Mensaje recibido erroneo")
            return
    else:
        return
#------------------------------------------------------------------------------#
# Configuración e Inicio de la conexión vía LoRaWAN con el network Server TTN
# Initialize LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN)
print('LoRa MAC:' + binascii.hexlify(lora.mac()).upper().decode('utf-8'))
# Create an OTA authentication params
dev_eui = binascii.unhexlify('70 B3 D5 49 9D AE C6 EA'.replace(' ',''))         #ID del dispositivo. Es la dirección LORA_MAC (puede ser cualquier número)
app_eui = binascii.unhexlify('70 B3 D5 7E F0 00 42 A4'.replace(' ',''))         #ID de la app. (Seleccionada por el usuario)
app_key = binascii.unhexlify('36 93 92 6E 05 B3 01 A5 02 AB CF CA 43 0D A5 2A'  #Clave de la app para realizar el handshake. Única para cada dispositivo.
                                .replace(' ',''))

# Set the 3 default channels to the same frequency (must be before sending the
# OTAA join request)
lora.add_channel(0, frequency=868100000, dr_min=0, dr_max=5)
lora.add_channel(1, frequency=868100000, dr_min=0, dr_max=5)
lora.add_channel(2, frequency=868100000, dr_min=0, dr_max=5)

# Join a network using OTAA
lora.join(activation=LoRa.OTAA, auth=(dev_eui,app_eui, app_key), timeout=0)

# Wait until the module has joined the network
while not lora.has_joined():
    time.sleep(2.5)
    print('Not joined yet...')
print('Joined!!!')
# Remove all the non-default channels
for i in range(3, 16):
    lora.remove_channel(i)

# Create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# Set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)

# Make the socket blocking
s.setblocking(False)

# Desactiva heartbeat (ahorro batería)
pycom.heartbeat(False)

time.sleep(5.0)
#------------------------------------------------------------------------------#
# Código propio para lectura y publicación de valores de sensores
# Crea una instancia de la clase que gestiona los sensores
gestion = Gestion()
time.sleep(4.0)
#Se desactiva acelerometro y giroscopo
gestion.activarSensor(sensor='A',en=0)
gestion.activarSensor(sensor='G',en=0)
intervalopub = gestion.intervaloMinimo()                                        # El intervalo de publicacion será igual al intervalo minimo de toma de datos
print("Intervalo de Publicacion: %d segundos"  %(intervalopub))
# Fija la alarma de publicación de datos con el intervalo mínimo de los
# intervalos de publicación.
alarmaPub = Timer.Alarm(publicarJSON, intervalopub, periodic=True)
# Fija el handler de recpeción de paquetes
lora.callback(trigger=(LoRa.RX_PACKET_EVENT), handler=lora_cb)
# FIN PROGRAMA
