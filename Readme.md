README
================================================================================
This folder contains all the firmware and software projects developed for the
LoPy/LoPy4 device based on the LoRaWAN communication protocol.
In this file, a brief description of the different projects is given in order to
make easier their use.

__PROJECTS__  
* SOFTWARE
  - lorawan-nano-gateway: This folder contains the software of a single-channel
  LoRaWAN gateway. It has been used successfully to test the rest of the projects.
  - Upload_Pysense: Main project. It obtains the measurements from the sensors
  and send via LoRaWAN on a fixed interval. It is optimized to save as much
  power as possible. IT REQUIRES PYSENSE BOARD.
  - Upload_Pysense_OTA: Same as Upload_Pysense, but it also has the possibility
  to upgrade the firmware via Wi-Fi. IT REQUIRES PYSENSE BOARD.
  - Upload_MachineDeepsleep: The purpose of this project is to get rid of the
  Pysense Board (its processor wastes a lot of power). Its performance is the
  same, but it is needed to add sensors.
  - OTAA_Aceleracion_STOPPED: This project aims to measure the acceleration of
  the device and to send the data if a certain threshold is passed, but the
  project is stopped right now. IT REQUIRES PYSENSE BOARD.
* FIRMWARE
  - Original_Pycom: Last version of the LoPy/LoPy4 firmware developed by Pycom.
  This firmware is not optimized for the software projects, but if some unknown
  problem appears is a good point to start all the tests.
  - pycom-micropython-sigfox: Firmware of the LoPy/LoPy4 modified to minimize
  its power consumption and therefore to boost the software projects efficiency.
  This is one of the main folders.
  - pycom_firmware_update_1.1.2.b2: program to update the firmware of the
  LoPy/LoPy4. It is needed when the device do not answer to the rest of available
  methods.
  - ServerFiles: Example of a OTA server folder. This folder has to be placed on
  the OTA server. 
