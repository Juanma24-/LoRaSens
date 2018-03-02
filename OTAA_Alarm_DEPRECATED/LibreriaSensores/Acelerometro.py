#Librería Acelerómetro
#JUAN MANUEL GALÁN SERRANO
#ALSTOM-UPC 2017
#==============================================================================#

#==============================================================================#
from machine import Timer
from pysense import Pysense
from LIS2HH12 import LIS2HH12
class Acelerometro:
    """
        Funciones de control del Acelerometro SI7006A20.
    """
    acc = None

    def __init__(self, pysense=None):
        if pysense is None:
            self.pysense = Pysense()
        self.last = [0,0,0]                                                     # Último valor leído de aceleracion
        self.raw = [0,0,0]                                                      # Valor leído actual de aceleracion
        self.lastg = [0,0,0]                                                    # Último valor leído de orientación
        self.rawg = [0,0,0]                                                     # Valor leído actual de orientación
        self.magic = 'LoPy'                                                     # Para detectar guardados corruptos
        self.update = [0,0]                                                     # El valor de (aceleracion,giro) ha sido actualizado
        self.interval = 20                                                      # Intervalo toma de datos
        Acelerometro.acc = LIS2HH12(pysense)
        if (Acelerometro.acc is not None):
            print('Cargado Acelerometro con éxito')
            self.alarma = Timer.Alarm(self.leeraceleracion,                     # Alarma de toma de datos de aceleracion
                                        self.interval, periodic=True)
            self.alarmg = Timer.Alarm(self.leerroll,                             # Alarma de toma de datos de giro
                                        self.interval, periodic=True)
    def leeraceleracion(self,alarma):
        self.raw = Acelerometro.acc.acceleration()                              # Devuelve tuple con aceleracion en tres ejes (G)
        self._compare_update('A')
        print("Aceleracion-> X:%fG Y:%fG Z:%fG"
                %(self.raw[0],self.raw[1],self.raw[2]))
    def leerroll(self,alarmg):
        self.rawg[0] = Acelerometro.acc.roll()                                    # Devuelve float con roll (º)
        print("Roll: %f º" %self.rawg[0])
        self.leerpitch()
    def leerpitch(self):
        self.rawg[1] = Acelerometro.acc.pitch()                                  # Devuelve float con Pitch (º)
        print("Pitch: %f º" %self.rawg[1])
        self.leeryaw()
    def leeryaw(self):
        self.rawg[2] = Acelerometro.acc.yaw()                                    # Devuelve float con Yaw (º)
        self._compare_update('G')
        print("Yaw: %f º" %self.rawg[2])
    def _compare_update(self,sensor=None):
        if sensor is 'A':
            if self.raw is not self.last:
                self.last = self.raw
                self.update[0] = 1
            else:
                self.update[0] = 0
        elif sensor is 'G':
            if self.rawg is not self.lastg :
                self.lastg = self.rawg
                self.update[1] = 1
            else:
                self.update[1] = 0
        else:
            print("Error de actualización; sensor no reconocido")
    def desactPub(self,sensor=None):
        if sensor is 'A':
            self.alarma.cancel()
            print("Desactivada publicación Aceleracion")
            return
        elif sensor is 'G':
            self.alarmg.cancel()
            print("Desactivada publicación Orientacion")
            return
        else:
            print("Sensor no reconocido")
            return
    def activarPub(self,sensor=None):
        if sensor is 'A':
            self.alarma.cancel()
            self.alarma = Timer.Alarm(self.leeraceleracion,
                                        self.interval, periodic=True)
            print("Activada publicación Aceleracion")
            return
        elif sensor is 'G':
            self.alarmg.cancel()
            self.alarmg = Timer.Alarm(self.leerroll,
                                        self.interval, periodic=True)
            print("Activada publicación Orientacion")
            return
        else:
            print("Sensor no reconocido")
