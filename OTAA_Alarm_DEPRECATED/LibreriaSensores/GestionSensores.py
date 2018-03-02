#Gestion de los sensores
#JUAN MANUEL GALÁN SERRANO
#ALSTOM-UPC 2017
#==============================================================================#

#==============================================================================#
from machine import Timer
from machine import SD
from network import LoRa
from pysense import Pysense
from LuzSensor import LuzSensor
from PresionSensor import PresionSensor
from HumedadSensor import HumedadSensor
from Acelerometro import Acelerometro
import machine
import ubinascii
import builtins
import os

class Gestion:
    """
        Clase encargada de gestionar todos los sensores de la placa Pysense.
    """
    acc = None

    def __init__(self,sd=0,pysense=None):
        if pysense is None:
            self.py = Pysense()                                                 #Instancia de Pysense
        self.ambientLight = LuzSensor(pysense = self.py);                       #Instancia Sensor de Luz
        self.pressure = PresionSensor(pysense = self.py);                       #Instancia Sensor de Presión
        self.tempHum = HumedadSensor(pysense = self.py);                        #Instancia Sensor de Humedad
        self.acelerometro = Acelerometro(pysense = self.py)                     #Instancia Acelerometro
        self.mininterval = 0                                                    #Intervalo Minimo por defecto = 0s
        self.sd = sd                                                            #0 = No hay tarjeta SD. 1 = Hay tarjeta SD.
        if self.sd is 1:                                                        # Si hay tarjeta SD
            sd = SD()                                                           # Crea instancia SD
            os.mount(sd, '/sd')                                                 # Monta el sistema de archivos
            os.listdir('/sd')                                                   # Lista los directorios
    def crearjson(self):
        """
            Rellena un tupple con las lecturas de todos los sensores que han
            sido leídos desde la última publicación. Los valores corresponden a
            los sensores en este orden:
                Luz, Presión, Humedad, Temperatura, Batería
        """
        tup = [0,0,0,0,0]
        """ Se comprueba la propiedad update de cada sensor por separado y se va
            sumando al tupple. Si la medida ha sido actualizada se añade al
            tuple, en caso contrario toma el valor 0.
        """
        if self.ambientLight.update is 1:                                       #Si la medida ha sido actualizada
            tup[0] = int(self.ambientLight.raw[0])                              #Se añade a la posicion correpondiente en el tuple
            print('Añadido valor luminosidad a list')
            self.ambientLight.update = 0                                        #Se desactiva la propiedad update del sensor
        else:                                                                   #En caso de que la medida no haya sido actualizada
            tup[0] = 0                                                          #La posicion del tuple toma el valor 0
        if self.pressure.update is 1:
            tup[1] = int(self.pressure.raw)
            print('Añadido valor presion a list')
            self.pressure.update = 0
        else:
            tup[1] = 0
        if self.tempHum.update[0] is 1:
            tup[2] = round(self.tempHum.raw[0],2)
            print('Añadido valor humedad a list')
            self.tempHum.update[0] = 0
        else:
            tup[2] = 0
        if self.tempHum.update[1] is 1:
            tup[3] = round(self.tempHum.raw[1],2)
            print('Añadido valor temperatura a list')
            self.tempHum.update[1] = 0
        else:
            tup[3] = 0
        tup[4] = round(self.py.read_battery_voltage(),2)                        #En la ultima posicion se añade en valor del voltaje de la bateria
        print('Añadido valor batería a list')
        print (str(tup).strip('[]'))
        return (tup)
        #TODO Guardar en SD los datos de forma más ordenada
        if self.sd is 1:                                                        # Si hay una tarjeta SD, guarda el
            _guardarEnSD(tup);                                                  # valor del tupple en la SD.
    def intervaloMinimo(self):
        """ Cálculo del intervalo mínimo en la toma de medidas. Este intervalo
            mínimo se usará como intervalo de publicación de los datos vía
            LoRAWAN.
        """
        self.mininterval = min(self.ambientLight.interval,                      #Calcula el minimo entre todos los intervalos de los diferentes sensores
                                self.pressure.interval,
                                self.tempHum.interval[0],
                                self.tempHum.interval[1],
                                self.acelerometro.interval)
        return self.mininterval                                                 #Devuelve el mínimo calculado
    def modificarIntervalo(self,intervalo,sensor=''):
        """ Función para modificar el intervalo de un sensor. Sus argumentos
            son:
                intervalo: Número de segundos. Período de toma de datos del
                            sensor.Antes de la llamada a esta función el
                            intervalo por defecto es 20 segundos.
                sensor: Inicial del sensor al que le será modificada la
                        variable intervalo. Si no es correcto, se imprimirá un
                        mensaje por pantalla y ningún intervalo será modificado.
                        L: Luminosidad
                        P: Presión
                        H: Humedad
                        T: Temperatura
        """
        if sensor is 'L':
            self.ambientLight.interval = intervalo                              #Modifica la propiedad intervlao del sensor
            self.ambientLight.activarPub()                                      #Reinicia la publicación para que el cambio tenga efecto
            print("Intervalo Sensor Luminosidad modificado a %d segundos"
                    %self.ambientLight.interval)
        elif sensor is 'P':
            self.pressure.interval = intervalo
            self.pressure.activarPub()
            print("Intervalo Sensor Presion modificado a %d segundos"
                    %self.pressure.interval)
        elif sensor is 'H':
            self.tempHum.interval[0] = intervalo
            self.tempHum.activarPub('H')
            print("Intervalo Sensor Humedad modificado a %d segundos"
                    %self.tempHum.interval)
        elif sensor is 'T':
            self.tempHum.interval[1] = intervalo
            self.tempHum.activarPub('T')
            print("Intervalo Sensor Temperatura modificado a %d segundos"
                    %self.tempHum.interval)
        elif (sensor is 'A') or (sensor is 'G'):
            self.acelerometro.interval = intervalo
            self.acelerometro.activarPub('A')
            self.acelerometro.activarPub('G')
            print("Intervalo Acelerometro/Giroscopo modificado a %d segundos"
                    %self.acelerometro.interval)
        else:
            print("¡¡Valor de Sensor no válido!!")
    def activarSensor(self,sensor='',en=0):
        """ Activa y desactiva la toma de datos de un sensor. Toma los
            siguientes argumentos:
                sensor: Inicial del sensor a activar/desactivar.Si no es
                        correcto, se imprimirá un mensaje por pantalla y nada
                        será modificado.
                        L: Luminosidad
                        P: Presión
                        H: Humedad
                        T: Temperatura
                en: 0/1 Activar/desactivar toma de medidas.
        """
        if sensor is 'L':
            if en is 0:                                                         #Si el argumento es 0
                self.ambientLight.desactPub()                                   #Desactiva la publiacion de datos del sensor
            else:                                                               #Si el argumento es 1
                self.ambientLight.activarPub()                                  #Activa la publicacion de datos del sensor, en caso de que estuviera activa, la reinicia
        elif sensor is 'P':
            if en is 0:
                self.pressure.desactPub()
            else:
                self.pressure.activarPub()
        elif sensor is 'H':
            if en is 0:
                self.tempHum.desactPub('H')
            else:
                self.tempHum.activarPub('H')
        elif sensor is 'T':
            if en is 0:
                self.tempHum.desactPub('T')
            else:
                self.tempHum.activarPub('T')
        elif sensor is 'A':
            if en is 0:
                self.acelerometro.desactPub('A')
            else:
                self.acelerometro.activarPub('A')
        elif sensor is 'G':
            if en is 0:
                self.acelerometro.desactPub('G')
            else:
                self.acelerometro.activarPub('G')
        else:
            print("Valor de Sensor no válido")
    def _guardarEnSD(self,buf):
            f = open('sd/data.txt', 'w')
            f.write(buf)
            f.close()
