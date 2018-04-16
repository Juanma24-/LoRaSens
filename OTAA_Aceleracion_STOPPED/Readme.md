README
================================================================================
This folder contains an app developed for Lopy + Pysense in which it is read the  
device acceleration (in Gs) and if this acceleration is above a maximum, the
values are sent via LoRaWAN to the Network Server.  
As auxiliary funcionalities, it is possible to enable/disable the acceleration
measurement with a downlink message or to modify the data rate of the device
sending.

__IMPORTANT__

Init Tutorials:
* https://github.com/ttn-liv/devices/wiki/Getting-started-with-the-PyCom-LoPy  
* https://docs.pycom.io/pycom_esp32/index.html

BUILD
--------------------------------------------------------------------------------
Para compilar una aplicación sin necesidad de tener conectado un dispositivo
LoPy al ordenador, es necesario instalar
To make the build it is needed to follow first the section INSTALL FIRMWARE,
insert the app files inside _esp32/frozen_ folder and build:
~~~
cd esp32
make BOARD=LOPY4 LORA_BAND=USE_BAND_868 clean
make BOARD=LOPY4 LORA_BAND=USE_BAND_868 TARGET=boot
make BOARD=LOPY4 LORA_BAND=USE_BAND_868 TARGET=app
~~~
To make things easier, there is a shell script named FullBuild.sh which can be
downloaded [here](https://github.com/Juanma24-/pycom-micropython-sigfox/tree/master/esp32).

APP ARQUITECTURE
--------------------------------------------------------------------------------
The app only contains 5 files; boot file, the main app and the sensor library (3).
The tree file is this:  
* Main Folder->  
    * boot.py (Init and select main file)   
    * otaa_node_acc.py (main file)
    * LIS2HH12.py (accelerometer library)
    * pysense.py
    * pycoproc.py


_If the files are charged via FTP._  
The first 2 file must be put on the flash folder of the file system of the
device (/flash). The sensor library must be put on the /lib folder of the intern
memory of the device.  
_If the files are charged via flashing firmware._  
The boot file must be renamed to _boot and the ota_node_acc file must be renamed
to _main.

APP USE (DATA SENDING AND RECEPTION)
--------------------------------------------------------------------------------
The sending/reception of data to/from the node is made by LoRaWAN protocol,
therefore to optimize the power consumption, gateway use and not to overpass
limitations some Network Servers have, it is needed to the reduce the message
size to its minimum.

### Sending
Data sending is programmed to send a bytes string that contains only the sensor
value in a specific order. An array of 6 values are sent; the 3 axis acceleration
before overpassed the threshold and the 3 axis acceleration once the threshold
has been overpassed. This string is the minimum quantity of information that can
be send.  
In this app not all the measturements are sent to the device, however, the
measurement frequency will be superior to the maximum data sending frequency.
This can bring sending errors if the socket is busy when another message wants
to be sent. To solve this problem the use of threads and mutex to access a
shared resource has been used.
### Reception
Data reception takes place after data sending, if a correct string is received,
three different options can be execute.

* _Interval Change Message_  
   This message has not a maximum defined length because it depends on the number
   of seconds in hexadecimal. The minimum length is 2 bytes, being the first
   byte the ASCII code of "I" letter on hexadecimal code (0x49). The rest of the
   payload corresponds to the number of seconds on hexadecimal code.
   E.g: `49 64`= I 100
* _Cancel Message_  
  The ASCII letter "C" is sent to cancel the measurement.
  E.g: `43` = C
  The ASCII letter "C" is sent to cancel the measurement.
* _Data Rate Modification Message_  
  This message allows to modify data rate in a dinamic way. Data Rate values are
  fixed (0 to 5), therefore length is also fixed to 2 bytes. First bytes
  corresponds to ASCII letter "R" (0x52). Second byte corresponds to the new
  data rate.
  E.g: `52 05`= R 5

__IMPORTANT__  
Although codifications are done in hexadecimal format, the device turns them
into decimal, therefore the user has to take into account that if number strings
have to be compared.


MQTT
--------------------------------------------------------------------------------
To check if the device and the Network Server are working fine and sending the
messages on a right way, the mqtt client Mosquitto can be configure in the next
way:

__ATTENTION!! EVERY ORDER ARE THOUGHT TO BE USE WITH TTN NETWORK SERVER__

### Subscription
```
mosquitto_sub -h eu.thethings.network:1883 -t '<AppId/devices/<DevID>/up' -u
'<AppID>' -P '<AppKey>' -v
```
Every field to be complete can be found on the app description created on TTN.

### Publish
To send a command (defined on the last section), the next order must be called:
~~~
mosquitto_pub -h <Region>.thethings.network -t '<AppID>/devices/<DevID>/down' -u
 '<AppID>' -P '<AppKey>' -m '{"payload_raw":""}'
~~~
The `payload_raw`field has to be codified in Base64. Due to orders has been
designed in bytes format (hexadecimal), they have to be convert using a tool
like [this](http://tomeko.net/online_tools/hex_to_base64.php?lang=en).

INSTALL FIRMWARE
--------------------------------------------------------------------------------
1.-  __Obtain pycom-micropython-sigfox__
~~~
git clone https://github.com/pycom/pycom-micropython-sigfox.git
cd pycom-micropython-sigfox
git submodule update --init
~~~
2.- __Install Toolchain__
~~~
sudo easy_install pip
sudo pip install pyserial
~~~
Download:
https://dl.espressif.com/dl/xtensa-esp32-elf-osx-1.22.0-61-gab8375a-5.2.0.tar.gz
~~~
mkdir -p ~/esp
cd ~/esp
tar -xzf ~/Downloads/xtensa-esp32-elf-osx-1.22.0-61-gab8375a-5.2.0.tar.gz
~~~
3.- __Set Enviroment Variables__  
Modify .profile file (inside root folder ~) and add the following lines:
~~~
export PATH=$PATH:$HOME/esp/xtensa-esp32-elf/bin
export IDF_PATH=~/esp/pycom-esp-idf
~~~
4.- __Obtain Espressif__
~~~
cd ~/esp
git clone https://github.com/pycom/pycom-esp-idf.git
cd ~/esp/esp-idf
git submodule update --init
~~~
5.- __Compile mpy-cross__  
~~~
cd pycom-micropython-sigfox/mpy-cross
make all
~~~
