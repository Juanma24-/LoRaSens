#JUAN MANUEL GALÁN SERRANO
#ALSTOM-UPC 2017
#==============================================================================#
# Archivo de prueba para comprobar el correcto funcionamiento de la clase de
# gestión de los sensores y los sensores en sí.
#==============================================================================#
from pysense import Pysense
from GestionSensores import Gestion
from machine import Timer
import binascii
import time
import machine
import pycom
#------------------------------------------------------------------------------#
# Función encargada de crear la cadena en formato JSON con los datos de los
# sensores medidos.
def publicarJSON(alarmaPub):
        print("Creando JSON")
        pycom.rgbled(0x00FF00)                                                      #Se enciende el led tricolor en verde
        json = gestion.crearjson()
        print(str(json))
        pycom.rgbled(0x000000)                                                      #Se apaga el led tricolor

#------------------------------------------------------------------------------#
# Código de las pruebas.
# Crea una instancia para gestionar los sensores.
gestion = Gestion()
pycom.heartbeat(False)

time.sleep(4)
#Se desactiva acelerometro y giroscopo
gestion.activarSensor(sensor='A',en=0)
gestion.activarSensor(sensor='G',en=0)
# Se busca en intervalo mínimo de lectura de datos en los sensores.
intervalopub = gestion.intervaloMinimo()
print("Intervalo de Publicacion: %d segundos"  %(intervalopub))
# Fija el intervalo creación de JSON como el mínimo de los intervalos de lectura.
alarmaPub = Timer.Alarm(publicarJSON, intervalopub, periodic=True)
time.sleep(60)
gestion.activarSensor(sensor='A',en=0)
gestion.activarSensor(sensor='G',en=0)
# Fija el intervalo del sensor de Luminosidad en 30s (por defecto 20s)
print("Modificado intervalo de Luminosidad a 30s")
gestion.modificarIntervalo(30,'L')
time.sleep(120)
# Desactiva todos los sensores
gestion.activarSensor(sensor='L',en=0)
gestion.activarSensor(sensor='P',en=0)
gestion.activarSensor(sensor='H',en=0)
gestion.activarSensor(sensor='T',en=0)
alarmaPub.cancel()
time.sleep(120)
# Vuelve a activar todos los sensores
gestion.activarSensor(sensor='L',en=1)
gestion.activarSensor(sensor='P',en=1)
gestion.activarSensor(sensor='H',en=1)
gestion.activarSensor(sensor='T',en=1)
intervalopub = gestion.intervaloMinimo()
alarmaPub = Timer.Alarm(publicarJSON, intervalopub, periodic=True)

# FIN PROGRAMA
