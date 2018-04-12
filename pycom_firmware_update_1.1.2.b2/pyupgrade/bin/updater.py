#!/usr/bin/env python

#   Copyright (c) 2016-2017, Pycom Limited.
#
#   This software is licensed under the GNU GPL version 3 or any
#   later version, with permitted additional terms. For more information
#   see the Pycom Licence v1.0 document supplied with this file, or
#   available at https://www.pycom.io/opensource/licensing

from esptool import ESP32ROM
import esptool
import argparse

import os
import sys
import tarfile
import json
import cStringIO
import struct
import base64

HERE_PATH = os.path.dirname(os.path.realpath(__file__))

FAST_BAUD_RATE = 921600
SLOW_BAUD_RATE = 57600

FLASH_SIZE = 4*1024*1024

def print_exception(e):
    print ('Exception: {}, on line {}'.format(e, sys.exc_info()[-1].tb_lineno))

class Args(object):
    pass

def load_tar(fileobj):
    tar = tarfile.open(mode="r:gz", fileobj = fileobj)
    script = json.load(tar.extractfile("script"))
    for i in range(len(script)):
        if script[i][0] == 'w':
            script[i][2] = tar.extractfile(script[i][2]).read()
    tar.close()
    return script

class NPyProgrammer(object):
    def __init__(self, port, baudrate, continuation=False):
        if continuation == False:
            self.esp = ESP32ROM(port, SLOW_BAUD_RATE)
            self.esp.connect()
            self.esp = self.esp.run_stub()
            self.esp.change_baud(baudrate)
        else:
            esp = ESP32ROM(port, baudrate)
            self.esp = esp.STUB_CLASS(esp) # enable the stub functions


    def read(self, offset, size):
        return self.esp.read_flash(offset, size)

    def erase(self, offset, section_size):

        MAX_SECTION_SIZE = 0x380000

        offset = (offset // 4096) * 4096
        iterations = (section_size + MAX_SECTION_SIZE - 1) // MAX_SECTION_SIZE

        for i in range(iterations):
            s = min(section_size, MAX_SECTION_SIZE)
            s = ((s + 4095) // 4096) * 4096
            self.esp.erase_region(offset, s)
            offset += s

    def write(self, offset, contents):
        args = Args()

        args.flash_size = 'detect'
        args.flash_mode = 'dio'
        args.flash_freq = '80m'
        args.compress = True
        args.verify = False
        args.no_stub = False

        fmap = cStringIO.StringIO(contents)
        args.addr_filename = [[offset, fmap]]

        esptool.write_flash(self.esp, args)
        fmap.close()

    def run_script(self, script):
        for instruction in script:
            if instruction[0] == 'e':
                self.erase(int(instruction[1], 16), int(instruction[2], 16))
            elif instruction[0] == 'w':
                self.write(int(instruction[1], 16), instruction[2])

    def erase_sytem_mem(self):
        # Erase first 3.5Mb (this way fs and MAC address will be untouched)
        self.erase(0, 0x3100000)

    def flash_bin(self, dest_and_file_pairs):
        args = Args()

        args.flash_size = 'detect'
        args.flash_mode = 'dio'
        args.flash_freq = '80m'
        args.compress = True
        args.verify = True

        dest_and_file = list(dest_and_file_pairs)

        for i, el in enumerate(dest_and_file):
            dest_and_file[i][1] = open(el[1], "rb")

        args.addr_filename = dest_and_file

        esptool.write_flash(self.esp, args)

    def read_mac(self):
        # returns a tuple with (wifi_mac, bluetooth_mac)
        return self.esp.read_mac()

def process_arguments():
    cmd_parser = argparse.ArgumentParser(description='Update your Pycom device with the specified firmware image file')
    cmd_parser.add_argument('-f', '--file', default=None, help='the path of the firmware file')
    cmd_parser.add_argument('-p', '--port', default=None, required=True, help='the serial port to use')
    cmd_parser.add_argument('-t', '--tar', default=None, help='perform the upgrade from a tar')
    cmd_parser.add_argument('-s', '--speed', default=115200, type=int, help='baudrate')
    cmd_parser.add_argument('-a', '--address', default=None, type=int, help='address to write to')
    cmd_parser.add_argument('-c', '--continuation', action='store_true', help='continue previous connection')
    cmd_parser.add_argument('--contents', default=None, help='contents of the memory to write (base64)')
    cmd_parser.add_argument('command', choices=['flash', 'smac', 'wmac', 'write'], help='command: flash, smac, wmac, write')


    args = cmd_parser.parse_args()
    try:
        if args.file is None and args.tar is None and args.command == 'flash':
            raise ValueError('The tar or image file path must be specified')
    except Exception as e:
        print_exception(e)
        sys.exit(1)

    return args

def mac_to_string(mac):
    result = ''

    if type(mac) == str:
        m = []
        for c in mac:
            m.append(struct.unpack("B", c)[0])
        mac = m

    for c in mac:
        result += '{:02X}'.format(c)

    return result

def main():
    args = process_arguments()
    bin_dests_and_filenames = [[0x1000, HERE_PATH + '/../firmware/bootloader.bin'], [0x8000, HERE_PATH + '/../firmware/partitions.bin'], [0x10000, args.file]]
    try:
        nPy = NPyProgrammer(args.port, args.speed, args.continuation)
        if args.command == 'flash':
            if args.tar != None:
                tar_file = open(args.tar, "rb")
                script = load_tar(tar_file)
                nPy.run_script(script)
            else:
                nPy.erase_sytem_mem()
                nPy.flash_bin(bin_dests_and_filenames)
        elif args.command == 'wmac':
            print("WMAC=%s" % mac_to_string(nPy.read_mac()))
        elif args.command == 'smac':
            print("SMAC=%s" % mac_to_string(nPy.read(FLASH_SIZE - 4096, 8)))
        elif args.command == 'write':
            nPy.write(args.address, base64.b64decode(args.contents))


    except Exception as e:
        print_exception(e)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
