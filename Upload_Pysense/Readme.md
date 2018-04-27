Pysense Software
================================================================================
This file is intended to explain the way the software for Pysense works.
The library files and "_main.py" file should not be modified. Only "_boot.py"
can be modified in order to show more info about the device on the boot or to
enable UART for debugging purposes.

__IMPORTANT__  
To keep the device battery as much time as possible, deepsleep function is used.
Using LoPy and Pysense, deepsleep can be accessed in two different ways: using
the LoPy function and using the Pysense function.  

It has been decided to used the Pysense function because using this hardware
configuration is the option with the best performance. This [forum thread](https://forum.pycom.io/topic/1589/deep-sleep-summary/2)
confirms it.

__INIT TUTORIAL__
* https://github.com/ttn-liv/devices/wiki/Getting-started-with-the-PyCom-LoPy  
* https://docs.pycom.io/
### Performance  

The software executes a infinite loop with two parts. The first (almost all time),
the device is in deepsleep mode, saving power. When the device awakes, it
measures the Pysense sensors and sends the data via LoRaWAN.

This loop can only be broken when the Pysense button is pressed. If this button
is pressed, the device enables Wi-Fi and Telnet and FTP servers and its file
system can be modified remotely.

When the device is booted the first time, it connect with the LoRaWAN Network
Server via OTAA procedure. For testing, The Things Network Server has been used,
however, with the correct gateway any Network Server (like for example Loriot)
can be used.

The device can also receive two kind of downlink messages, to chenge the
measurement interval and to change the data rate.
* Changing the measurement interval
	This message has not a minimum length of 2 bytes. The first byte corresponds to
	the ASCII code of 'I' letter in hexadecimal format (0x49). The rest of the
	payload corresponds to the number of seconds of the new interval.
	E.g: `49 64`= I 100

* Changing Data Rate
	This message has a fixed length of 2 bytes because the data rate options are
	also fixed (0 to 5). The first byte corresponds to the ASCII code of 'R'
	letter in hexadecimal format (0x52). The second byte of the payload corresponds to
	the new data rate number.
	E.g: `52 05`= R 5

### Firmware

The original firmware developed by Pycom has been modified to achieve a better
performance about power consumption in active mode. For this reason, the modified
firmware has to be downloaded and charge using the following instructions.

This software can work with several ESP32 firmware configurations, but the
author recommends to use the low power consumption configuration. This
configuration includes the only use of core 0 and a CPU frequency of 80 MHz
instead of 160 MHz (default).  

To do so, it is needed to use the firmware modified by the author.
To compile this firmware, it is needed to execute the configuration shell script
on `~/esp/wifi-scan/`. This script changes the firmware libraries with the new
configuration and copy it to the pycom firmware (need to check the path of
pycom-micropython-sigfox on libs.sh file, the libs.sh file can be downloaded [here](https://github.com/Juanma24-/pycom-micropython-sigfox/tree/master/esp32).

Next step is to execute the FullBuild shell script on
`/pycom-micropython-sigfox/esp32/` which can be downloaded on
[pycom-micropython-sigfox](https://github.com/Juanma24-/pycom-micropython-sigfox).


COMPILE SOFTWARE INSTALATION
--------------------------------------------------------------------------------
1.-  __Obtain pycom-micropython-sigfox__
~~~
git clone https://github.com/Juanma24-/pycom-micropython-sigfox.git
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
3.- __Set Variables__  
Modify archive .profile (inside root folder ~) and add next line:
~~~
export PATH=$PATH:$HOME/esp/xtensa-esp32-elf/bin
export IDF_PATH=~/esp/pycom-esp-idf
~~~
4.- __Obtain Espressif__
~~~
cd ~/esp
git clone https://github.com/pycom/pycom-esp-idf.git
cd ~/esp/pycom-esp-idf
git submodule update --init
~~~
(The paths are now relative to the install folder and not absolute)
5.- __Compile mpy-cross__  
~~~
cd pycom-micropython-sigfox/mpy-cross
make all
~~~

BUILD PROCESS
--------------------------------------------------------------------------------
1.- __Compile ESP-IDF Libraries__
~~~
cp ~/esp/pycom-esp-idf/examples/wifi/scan ~/esp/
cd ~/esp/scan/
~~~
Libs file opens the ESP32 configuration window, in that window the following changes have to be made.
~~~   
Bootloader config--> Bootloader log verbosity ---> Debug
Component config --> Bluetooth 			   ---> [ ] Bluetooth
				 --> ESP32-specific 	      ---> CPU Frequency -> 80MHz
								              ---> [ ] Reserve memory for two cores
				 --> Free RTOS                ---> [*] Run FreeRTOS only on first core
				 --> Log output               ---> Default log verbosity ->  Debug
~~~
cp /pycom-micropython-sigfox/esp32/libs.sh ~/esp/scan/
bash libs.sh
~~~
2.-__Compile Firmware__
~~~
cd /pycom-micropython-sigfox/esp32/
bash FullBuild.sh
~~~

MQTT
--------------------------------------------------------------------------------

To check if the device and the Network Server are sending messages in the correct
way, MQTT broker Mosquitto can be used in the following way:
__ATTENTION!! ALL THE CODE IS THOTUGHT TO BE USED WITH THE THING NETWORK SERVER ONLY__  

### Subscribe
```
mosquitto_sub -h eu.thethings.network:1883 -t '<AppId/devices/<DevID>/up' -u
'<AppID>' -P '<AppKey>' -v
```
All the fields can be found on the App description that has been created on TTN.

### Publish
Publish will be made through the private broker to the Network Server.
To send a command, next order has to be be used:
~~~
mosquitto_pub -h <Region>.thethings.network -t '<AppID>/devices/<DevID>/down' -u
 '<AppID>' -P '<AppKey>' -m '{"payload_raw":""}'
~~~
The `payload_raw` field has to be codified in Base64. The orders has been thought
for hexadecimal format, and a tool like [this](http://tomeko.net/online_tools/hex_to_base64.php?lang=en)
can be used to perform the conversion.
