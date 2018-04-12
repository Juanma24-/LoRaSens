#!/usr/bin/env python

#   Copyright (c) 2016-2017, Pycom Limited.
#
#   This software is licensed under the GNU GPL version 3 or any
#   later version, with permitted additional terms. For more information
#   see the Pycom Licence v1.0 document supplied with this file, or
#   available at https://www.pycom.io/opensource/licensing

TOOL_VERSION = 67634305

import os
HERE_PATH = os.path.dirname(os.path.realpath(__file__))

from io import BytesIO
import requests
import json
import tarfile
import cStringIO
import sys
import struct
import base64
import binascii
sys.path.append(HERE_PATH) # fix for MacOS running from a different PWD

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMovie, QLabel
from PyQt4.QtCore import QThread, pyqtSignal, QObject, QSize, Qt

from bin.esptool import ESP32ROM
from bin import esptool

from bin.updater import NPyProgrammer
from bin.updater import FAST_BAUD_RATE
from bin.updater import SLOW_BAUD_RATE


FIRMWARE_TYPE = "all"
SERVER_URL = "https://software.pycom.io"
SIGFOX_CLIENT_NAME = "pycom"

countryList = []
regionList = []


def detectOsFamily():
    osFamily = sys.platform.rstrip('1234567890')
    if osFamily == 'linux':
        osFamily = 'unix'
    elif osFamily == 'win':
        osFamily = 'win32'
    elif osFamily == 'darwin':
        osFamily = 'macos'
    return osFamily

def load_tar(fileobj):
    tar = tarfile.open(mode="r:gz", fileobj = fileobj)
    script = json.load(tar.extractfile("script"))
    for i in range(len(script)):
        if script[i][0] == 'w':
            script[i][2] = tar.extractfile(script[i][2]).read()
    tar.close()
    return script

class Args(object):
    pass

class LoadingSpin(QLabel):
    def __init__(self):
        super(self.__class__, self).__init__()
        movie = QMovie(HERE_PATH + "/spinner.gif")
        movie.setScaledSize(QSize(23, 23))
        movie.setSpeed(200)
        self.setMovie(movie)
        movie.start()

class RunInWorker(QObject):
    __run_signal = pyqtSignal(object, object, object)
    __done_signal = pyqtSignal(object, object, object)
    __workerThread = None

    def __init__(self):
        super(self.__class__, self).__init__()
        if RunInWorker.__workerThread == None:
            RunInWorker.__workerThread = QThread()

        self.__done_signal.connect(self.__after) # slot in callers thread
        self.moveToThread(self.__workerThread)
        self.__run_signal.connect(self.__do_work) # slot in worker thread
        self.__workerThread.start()

    def __do_work(self, func, param, callback):
        self.__done_signal.emit(callback, func(param), param)

    def __after(self, callback, result, param):
        callback(result, param)

    def run(self, func, param, callback):
        self.__run_signal.emit(func, param, callback)

class FetchFiles(object):
    def __init__(self):
        self.__worker = RunInWorker()

    def __product_to_key(self, product, frequency=None):
        key = "%s.%s with esp32" % (product, product)
        if product == "lopy":
            key += "." + str(frequency)
        return key

    def get_file_worker(self, params):
        params['type'] = FIRMWARE_TYPE
        return requests.get(SERVER_URL + '/findupgrade',
                                params=params,
                                allow_redirects=True,
                                timeout=20
                ).content

    def get_file(self, key, redirect, callback):
        params = {
            'key': key,
            'redirect': str(redirect).lower(),
        }
        self.__worker.run(self.get_file_worker, params, callback)

    def find_new_firmware(self, callback, hardware, product, frequency=None):
        product = product.lower()
        key = self.__product_to_key(product, frequency)
        return self.get_file(key, False,
                            lambda res, req: callback(json.loads(res), key))

    def download_new_firmware(self, callback, key=None, product=None, frequency=None):
        if not key:
            product = product.lower()
            key = self.__product_to_key(product, frequency)
        return self.get_file(key, True, lambda res, req: callback(BytesIO(res)))

    def fetch_frequency_list(self, callback, product):
        product = product.lower()
        if product == "lopy" or product == "sipy":
            return self.get_file(product + ".freqlist", True, lambda res, req: callback(json.loads(res)))

    def fetch_updater_version(self, callback):
        self.get_file("pycom-firmware-updater." + detectOsFamily(),
                        False, lambda res, req: callback(json.loads(res)))

class DeviceInfoQuery(object):
    def __init__(self):
        self.__worker = RunInWorker()

    def __get_worker(self, params):
        r = requests.get(SERVER_URL + params['route'],
                                params=params['query'],
                                allow_redirects=True,
                                timeout=20)
        try:
            ret_val = r.json()
        except ValueError:
            ret_val = None

        return r.status_code, ret_val

    def __read_mac_worker(self, params):
        try:
            npy = NPyProgrammer(str(params['port']), params['speed'])
            return npy
        except:
            return None

    def __read_mac(self, params, callback):
        self.__worker.run(self.__read_mac_worker, params, callback)

    def __get(self, route, callback):
        params = {'route': route, 'query': {'toolversion': TOOL_VERSION}}
        self.__worker.run(self.__get_worker, params, callback)

    def __post_worker(self, params):
        r = requests.post(SERVER_URL + params['route'],
                                json=params['json'],
                                allow_redirects=True,
                                timeout=20)
        try:
            ret_val = r.json()
        except ValueError:
            ret_val = None

        return r.status_code, ret_val

    def __post(self, route, params, callback):
        params['toolversion'] = TOOL_VERSION
        self.__worker.run(self.__post_worker, {'route': route, 'json': params}, callback)

    def read_mac(self, port, speed, callback):
        return self.__read_mac({'port': port, 'speed': speed}, lambda res,req: callback(res))

    def get_info(self, wmac, callback):
        return self.__get('/device/get/' + wmac, lambda res,req: callback(res))

    def insert(self, name, wmac, smac, callback):
        json_parameters = {'name': name, 'wmac': wmac, 'smac': smac}
        return self.__post('/device/insert', json_parameters, lambda res,req: callback(res))

    def insert_sigfox(self, name, wmac, smac, zone, callback):
        json_parameters = {'name': name, 'wmac': wmac, 'smac': smac, 'zone': zone, 'client': SIGFOX_CLIENT_NAME}
        return self.__post('/device/insert/sigfox', json_parameters, lambda res,req: callback(res))

    def update_firmware_info(self, wmac, version, callback):
        json_parameters = {'wmac': wmac, 'version': version}
        return self.__post('/device/update/fwversion', json_parameters, lambda res,req: callback(res))

class DeviceUpgrade(object):
    def __init__(self):
        self.__worker = RunInWorker()

    def __upgradeWorker(self, params):
        try:
            params['npy'].run_script(params['script'])
            return 0
        except:
            return 1

    def upgrade(self, npy, script, callback):
        return self.__worker.run(self.__upgradeWorker, {'npy': npy, 'script': script}, lambda res,req: callback(res))

class CustomWizardPage(QtGui.QWizardPage):
    def __init__(self, nextTabMethod=None, isCompleteMethod=None):
        super(self.__class__, self).__init__()
        self.__isCompleteMethod = isCompleteMethod
        self.__nextTabMethod = nextTabMethod
        self.__nextPage = None

    # Note: This method is called more than once, tipically when the
    #       page is loaded and then when the next button is clicked
    def nextId(self):
        if self.__nextPage != None:
            n = self.__nextPage
            self.__nextPage = None
            return n

        if self.__nextTabMethod:
            return self.__nextTabMethod()
        return wizard.currentId() + 1

    def validatePage(self):
        if self.__isCompleteMethod:
            return self.__isCompleteMethod()
        return True

    def jumpPage(self, page):
        self.__nextPage = page
        self.wizard().next()

class CustomWizard(QtGui.QWizard):
    WELCOME_IDX  = 0
    SETUP_IDX    = WELCOME_IDX + 1
    SERIAL_IDX   = SETUP_IDX + 1
    GET_INFO_IDX = SERIAL_IDX + 1
    BOARD_IDX    = GET_INFO_IDX + 1
    COUNTRY_IDX  = BOARD_IDX + 1
    REGION_IDX   = COUNTRY_IDX + 1
    DOWNLOAD_IDX = REGION_IDX + 1
    WAIT_IDX     = DOWNLOAD_IDX + 1
    RESULT_IDX   = WAIT_IDX + 1

    def __init__(self):
        super(self.__class__, self).__init__()
        self.__onlineFirmwareVersions = {}
        self.__optionalCountryWidgets = []
        self.__upgrade = None
        self.__backgroundFetch = FetchFiles()
        self.__deviceInfoQuery = DeviceInfoQuery()
        self.__res_json = None
        self.__res_status = None
        self.__info_requested = False
        self.__info_obtained = False
        self.__w_mac_s = ''
        self.__s_mac_s = None
        self.__npy = None
        self.__sigfox_zone = 0
        self.__firmwareScript = None
        self.__board_connection_failed = False
        self.setPage(CustomWizard.WELCOME_IDX, self.__createIntroPage())
        self.setPage(CustomWizard.SETUP_IDX, self.__createSetupPage())
        self.setPage(CustomWizard.SERIAL_IDX, self.__createSerialPage())
        self.setPage(CustomWizard.GET_INFO_IDX, self.__createGetInfoPage())
        self.setPage(CustomWizard.BOARD_IDX, self.__createBoardPage())
        self.setPage(CustomWizard.COUNTRY_IDX, self.__createCountrySelectionPage())
        self.setPage(CustomWizard.REGION_IDX, self.__createRegionSelectionPage())
        self.setPage(CustomWizard.DOWNLOAD_IDX, self.__createDownloadWaitPage())
        self.setPage(CustomWizard.WAIT_IDX, self.__createWaitPage())
        self.setPage(CustomWizard.RESULT_IDX, self.__createConclusionPage())

        self.currentIdChanged.connect(self.__wizardPageShown)


    def __loadLoPyCountryList(self, result):
        global countryList
        countryList = result
        widget = self.__countrySelectorLoPy
        for e in countryList:
            widget.addItem(e[0])
        widget.insertSeparator(widget.count())
        widget.addItem("Not Listed")
        self.__countrySelectorSpinLoPy.hide()

    def __loadSiPyCountryList(self, result):
        global regionList
        regionList = result
        widget = self.__countrySelectorSiPy
        for e in regionList:
            widget.addItem(e[0])
        widget.insertSeparator(widget.count())
        self.__countrySelectorSpinSiPy.hide()

    def __rx_firmware_version(self, result, key):
        self.__onlineFirmwareVersions[key] = result['version']
        self.__newBoardSelected(0)

    def __rx_tool_version(self, result):
        if result['intVersion'] > TOOL_VERSION:
            msg = "<b>Note:</b> There is a new version of this tool! We recomend you to update it."
        else:
            msg = ""
        self.__findNewVersionMsg[2].removeWidget(self.__findNewVersionMsg[0])
        self.__findNewVersionMsg[2].removeWidget(self.__findNewVersionMsg[1])

        self.__findNewVersionMsg[2].addWidget(self.__findNewVersionMsg[0], 1, 0, 1, 3)
        self.__findNewVersionMsg[0].setText(msg)
        self.__findNewVersionMsg[0].adjustSize()
        self.__findNewVersionMsg[0].setWordWrap(True)
        self.__findNewVersionMsg[1].hide()

    def __firmwareDownloadCompleted(self, result):
        self.__firmwareScript = load_tar(result)
        if self.currentId() != self.DOWNLOAD_IDX:
            wizard.button(QtGui.QWizard.NextButton).setVisible(True)
        self.next()

    def __createIntroPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Welcome")

        introLabel = QtGui.QLabel("This wizard will help you upgrade your Pycom board firmware.")
        introLabel.setWordWrap(True)

        spin = LoadingSpin()
        searchMsg = QtGui.QLabel("Fetching updates for this tool...")
        searchMsg.adjustSize()

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        layout = QtGui.QGridLayout()
        layout.setVerticalSpacing(30)
        layout.addWidget(introLabel, 0, 0, 1, 3)
        layout.addWidget(searchMsg, 1, 0)
        layout.addWidget(spin, 1, 1)
        layout.addItem(spacerItem1, 1, 2)

        page.setLayout(layout)

        self.__findNewVersionMsg = [searchMsg, spin, layout]

        self.__backgroundFetch.fetch_updater_version(self.__rx_tool_version)

        return page

    def __createBoardPage(self):
        page = CustomWizardPage(self.__skipCountryIfNeeded)
        page.setTitle("Device type")
        page.setSubTitle("Please select the type of device to upgrade from the list.")

        boardLabel = QtGui.QLabel("Board:")
        boardLabel.adjustSize()

        boardSelector = QtGui.QComboBox()
        boardSelector.addItems(["LoPy", "WiPy 2.0", "SiPy"])
        boardSelector.setMinimumSize(QtCore.QSize(80, 0))
        boardSelector.currentIndexChanged.connect(self.__newBoardSelected)

        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        versionString = QtGui.QLabel("")

        layout = QtGui.QGridLayout()

        layout.addWidget(boardLabel, 0, 0)
        layout.addWidget(boardSelector, 0, 1)
        layout.addItem(spacerItem, 0, 2)
        layout.addWidget(versionString, 1, 1, 1, 2)
        layout.setVerticalSpacing(30)

        page.setLayout(layout)

        self.__firmwareVersionLabel1 = versionString

        page.registerField("board_selector", boardSelector)

        self.__fetchLastVersion = {}
        for el in [["LoPy", "868"], ["LoPy", "915"], ["WiPy", None], ["SiPy", None]]:
            self.__backgroundFetch.find_new_firmware(self.__rx_firmware_version, el, el[0], frequency=el[1])

        return page

    def __createCountrySelectionPage(self):
        page = CustomWizardPage(self.__skipRegion)
        page.setTitle("Country selection")
        page.setSubTitle("Please select your country:")

        countryLabel = QtGui.QLabel("Country:")
        countryLabel.adjustSize()

        frequencyLabel = QtGui.QLabel("Frequency:")
        frequencyLabel.adjustSize()
        mhzLabel = QtGui.QLabel("MHz")
        mhzLabel.adjustSize()

        countrySelector = QtGui.QComboBox()
        frequencySelector = QtGui.QComboBox()

        countrySelector.setMinimumSize(QtCore.QSize(160, 0))
        frequencySelector.setMinimumSize(QtCore.QSize(60, 0))

        frequencySelector.addItems(["868", "915"])

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        self.__countrySelectorLoPy = countrySelector
        self.__countrySelectorLoPy.currentIndexChanged.connect(self.__newCountrySelected)

        self.__optionalCountryWidgets.append(frequencyLabel)
        self.__optionalCountryWidgets.append(frequencySelector)
        self.__optionalCountryWidgets.append(mhzLabel)

        spin = LoadingSpin()
        self.__countrySelectorSpinLoPy = spin

        freqLayout = QtGui.QHBoxLayout()
        freqLayout.addWidget(frequencySelector)
        freqLayout.addWidget(mhzLabel)
        freqLayout.setSpacing(5)

        layout = QtGui.QGridLayout()

        layout.addWidget(countryLabel, 0, 0)
        layout.addWidget(countrySelector, 0, 1)
        layout.addWidget(spin, 0, 2)
        layout.addItem(spacerItem1, 0, 3)
        layout.addWidget(frequencyLabel, 1, 0)
        layout.addItem(freqLayout, 1, 1, 1, 2)

        page.setLayout(layout)

        page.registerField("frequency_selector", frequencySelector)

        self.__backgroundFetch.fetch_frequency_list(self.__loadLoPyCountryList, "LoPy")

        self.__setFrequencySelectorVisible(False)
        return page

    def __createRegionSelectionPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Sigfox region selection")
        page.setSubTitle("Please select your country or region:")

        countryLabel = QtGui.QLabel("Country or region:")
        countryLabel.adjustSize()

        countrySelector = QtGui.QComboBox()
        countrySelector.setMinimumSize(QtCore.QSize(160, 0))

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        self.__countrySelectorSiPy = countrySelector
        self.__countrySelectorSiPy.currentIndexChanged.connect(self.__newRegionSelected)

        spin = LoadingSpin()
        self.__countrySelectorSpinSiPy = spin

        layout = QtGui.QGridLayout()

        layout.addWidget(countryLabel, 0, 0)
        layout.addWidget(countrySelector, 0, 1)
        layout.addWidget(spin, 0, 2)
        layout.addItem(spacerItem1, 0, 3)

        page.setLayout(layout)

        self.__backgroundFetch.fetch_frequency_list(self.__loadSiPyCountryList, "SiPy")

        return page

    def __createSetupPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Setup")
        page.setSubTitle("Please follow these instructions:")

        setupLabel = QtGui.QLabel(
            "1. Turn off your device.<br>"
            "2. Connect a jumper cable between <i>G23</i> and <i>GND</i> on the expansion board.<br>"
            "3. Connect the expansion board to the computer using the USB cable.<br>"
            "<br>"
            "<b>Notes</b>: Looking at the device with the LED on the top side<br>"
            "G23 is the <i>4th</i> pin from top on the left side.<br>"
            "GND is the <i>2nd</i> pin from top on the right side."
            "<br><br>"
            "In case you don't have an expansion board available, you need to connect the device "
            "to the computer using a serial port, and also perform step 2.<br>"
        )

        setupLabel.setOpenExternalLinks(True)
        setupLabel.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(setupLabel)
        page.setLayout(layout)

        return page

    def __skipBoardPage(self):
        if self.__res_json:
            return CustomWizard.WAIT_IDX
        else:
            return CustomWizard.BOARD_IDX

    def __createSerialPage(self):
        page = CustomWizardPage(None, self.__getBoardInfo)
        page.setTitle("Communication")
        page.setSubTitle("Please select the serial port to use:")

        portLabel = QtGui.QLabel("Port:")
        portSelector = QtGui.QComboBox()

        speedSelector = QtGui.QCheckBox("High speed transfer")
        speedSelector.setChecked(True)

        self.__portSelector = portSelector
        self.__fillPortList()

        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        layout = QtGui.QGridLayout()

        layout.addWidget(portLabel, 0, 0)
        layout.addWidget(portSelector, 0, 1)
        layout.addItem(spacerItem, 0, 2)
        layout.addWidget(speedSelector, 1, 1)

        page.setLayout(layout)

        portSelector.setObjectName("port_selector")
        page.registerField("speed_selector", speedSelector)

        return page

    def __createIntroPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Welcome")

        introLabel = QtGui.QLabel("This wizard will help you upgrade your Pycom board firmware.<br><br>Both the wizard and the firmware it installs are covered by the <a href='https://www.pycom.io/opensource/licensing/'>Pycom License</a>.")
        introLabel.setWordWrap(True)
        introLabel.setOpenExternalLinks(True)

        spin = LoadingSpin()
        searchMsg = QtGui.QLabel("Fetching updates for this tool...")
        searchMsg.adjustSize()

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        layout = QtGui.QGridLayout()
        layout.setVerticalSpacing(30)
        layout.addWidget(introLabel, 0, 0, 1, 3)
        layout.addWidget(searchMsg, 1, 0)
        layout.addWidget(spin, 1, 1)
        layout.addItem(spacerItem1, 1, 2)

        page.setLayout(layout)

        self.__findNewVersionMsg = [searchMsg, spin, layout]
        self.__backgroundFetch.fetch_updater_version(self.__rx_tool_version)

        return page

    def __createGetInfoPage(self):
        page = CustomWizardPage(self.__skipBoardPage)
        page.setTitle("Getting board information...")

        waitLabel = QtGui.QLabel("Please wait, reading information about the board...")
        spin = LoadingSpin()

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        layout = QtGui.QHBoxLayout()
        layout.addWidget(waitLabel)
        layout.addWidget(spin)
        layout.addItem(spacerItem1)

        self.__getInfoItems = [waitLabel, spin]

        page.setLayout(layout)

        return page

    def __createDownloadWaitPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Downloading...")

        waitLabel = QtGui.QLabel("Please wait, firmware download in progress...")
        spin = LoadingSpin()

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        layout = QtGui.QHBoxLayout()
        layout.addWidget(waitLabel)
        layout.addWidget(spin)
        layout.addItem(spacerItem1)

        page.setLayout(layout)

        return page

    def __createWaitPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Upgrading...")

        waitLabel = QtGui.QLabel("Please be patient while the firmware is being uploaded to the board (this can take around a minute).")
        spin = LoadingSpin()

        versionString = QtGui.QLabel("")

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        layout = QtGui.QGridLayout()
        layout.setVerticalSpacing(30)
        layout.addWidget(waitLabel, 0, 0, 1, 3)
        layout.addWidget(spin, 1, 1, 1, 1, Qt.AlignCenter)
        layout.addWidget(versionString, 2, 0, 1, 2)

        page.setLayout(layout)

        waitLabel.setWordWrap(True)

        self.__firmwareVersionLabel2 = versionString

        return page

    def __createConclusionPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Result")

        label = QtGui.QLabel("")
        resultText = label
        self.__resultText = resultText
        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)

        page.setFinalPage(True)

        return page

    def __getBoardInfo(self):
        if not self.__info_requested:
            port = self.page(CustomWizard.SERIAL_IDX).findChild(QtGui.QComboBox, "port_selector").currentText()
            if self.page(CustomWizard.SERIAL_IDX).field('speed_selector').toBool():
                speed = FAST_BAUD_RATE
            else:
                speed = SLOW_BAUD_RATE

            self.__deviceInfoQuery.read_mac(port, speed, self.__read_mac_callback)
            self.__info_requested = True
        return True

    def __skipCountryIfNeeded(self):
        if self.page(CustomWizard.BOARD_IDX).field('board_selector').toInt()[0] == 1:
            return CustomWizard.DOWNLOAD_IDX
        elif self.page(CustomWizard.BOARD_IDX).field('board_selector').toInt()[0] == 0:
            return CustomWizard.COUNTRY_IDX
        else:
            return CustomWizard.REGION_IDX

    def __skipRegion(self):
        # TODO: Modify this when the FiPy is released
        return CustomWizard.DOWNLOAD_IDX

    def __wizardPageShown(self, id):
        if id == CustomWizard.SERIAL_IDX:
            self.__fillPortList()

        elif id == CustomWizard.GET_INFO_IDX:
            if not self.__info_obtained:
                wizard.button(QtGui.QWizard.NextButton).setEnabled(False)
                wizard.button(QtGui.QWizard.BackButton).setEnabled(False)

        elif id == CustomWizard.DOWNLOAD_IDX:
            if self.__board_connection_failed:
                self.next()
            else:
                wizard.button(QtGui.QWizard.NextButton).setEnabled(False)
                wizard.button(QtGui.QWizard.BackButton).setEnabled(False)

                if not self.__info_obtained:
                    if self.page(CustomWizard.BOARD_IDX).field('board_selector').toInt()[0] == 2:
                        self.__deviceInfoQuery.insert_sigfox('sipy.sipy with esp32', self.__w_mac_s,
                                                            self.__s_mac_s, self.__sigfox_zone,
                                                            self.__insert_callback)
                    elif self.page(CustomWizard.BOARD_IDX).field('board_selector').toInt()[0] == 0:
                        if self.page(CustomWizard.COUNTRY_IDX).field('frequency_selector').toInt()[0] == 0:
                            freq = 868
                        else:
                            freq = 915
                        self.__deviceInfoQuery.insert('lopy.lopy with esp32.' + str(freq), self.__w_mac_s, self.__s_mac_s, self.__insert_callback)
                    else:
                        self.__deviceInfoQuery.insert('wipy.wipy with esp32', self.__w_mac_s, self.__s_mac_s, self.__insert_callback)

        elif id == CustomWizard.WAIT_IDX:
            if self.__res_json:
                wizard.button(QtGui.QWizard.NextButton).setEnabled(False)
                wizard.button(QtGui.QWizard.BackButton).setEnabled(False)
                self.__beginBoardUpgrade()
            else:
                self.next()

        elif id == CustomWizard.RESULT_IDX:
            wizard.button(QtGui.QWizard.BackButton).setVisible(False)

        elif id == CustomWizard.BOARD_IDX or id == CustomWizard.COUNTRY_IDX or id == CustomWizard.REGION_IDX:
            if self.__board_connection_failed:
                self.next()

    def __insert_callback(self, res):
        self.__res_status = res[0]
        if self.__res_status == 200:
            self.__deviceInfoQuery.get_info(self.__w_mac_s, self.__get_info_callback)

    def __read_mac_callback(self, npy):
        if npy:
            self.__npy = npy
            w_mac = npy.read_mac()
            self.__w_mac_s = ''
            for n in w_mac:
                self.__w_mac_s += '{:02X}'.format(n)
            self.__deviceInfoQuery.get_info(self.__w_mac_s, self.__get_info_callback)
            config_block = self.__npy.read(0x3FF000, 0x1000)
            s_mac_s = "%02X%02X%02X%02X%02X%02X%02X%02X" % struct.unpack("BBBBBBBB", config_block[:8])
            if s_mac_s != "FFFFFFFFFFFFFFFF":
                self.__s_mac_s = [{"id": s_mac_s, "type": "lpwan"}]
            else:
                self.__s_mac_s = []
        else:
            self.__board_connection_failed = True
            self.__finishedUpgrade(1)

    def __get_info_callback(self, res):
        self.__res_status = res[0]

        if self.__res_status == 200:
            self.__res_json = res[1]
            self.__info_obtained = True
            self.__backgroundFetch.download_new_firmware(self.__firmwareDownloadCompleted, key=self.__res_json['firmware_type'])
            try:
                self.currentPage().jumpPage(self.DOWNLOAD_IDX)
            except AttributeError:
                pass
        else:
            wizard.button(QtGui.QWizard.NextButton).setEnabled(True)
            wizard.button(QtGui.QWizard.BackButton).setEnabled(True)
            self.currentPage().jumpPage(self.BOARD_IDX)

    def __setFrequencySelectorVisible(self, visible):
        for i in self.__optionalCountryWidgets:
            i.setVisible(visible)

    def __newBoardSelected(self, index):
        try:
            if self.page(CustomWizard.BOARD_IDX).field('board_selector').toInt()[0] == 0:
                version = self.__onlineFirmwareVersions['lopy.lopy with esp32.915']
            elif self.page(CustomWizard.BOARD_IDX).field('board_selector').toInt()[0] == 1:
                version = self.__onlineFirmwareVersions['wipy.wipy with esp32']
            else:
                version = self.__onlineFirmwareVersions['sipy.sipy with esp32']
            version = "Last available version is: " + "<b>" + version + "</b>"
        except:
            version = ""
        self.__firmwareVersionLabel1.setText(version)
        self.__firmwareVersionLabel2.setText(version)

    def __newCountrySelected(self, index):
        if index >= len(countryList):
            self.__setFrequencySelectorVisible(True)
            freq = 0
        else:
            self.__setFrequencySelectorVisible(False)

            # load frequency here
            freq = countryList[index][1]
            if freq == 868:
                freq = 0
            else:
                freq = 1

        self.page(CustomWizard.COUNTRY_IDX).setField('frequency_selector', freq)

    def __newRegionSelected(self, index):
        # load frequency here
        if index < len(regionList):
            self.__sigfox_zone = regionList[index][1]

    def __fillPortList(self):
        try:
            import serial.tools.list_ports
            self.__portSelector.clear()
            topUsb = 0
            portList = []
            for n, (portname, desc, hwid) in enumerate(sorted(serial.tools.list_ports.comports())):
                if "usb" in portname.lower():
                    portList.insert(topUsb, portname)
                    topUsb += 1
                else:
                    portList.append(portname)
            self.__portSelector.addItems(portList)
        except:
            pass

    def __beginBoardUpgrade(self):
        self.__deviceInfoQuery.update_firmware_info(self.__w_mac_s, self.__onlineFirmwareVersions[self.__res_json['firmware_type']], self.__beginBoardUpgradeCallback)

    def __beginBoardUpgradeCallback(self, res):
        if res[0] == 200:
            self.__upgradeBoard()

    def __upgradeBoard(self):
        self.__upgrade = DeviceUpgrade()
        self.__upgrade.upgrade(self.__npy, self.__firmwareScript, self.__finishedUpgrade)

    def __finishedUpgrade(self, res):
        self.__resultText.setWordWrap(True)
        if res == 0:
            config_block = base64.b64decode(self.__res_json['binary'])
            self.__npy.write(0x3FF000, config_block)
            sigfox_id = str(binascii.hexlify(config_block[8:12]).upper())
            sigfox_pac = str(binascii.hexlify(config_block[12:20]).upper())
            final_text = "Your device was successfully updated!<br><br>Please remove the wire and reset the board."
            if sigfox_id != 'FFFFFFFF':
                final_text += "<br><br><b>The Sigfox ID is</b>: " + sigfox_id
                final_text += "<br><br><b>The Sigfox PAC is</b>: " + sigfox_pac
            self.__resultText.setText(final_text)
        elif res == 1:
            new_stream.seek(0, 0)
            scriptResult = new_stream.read()
            if scriptResult:
                scriptResult = "This is the log of the upgrading process:\n\n" + scriptResult + '\nFailure!'
            if self.__upgrade or self.__board_connection_failed:
                self.__resultText.setText("The upgrade failed, please check the connections and try the steps again.\n\n" + scriptResult)
            else:
                self.__resultText.setText("""The upgrade failed because there are no more Sigfox IDs available at this moment.<br>
                                             Please getting touch with us by sending an email to support@pycom.io.""")
        self.next()

if __name__ == '__main__':
    new_stream = cStringIO.StringIO()

    old_stdout = sys.stdout
    sys.stdout = new_stream

    app = QtGui.QApplication(sys.argv)

    wizard = CustomWizard()

    wizard.setWindowTitle("Pycom Upgrade")
    wizard.show()
    wizard.raise_()
    sys.exit(wizard.exec_())
