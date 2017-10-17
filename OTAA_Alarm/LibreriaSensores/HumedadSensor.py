#Librería Sensor de Humedad
#JUAN MANUEL GALÁN SERRANO
#ALSTOM-UPC 2017
#==============================================================================#
# Sensor de Humedad/Temperatura
# Con este sensor se realizaran las medidas de humedad y de temperatura. La
# librería es similar a las del resto de sensores, solo que las variables de
# medidas e intervalos son un tuple de 2 float en lugar de un único float.
#==============================================================================#
from machine import Timer
from pysense import Pysense
from SI7006A20 import SI7006A20
class HumedadSensor:
    """
        Funciones de control del sensor de Humedad SI7006A20.
    """
    tempHum = None

    def __init__(self, pysense=None):
        if pysense is None:
            self.pysense = Pysense()
        self.last = [0,0]                                                       # Último valor leído (Humedad, Temperatura)
        self.raw = [0,0]                                                        # Valor leído actual (Humedad, Temperatura)
        self.magic = 'LoPy'                                                     # Para detectar guardados corruptos
        self.update = [0,0]                                                     # El valor de (Humedad,Temperatura) ha sido actualizado
        self.interval = [20,20]                                                 # Intervalo toma de datos (Humedad,Temperatura)
        HumedadSensor.tempHum = SI7006A20(pysense)
        if (HumedadSensor.tempHum is not None):
            print('Cargado Sensor Humedad con éxito')
            self.alarmh = Timer.Alarm(self.leerhumedad,                         # Alarma de toma de datos de Humedad
                                        self.interval[0], periodic=True)
            self.alarmt = Timer.Alarm(self.leertemp,                            # Alarma de toma de datos de Temperatura
                                        self.interval[1], periodic=True)
    def leerhumedad(self,alarmh):
        self.raw[0] = HumedadSensor.tempHum.humidity()                          # Devuelve float con % Humedad Relativa
        self._compare_update('H')                                               # Compara con la ultima medida y actualiza si no coinciden
        print("Humedad: %fRH" %self.raw[0])
    def leertemp(self,alarmt):
        self.raw[1] = HumedadSensor.tempHum.temperature()                       # Devuelve float con temperatura
        self._compare_update('T')
        print("Temperatura: %f C" %self.raw[1])
    def _compare_update(self,sensor=None):
        if sensor is 'H':
            if self.raw[0] is not self.last[0] :
                self.last[0] = self.raw[0]
                self.update[0] = 1
            else:
                self.update[0] = 0
        elif sensor is 'T':
            if self.raw[1] is not self.last[1] :
                self.last[1] = self.raw[1]
                self.update[1] = 1
            else:
                self.update[1] = 0
        else:
            print("Error de actualización; sensor no reconocido")
    def desactPub(self,sensor=None):
        if sensor is 'H':
            self.alarmh.cancel()
            print("Desactivada publicación Sensor Humedad")
            return
        elif sensor is 'T':
            self.alarmt.cancel()
            print("Desactivada publicación Sensor Temperatura")
            return
        else:
            print("Sensor no reconocido")
            return
    def activarPub(self,sensor=None):
        if sensor is 'H':
            self.alarmh.cancel()
            self.alarmh = Timer.Alarm(self.leerhumedad,
                                        self.interval[0], periodic=True)
            print("Activada publicación Sensor Humedad")
            return
        elif sensor is 'T':
            self.alarmt.cancel()
            self.alarmt = Timer.Alarm(self.leertemp,
                                        self.interval[1], periodic=True)
            print("Activada publicación Sensor Temperatura")
            return
        else:
            print("Sensor no reconocido")
