README
================================================================================

To config the NanoGateway three parameters has to be modified depending the
network server which is going to be used. This parameters are set on config.py
file and two different options are possible:
* The Things Network. For using this network server, the gateway ID must have
the form ` WIFI_MAC[:6] + "FFFE" + WIFI_MAC[6:12], the Server direction must be
`router.eu.thethings.network` and the port must be 1700.  

* Loriot. For using this network server, the gateway ID must have
the form ` WIFI_MAC[:6] + "FFFF" + WIFI_MAC[6:12], the Server direction must be
`eu1.loriot.io` and the port must be 1780.


Although two different options has been provided, it is not recommend to use the
Loriot option. The reason is that the Nanogateway use a single channel and it
software is limited. Loriot do not handle well this kind of gateway and therefore
after a reboot of the gateway, the device lost the connection with the server,
being not possible to recover it without rebooting the device.

FTP SERVER USE
--------------------------------------------------------------------------------
With the Nanogateway software, it is recommended to use the official Pycom
Firmware. After loading the firmware, the FTP server is enabled. This is the
easiest way to upload files (author opinion). To do so, this is the FTP
configuration:
* Host : 192.168.4.1
* User: micro
* Password: python
* Only use plain FTP (insecure)
* Transfer Mode: Passive

To transfer the files, a program like Filezilla can be used.

If the firmware has not been updated but it is necessary or wanted to change the
software, it is possible to go back to the a previous state using the expansion
board and connecting the G28 and 3V3 pin, pressing reset and waiting for 3 seconds
before removing the wire. The Wifi net will appear next.
