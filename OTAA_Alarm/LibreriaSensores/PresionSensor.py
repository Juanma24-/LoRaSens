#Librería Sensor de Presion
#JUAN MANUEL GALÁN SERRANO
#ALSTOM-UPC 2017
#==============================================================================#
# Sensor de Presión.
# Es posible la lectura de presión en dos formatos: presión o altura. Ambos
# métodos han sido desarrollados en esta librería auxiliar. El sensor también es
# capaz de realizar lecturas de temperatura pero dado que se dispone de un sensor
# únicamente destinado a ello, no se ha desarrollado esa funcionalidad.
#==============================================================================#

from machine import Timer
from pysense import Pysense
from MPL3115A2 import MPL3115A2
class PresionSensor:
    """
        Funciones de control del sensor de Humedad SI7006A20.
    """
    pressure = None

    def __init__(self, pysense=None):
        if pysense is None:
            self.pysense = Pysense()
        self.last = 0                                                           # Último valor leído
        self.raw = 0                                                            # Valor actual de Presión
        self.magic = 'LoPy'                                                     # Para evitar lecturas corruptas de SD
        self.update = 0                                                         # Se ha tomado un nuevo valor
        self.interval = 20                                                      # Intervalo(s) de toma de datos
        PresionSensor.pressure = MPL3115A2(pysense)
        if (PresionSensor.pressure is not None):
            print('Cargado Sensor Presion con éxito')
            self.alarmp = Timer.Alarm(self.leerpresion,
                                        self.interval, periodic=True)
    def leerpresion(self,alarmp):
        self.raw = PresionSensor.pressure.pressure()                            # Devuelve float con presion en Pascales
        self._compare_update()                                                  # Compara con la ultima medida y actualiza si no coinciden
        print("Presion: %fPa" %self.raw)
    def leeraltura(self,alarmp):
        self.raw = PresionSensor.pressure.altitude()                            # Devuelve float con altura en metros
        self._compare_update()
        print("Altura: %fm" %self.raw)
    def _compare_update(self):
        if self.raw is not self.last :
            self.last = self.raw
            self.update = 1
        else:
            self.update = 0
    def desactPub(self):
        self.alarmp.cancel()
        print("Desactivada publicación Sensor Presion")
    def activarPub(self):
        self.alarmp.cancel()
        self.alarmp = Timer.Alarm(self.leerpresion,
                                    self.interval, periodic=True)
        print("Activada publicación Sensor Presión")
