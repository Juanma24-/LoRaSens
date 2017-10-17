import math
import struct

class LIS2HH12:

    ACC_I2CADDR = const(30)

    PRODUCTID_REG = const(0x0F)
    ACT_THS_REG = const(0x1E)                                                   #Activation Threshold (Default: 0000 0000)
    ACT_DUR_REG = const(0x1F)                                                   #Desactivation Minimal Duration (Default: 0000 0000)
    CTRL1_REG = const(0x20)                                                     #Default: 0000 0111
    CTRL2_REG = const(0x21)                                                     #Default: 0000 0000
    CTRL3_REG = const(0x22)                                                     #INT1 Control Register (Default: 0000 0000)
    CTRL4_REG = const(0x23)                                                     #Default: 0000 0100
    CTRL5_REG = const(0x24)                                                     #(Default: 0000 0000)
    CTRL6_REG = const(0x25)                                                     #(Default: 0000 0000)
    CTRL7_REG = const(0x26)                                                     #(Default: 0000 0000)
    IG_CFG1_REG = const(0x30)                                                   #Interrupt Generator 1 configuration (Default: 0000 0000)
    IG_SRC1_REG = const(0x31)                                                   #Interrupt Generator 1 Status Register (OUTPUT)
    IG_THS_X1_REG = const(0x32)                                                 #Interrupt Generatos 1 Threshold X (Default: 0000 0000)
    IG_THS_Y1_REG = const(0x33)                                                 #Interrupt Generatos 1 Threshold Y (Default: 0000 0000)
    IG_THS_Z1_REG = const(0x34)                                                 #Interrupt Generatos 1 Threshold Z (Default: 0000 0000)
    IG_DUR1_REG = const(0x39)                                                   #Interrupt Generator 1 Duration (Default: 0000 0000)
    ACC_X_L_REG = const(0x28)                                                   #OUT_X_L
    ACC_X_H_REG = const(0x29)                                                   #OUT_X_H
    ACC_Y_L_REG = const(0x2A)                                                   #OUT_Y_L
    ACC_Y_H_REG = const(0x2B)                                                   #OUT_Y_H
    ACC_Z_L_REG = const(0x2C)                                                   #OUT_Z_L
    ACC_Z_H_REG = const(0x2D)                                                   #OUT_Z_H

    SCALE = const(8192)

    def __init__(self, pysense = None, sda = 'P22', scl = 'P21'):
        if pysense is not None:
            self.i2c = pysense.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.reg = bytearray(1)

        self.x = 0
        self.y = 0
        self.z = 0

        whoami = self.i2c.readfrom_mem(ACC_I2CADDR , PRODUCTID_REG, 1)
        if (whoami[0] != 0x41):
            raise ValueError("Incorrect Product ID")

        # enable acceleration readings
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL1_REG, self.reg)
        self.reg[0] &= ~0b01110000
        self.reg[0] |= 0b00110000
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL1_REG, self.reg)

        # change the full-scale to 4g
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL4_REG, self.reg)
        self.reg[0] &= ~0b00110000
        self.reg[0] |= 0b00100000
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL4_REG, self.reg)
        '''
        #Modify Threshold and Duration (ODR = 100Hz)
        self.i2c.readfrom_mem_into(ACC_I2CADDR , ACT_THS_REG, self.reg)
        self.reg[0] |= 0b00110000                                               #1500mg
        self.i2c.writeto_mem(ACC_I2CADDR , ACT_THS_REG, self.reg)
        self.i2c.readfrom_mem_into(ACC_I2CADDR , ACT_DUR_REG, self.reg)
        self.reg[0] |= 0b00011001                                               #0.24s
        self.i2c.writeto_mem(ACC_I2CADDR , ACT_DUR_REG, self.reg)
        #Enable Interrupt
        self.i2c.readfrom_mem_into(ACC_I2CADDR , CTRL3_REG, self.reg)
        self.reg[0] |= 0b00100000                                               #INT1_INACT Enable
        self.i2c.writeto_mem(ACC_I2CADDR , CTRL3_REG, self.reg)
        '''
        # make a first read
        self.acceleration()

    def acceleration(self):
        x = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_X_L_REG, 2)
        self.x = struct.unpack('<h', x)
        y = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_Y_L_REG, 2)
        self.y = struct.unpack('<h', y)
        z = self.i2c.readfrom_mem(ACC_I2CADDR , ACC_Z_L_REG, 2)
        self.z = struct.unpack('<h', z)
        return (self.x[0] / SCALE, self.y[0] / SCALE, self.z[0] / SCALE)

    def roll(self):
        div = math.sqrt(math.pow(self.y[0], 2) + math.pow(self.z[0], 2))
        if div == 0:
            div = 0.01
        return (180 / 3.14154) * math.atan(self.x[0] / div)

    def pitch(self):
        if self.z[0] == 0:
            div = 1
        else:
            div = self.z[0]
        return (180 / 3.14154) * math.atan(math.sqrt(math.pow(self.x[0], 2) + math.pow(self.y[0], 2)) / div)

    def yaw(self):
        div = math.sqrt(math.pow(self.x[0], 2) + math.pow(self.z[0], 2))
        if div == 0:
            div = 0.01
        return (180 / 3.14154) * math.atan(self.y[0] / div)
