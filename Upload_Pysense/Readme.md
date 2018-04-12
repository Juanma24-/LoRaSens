Pysense Software
================================================================================
This file is intended to explain the way the software for Pysense works.
This Library files and "_main.py" file should not be modified. Only "_boot.py"
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
* https://docs.pycom.io/pycom_esp32/index.html

### Firmware

This software can work with several ESP32 firmware configurations, but the
author recommends to use the low power consumption configuration. This
configuration includes the only use of core 0 and a CPU frequency of 80 MHz
instead of 160 MHz (default).  

To do so, it is needed to use the firmware modified by the author.
To compile this firmware, it is needed to execute the configuration shell script
on `~/esp/wifi-scan/`. This script changes the firmware libraries with the new
configuration and copy it to the pycom firmware (need to check the path).

Next step is to execute the FullBuild shell script on
`/pycom-micropython-sigfox/esp32/` which can be downloaded on
[pycom-micropython-sigfox]().

APP ARQUITECTURE
--------------------------------------------------------------------------------
