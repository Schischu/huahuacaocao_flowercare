import binascii
import struct
import time
import math
import os
import sys

from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate, BTLEException

#handle = 0x0002, char properties = 0x02, char value handle = 0x0003, uuid = 00002a00-0000-1000-8000-00805f9b34fb
#handle = 0x0004, char properties = 0x02, char value handle = 0x0005, uuid = 00002a01-0000-1000-8000-00805f9b34fb
#handle = 0x0006, char properties = 0x0a, char value handle = 0x0007, uuid = 00002a02-0000-1000-8000-00805f9b34fb
#handle = 0x0008, char properties = 0x02, char value handle = 0x0009, uuid = 00002a04-0000-1000-8000-00805f9b34fb
#handle = 0x000d, char properties = 0x22, char value handle = 0x000e, uuid = 00002a05-0000-1000-8000-00805f9b34fb
#handle = 0x0011, char properties = 0x1a, char value handle = 0x0012, uuid = 00000001-0000-1000-8000-00805f9b34fb
#handle = 0x0014, char properties = 0x02, char value handle = 0x0015, uuid = 00000002-0000-1000-8000-00805f9b34fb
#handle = 0x0016, char properties = 0x12, char value handle = 0x0017, uuid = 00000004-0000-1000-8000-00805f9b34fb
#handle = 0x0018, char properties = 0x08, char value handle = 0x0019, uuid = 00000007-0000-1000-8000-00805f9b34fb
#handle = 0x001a, char properties = 0x08, char value handle = 0x001b, uuid = 00000010-0000-1000-8000-00805f9b34fb
#handle = 0x001c, char properties = 0x0a, char value handle = 0x001d, uuid = 00000013-0000-1000-8000-00805f9b34fb
#handle = 0x001e, char properties = 0x02, char value handle = 0x001f, uuid = 00000014-0000-1000-8000-00805f9b34fb
#handle = 0x0020, char properties = 0x10, char value handle = 0x0021, uuid = 00001001-0000-1000-8000-00805f9b34fb
#handle = 0x0024, char properties = 0x0a, char value handle = 0x0025, uuid = 8082caa8-41a6-4021-91c6-56f9b954cc34
#handle = 0x0026, char properties = 0x0a, char value handle = 0x0027, uuid = 724249f0-5ec3-4b5f-8804-42345af08651
#handle = 0x0028, char properties = 0x02, char value handle = 0x0029, uuid = 6c53db25-47a1-45fe-a022-7c92fb334fd4
#handle = 0x002a, char properties = 0x0a, char value handle = 0x002b, uuid = 9d84b9a3-000c-49d8-9183-855b673fda31
#handle = 0x002c, char properties = 0x0e, char value handle = 0x002d, uuid = 457871e8-d516-4ca1-9116-57d0b17b9cb2
#handle = 0x002e, char properties = 0x12, char value handle = 0x002f, uuid = 5f78df94-798c-46f5-990a-b3eb6a065c88
#handle = 0x0032, char properties = 0x0a, char value handle = 0x0033, uuid = 00001a00-0000-1000-8000-00805f9b34fb
#handle = 0x0034, char properties = 0x1a, char value handle = 0x0035, uuid = 00001a01-0000-1000-8000-00805f9b34fb
#handle = 0x0037, char properties = 0x02, char value handle = 0x0038, uuid = 00001a02-0000-1000-8000-00805f9b34fb
#handle = 0x003b, char properties = 0x02, char value handle = 0x003c, uuid = 00001a11-0000-1000-8000-00805f9b34fb
#handle = 0x003d, char properties = 0x1a, char value handle = 0x003e, uuid = 00001a10-0000-1000-8000-00805f9b34fb
#handle = 0x0040, char properties = 0x02, char value handle = 0x0041, uuid = 00001a12-0000-1000-8000-00805f9b34fb

GAP_DEVICE_NAME_UUID                                = UUID(0x2A00)
GAP_APPEARANCE_UUID                                 = UUID(0x2A01)
GAP_PERIPHERAL_PRIVACY_FLAG_UUID                    = UUID(0x2A02)
GAP_PERIPHERAL_PREFERRED_CONNECTION_PARAMETERS_UUID = UUID(0x2A04)
GATT_SERVICE_CHANGED_UUID                           = UUID(0x2A05)

DEVICE_VERSION_UUID          = UUID('00002a2600001000800000805f9b34fb')

DATA_WRITE_MODE_CHANGE_UUID  = UUID('00001a0000001000800000805f9b34fb')
DATA_DATA_UUID               = UUID('00001a0100001000800000805f9b34fb')
DATA_BATTERY_VERSION_UUID    = UUID('00001a0200001000800000805f9b34fb')

HISTORY_NOTIFY_UUID          = UUID('00001a1000001000800000805f9b34fb')
HISTORY_READ_DATA_BLOCK_UUID = UUID('00001a1100001000800000805f9b34fb')
HISTORY_READ_RTC_UUID        = UUID('00001a1200001000800000805f9b34fb')

OAD_SEND_SIGNAL_UUID         = UUID('8082caa841a6402191c656f9b954cc34')
OAD_SET_GPIO_MAP_UUID        = UUID('724249f05eC34b5f880442345af08651')
OAD_UNKNOWN_J_UUID           = UUID('6c53db2547a145fea0227c92fb334fd4')
OAD_SET_PATCH_LENGTH_UUID    = UUID('9d84b9a3000c49d89183855b673fda31')
OAD_SEND_BLOCK_UUID          = UUID('457871e8d5164ca1911657d0b17b9cb2')
OAD_NOTIFY_UUID              = UUID('5f78df94798c46f5990ab3eb6a065c88')

#attr handle = 0x0001, end grp handle = 0x0009 uuid: 00001800-0000-1000-8000-00805f9b34fb
#attr handle = 0x000c, end grp handle = 0x000f uuid: 00001801-0000-1000-8000-00805f9b34fb
#attr handle = 0x0010, end grp handle = 0x0022 uuid: 0000fe95-0000-1000-8000-00805f9b34fb
#attr handle = 0x0023, end grp handle = 0x0030 uuid: 0000fef5-0000-1000-8000-00805f9b34fb
#attr handle = 0x0031, end grp handle = 0x0039 uuid: 00001204-0000-1000-8000-00805f9b34fb
#attr handle = 0x003a, end grp handle = 0x0042 uuid: 00001206-0000-1000-8000-00805f9b34fb


GENERIC_ACCESS_SERVICE_UUID                        = UUID(0x1800)
GENERIC_ATTRIBUTE_SERVICE_UUID                     = UUID(0x1801)

UNKNOWN_A_SERVICE_UUID = UUID('f000ffc004514000b000000000000000')
UNKNOWN_B_SERVICE_UUID = UUID('f000ccc004514000b000000000000000')
HISTORY_SERVICE_UUID   = UUID('0000120600001000800000805f9b34fb')
DATA_SERVICE_UUID      = UUID('0000120400001000800000805f9b34fb')
UNKNOWN_E_SERVICE_UUID = UUID('0000120500001000800000805f9b34fb')
DEVICE_SERVICE_UUID    = UUID('0000180a00001000800000805f9b34fb')
OAD_SERVICE_UUID       = UUID('0000fef500001000800000805f9b34fb')

UNKNOWN_H_SERVICE_UUID = UUID('0000fe9500001000800000805f9b34fb')

SCAN_UUIDS = [UNKNOWN_H_SERVICE_UUID]

DEFAULT_DEVICE_NAME = 'Flower care'

STRUCT_UInt8LE = 'B'
STRUCT_UInt16LE = 'H'
STRUCT_UInt32LE = 'I'
STRUCT_Float = 'f'
STRUCT_Bytes = 'B'
STRUCT_String = 's'

class DeviceInformation:
  localName = ""
  flags = 0
  adData = ""
  addr = ""
  rssi = 0.0
  uuid = None
  id = ""

class MifloraScanner:

  def __init__(self):
    self.scanner = Scanner()

  def _discover(self, duration=1, filter=None):
    devices = self.scanner.scan(duration)
    if devices is None:
      return None

    mifloraDevices = []
    for device in devices:
      #print device.getScanData()

      manufactureId = "{}{}{}".format(device.addr[0:2], device.addr[3:5], device.addr[6:8]).upper()
      uniqueId = "{}{}".format(device.addr[-5:-3], device.addr[-2:]).upper()

      if filter is not None:
        if uniqueId.upper() != filter.upper():
          continue

      deviceInformation = DeviceInformation()
      deviceInformation.localName    = device.getValueText(0x09) #Local Name

      flags        = device.getValueText(0x01) #Flags
      if flags is not None:
        deviceInformation.flags        = int(flags, 16)

      deviceInformation.adData = device.getValueText(0x16) # Service Data - 16-bit UUID

      deviceInformation.addr         = device.addr
      deviceInformation.rssi         = device.rssi

      uuid = device.getValueText(0x02) #Incomplete 128b Services
      if uuid is not None:
        uuid = "".join(reversed([uuid[i:i+2] for i in range(0, len(uuid), 2)]))
        deviceInformation.uuid       = UUID(uuid)

      if deviceInformation.localName == "Flower care" or manufactureId == "C47C8D":
        deviceInformation.id = uniqueId.upper()
        deviceInformation.localName = "Flower care {}".format(deviceInformation.id)

      if deviceInformation.uuid is not None:
        if deviceInformation.uuid in SCAN_UUIDS:
          print "-"*60
          print "deviceInformation.flags:", deviceInformation.flags
          print "deviceInformation.addr:", deviceInformation.addr
          print "deviceInformation.rssi:", deviceInformation.rssi
          print "deviceInformation.id:", deviceInformation.id
          print "deviceInformation.localName:", deviceInformation.localName
          print "deviceInformation.adData:", deviceInformation.adData
          print "deviceInformation.uuid:", deviceInformation.uuid

          flower = Miflora(deviceInformation)

          print "Found Flower:", flower
          mifloraDevices.append(flower)

    if len(mifloraDevices) == 0:
      mifloraDevices = None

    return mifloraDevices

  def discover(self, filter):
    devices = self._discover(1, filter)
    if devices is None:
      return None

    return devices

  def discoverAll(self):
    devices = self._discover(10)
    if devices is None:
      return None

    return devices

class Miflora:
  def __init__(self, deviceInformation):
    self._deviceInformation = deviceInformation
    self.name = deviceInformation.localName
    self.id = deviceInformation.id


  def connectAndSetup(self):
    print "Connecting to", self._deviceInformation.addr
    for i in range(0,10):
      try:
        ADDR_TYPE_PUBLIC = "public"
        self.peripheral = Peripheral(self._deviceInformation.addr, ADDR_TYPE_PUBLIC)
        return True
      except BTLEException, ex:
        if i == 10:
          print "BTLE Exception", ex
        continue

    return False

  def __str__(self):
    str = '{{name: "{}" addr: "{}"}}'.format(self.name, self._deviceInformation.addr)
    return str

################

  def readCharacteristic(self, serviceUuid, characteristicUuid):
    try:
      ch = self.peripheral.getCharacteristics(uuid=characteristicUuid)[0]
      if (ch.supportsRead()):
        val = ch.read()
        return val
    except BTLEException, ex:
      print "BTLE Exception", ex

    print "Error on readCharacteristic"
    return None

  def readDataCharacteristic(self, serviceUuid, characteristicUuid):
    try:
      ch = self.peripheral.getCharacteristics(uuid=characteristicUuid)[0]
      if (ch.supportsRead()):
        val = ch.read()
        val = binascii.b2a_hex(val)
        val = binascii.unhexlify(val)
        return val
    except BTLEException, ex:
      print "BTLE Exception", ex

    print "Error on readDataCharacteristic"
    return None

  class NotifyDelegate(DefaultDelegate):
    def __init__(self, miflora):
      DefaultDelegate.__init__(self)
      self.miflora = miflora

    def handleNotification(self, cHandle, data):
      print "handleNotification", cHandle, data
      if cHandle == 33:
        self.miflora.onRealtimeData(data)

  def notifyCharacteristic(self, serviceUuid, characteristicUuid, enable):

    service = self.peripheral.getServiceByUUID(serviceUuid)
    char = service.getCharacteristics(forUUID=characteristicUuid)[0]
    charDescr = service.getDescriptors(forUUID=characteristicUuid)[0]
    charHandle = char.getHandle()

    if enable:
      notifyDelegate = Miflora.NotifyDelegate(self)
      self.peripheral.withDelegate(notifyDelegate)

      charDescr.write(struct.pack('<BB', 0xA0, 0x1F), True)
    else:
      charDescr.write(struct.pack('<BB', 0xC0, 0x1F), True)

      self.peripheral.withDelegate(None)

    return charHandle


################

  def getBattery(self):
    data = self.readDataCharacteristic(DATA_SERVICE_UUID, DATA_BATTERY_VERSION_UUID)
    if data is None:
      return 0

    batteryLevel = ord(data[0])

    return batteryLevel

  def getDeviceFirmwareVersion(self):
    return None

  class RealtimeData:
    temperature = 0
    unknown = 0
    light = 0
    moisture = 0
    conductivity = 0

    def __init__(self):
      self.temperature = 0
      self.unknown = 0
      self.light = 0
      self.moisture = 0
      self.conductivity = 0

    def __str__(self):
      str = '{{moisture: "{}" conductivity: "{}" light: "{}" temperature: "{}" unknown: "{}"}}'.format(self.moisture, self.conductivity, self.light, self.temperature, self.unknown)
      return str

  def getRealtimeData(self):
    self.notifyCharacteristic(DATA_SERVICE_UUID, DATA_WRITE_MODE_CHANGE_UUID, True)

    self.waitingForData = True
    while self.waitingForData:
      notified = self.peripheral.waitForNotifications(10)
      if notified:
        pass

    data = self.readDataCharacteristic(DATA_SERVICE_UUID, DATA_DATA_UUID)

    #print "DATA", " ".join("{:02x}".format(ord(c)) for c in data)

    #09 01 
    #00 
    #fa 00 00 
    #00 
    #00 
    #00 00 
    #02 3c 00 fb 34 9b

    #f3 00 
    #00 
    #23 00 00 
    #00 
    #0d 
    #30 00 
    #02 3c 00 fb 34 9b


    realtimeData = Miflora.RealtimeData()
    realtimeData.temperature = (struct.unpack(STRUCT_UInt16LE, data[0:2])[0]) / 10.0
    realtimeData.unknown     = struct.unpack(STRUCT_UInt8LE, data[2:3])[0]
    realtimeData.light       = struct.unpack(STRUCT_UInt32LE, data[3:6] + "\0")[0]
    realtimeData.moisture     = struct.unpack(STRUCT_UInt8LE, data[7:8])[0]
    realtimeData.conductivity = struct.unpack(STRUCT_UInt16LE, data[8:10])[0]

    realtimeData.light = (realtimeData.light * 1.0) / 1000.0

    self.notifyCharacteristic(DATA_SERVICE_UUID, DATA_WRITE_MODE_CHANGE_UUID, False)

    return realtimeData

  def onRealtimeData(self, data):
    self.waitingForData = False


def main(argv):
  deviceFilter = None

  print "Starting"

  if len(argv) > 1:
    deviceFilter = argv[1]

  scanner = MifloraScanner()
  if deviceFilter is not None:
    devices = scanner.discover(deviceFilter)
  else:
    devices = scanner.discoverAll()



  for device in devices:
    print device

    if device.connectAndSetup() is True:
      #print "Battery        ", device.getBattery(), "%"
      print "RealtimeData", device.getRealtimeData()

if __name__ == "__main__":
  main(sys.argv)