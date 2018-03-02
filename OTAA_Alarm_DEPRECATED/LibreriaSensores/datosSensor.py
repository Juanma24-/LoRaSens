#CLASE PARA ALMACENAR LOS DATOS DE LOS SENSORES
#ESTRUCTURA
from machine import Timer
from pysense import Pysense
from LTR329ALS01 import LTR329ALS01
from LIS2HH12 import LIS2HH12
from SI7006A20 import SI7006A20
from MPL3115A2 import MPL3115A2

class Lectura:
    """Clase encargada de gestionar las lecturas de todos los sensores
        de la placa Pysense.
        Se crea una instancia para cada sensor. Utilizando las funicones
        necesarias de cada sensor.
    """
    ambientLight = None
    pressure = None
    tempHum = None
    acc = None

    def __init__(self, pysense=None,sensor=''):
        if pysense is None:
            self.pysense = Pysense()
        self.last = 0
        self.raw = 0
        self.magic = 'LoPy'
        self.update = 0
        self.interval = 20
        #TODO:Pasar a estructura try except
        if sensor is 'L':
            Lectura.ambientLight = LTR329ALS01(pysense)
            if Lectura.ambientLight is not None:
                print('Cargado Sensor Luz con éxito')
            self.__alarm = Timer.Alarm(self.leerlux(), self.interval, periodic=True)
        elif sensor is 'P':
            Lectura.pressure = MPL3115A2(pysense)
            if Lectura.pressure is not None:
                print('Cargado Sensor Presión con éxito')
        elif sensor is 'H':
            Lectura.tempHum = SI7006A20(pysense)
            if Lectura.tempHum is not None:
                print('Cargado Sensor Humedad con éxito')
        elif sensor is 'A':
            Lectura.acc = LIS2HH12(pysense)
            if Lectura.acc is not None:
                print('Cargado Acelerómetro con éxito')
        else:
            print('No se ha seleccionado ningún sensor')


    def leerlux(self):
        self.raw = Lectura.ambientLight.lux()
        self.compare_update()
        #return self.raw
        print(self.raw)
    def leerpresion(self):
        self.raw = Lectura.pressure.alt()
        self.compare_update()
        return self.raw
    def leerhumedad(self):
        self.raw = Lectura.tempHum.humidity()
        self.compare_update()
        return self.raw
    def compare_update(self):
        if self.raw is not self.last :
            self.last = self.raw
            self.update = 1
        else:
            self.update = 0
