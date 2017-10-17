#Librería Sensor de Luz
#JUAN MANUEL GALÁN SERRANO
#ALSTOM-UPC 2017
#==============================================================================#

#==============================================================================#
from machine import Timer
from pysense import Pysense
from LTR329ALS01 import LTR329ALS01
class LuzSensor:
    """
        Funciones de control del sensor de Luminosidad LTR329ALS01.
    """
    ambientLight = None

    def __init__(self, pysense=None):
        if pysense is None:
            self.pysense = Pysense()
        self.last = 0                                                           # Último valor leído
        self.raw = 0                                                            # Actual valor de Luminosidad
        self.magic = 'LoPy'                                                     # Para evitar lecturas corruptas en SD
        self.update = 0                                                         # El valor de Luminosidad ha sido actualizado
        self.interval = 20                                                      # Intervalor de toma de datos
        LuzSensor.ambientLight = LTR329ALS01(pysense)
        if (LuzSensor.ambientLight is not None):
            print('Cargado Sensor Luz con éxito')
            self.alarml = Timer.Alarm(self.leerlux,
                                        self.interval, periodic=True)
    def leerlux(self,alarml):                                                   # Devuelve un tuple de 2 valores de luminosidad en lux
        self.raw = LuzSensor.ambientLight.light()
        self._compare_update()
        print("Luminosidad:(%d,%d)lux" %(self.raw[0],self.raw[1]))
    def _compare_update(self):
        if self.raw is not self.last :
            self.last = self.raw
            self.update = 1
        else:
            self.update = 0
    def desactPub(self):
        self.alarml.cancel()
        print("Desactivada publicación Sensor Luminosidad")
    def activarPub(self):
        self.alarml.cancel()
        self.alarml = Timer.Alarm(self.leerlux, self.interval, periodic=True)
        print("Activada publicación Sensor Luminosidad")
