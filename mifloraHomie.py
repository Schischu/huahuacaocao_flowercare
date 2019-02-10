import sys
import json
import paho.mqtt.client as mqtt
import time
from datetime import datetime

from miflora import Miflora, MifloraScanner

def broadcastMqtt(client, server, port, prefix, postfix, data):
  # Publishing the results to MQTT
  mqttc = mqtt.Client(client)
  mqttc.connect(server, port)

  topic = prefix + "/" + postfix

  print "MQTT Publish", topic, data
  mqttc.publish(topic, data, qos=1, retain=True)

  mqttc.loop(2)

  time.sleep(0.1)

def broadcastHomie(configuration, topic, value):
  broadcastMqtt(
    configuration["mqtt-client"], 
    configuration["mqtt-server"], 
    configuration["mqtt-port"], 
    "homie", 
    configuration["mqtt-prefix"] + "/" + topic,
    value)

def broadcastHomiePropertie(configuration, topic, name, unit, datatype, value):
  broadcastHomie(configuration, topic, value)
  broadcastHomie(configuration, topic + "/$name", name)
  broadcastHomie(configuration, topic + "/$unit", unit)
  broadcastHomie(configuration, topic + "/$datatype", datatype)

def main(argv):

  print "Starting"

  configuration = json.load(open('configuration.json'))
  if configuration.has_key("mqtt-client") is False:
    configuration["mqtt-client"] = "Miflora-Mqtt"

  if configuration.has_key("mqtt-server") is False:
    configuration["mqtt-server"] = "127.0.0.1"

  if configuration.has_key("mqtt-port") is False:
    configuration["mqtt-port"] = 1883

  if configuration.has_key("mqtt-prefix") is False:
    configuration["mqtt-prefix"] = "flower"

  print "Configuration:"
  print "MQTT Client:   ", configuration["mqtt-client"]
  print "MQTT Server:   ", configuration["mqtt-server"]
  print "MQTT Port:     ", configuration["mqtt-port"]
  print "MQTT Prefix   :", configuration["mqtt-prefix"]

  plants = []
  sensors = []
  if configuration.has_key("miflora"):
    miflora = configuration["miflora"]
    if miflora.has_key("plants"):
      plants = miflora["plants"]

    if miflora.has_key("sensors"):
      sensors = miflora["sensors"]

  print plants
  print sensors

  scanner = MifloraScanner()
  devices = scanner.discoverAll()

  nodes = ""

  for device in devices:

    deviceSensor = None
    for sensor in sensors:
      if sensor.has_key("name") and sensor["name"] == device.name:
        deviceSensor = sensor
        nodes = nodes + "," + sensor["name"][-4:].lower()

  broadcastHomie(configuration, "$homie", "3.0")
  broadcastHomie(configuration, "$state", "init")
  broadcastHomie(configuration, "$name", "Miflora")
  broadcastHomie(configuration, "$localip", "192.168.178.120")
  broadcastHomie(configuration, "$mac", "01:02:03:04:05:06")
  broadcastHomie(configuration, "$fw/name", "KleinPi01")
  broadcastHomie(configuration, "$fw/version", "1.0")
  broadcastHomie(configuration, "$implementation", "smart")
  broadcastHomie(configuration, "$stats", "")
  broadcastHomie(configuration, "$stats/interval", "60")
  broadcastHomie(configuration, "$extensions", "")

  if len(nodes) > 0:
    nodes = nodes[1:]
    broadcastHomie(configuration, "$nodes", nodes)

  for device in devices:
    print device

    deviceSensor = None
    for sensor in sensors:
      print "TEST", sensor["name"], device.name
      if sensor.has_key("name") and sensor["name"] == device.name:
        deviceSensor = sensor

    print "deviceSensor", deviceSensor

    devicePlant = None
    if deviceSensor is not None and deviceSensor.has_key("plant-name"):
      for plant in plants:
        if plant.has_key("name") and plant["name"] == deviceSensor["plant-name"]:
          devicePlant = plant

    print "devicePlant", devicePlant

    if devicePlant is not None:
      sensorId = deviceSensor["name"][-4:].lower()

      broadcastHomie(configuration, sensorId + "/$name", devicePlant["name"])
      broadcastHomie(configuration, sensorId + "/$properties", 
        "battery,air_temperature,air_temperature_status,fertilizer,fertilizer_status,light,light_status,watering,watering_status,last_utc")

      if device.connectAndSetup() is True:

        battery =  device.getBattery()
        realtimeData = device.getRealtimeData()

        if realtimeData.temperature < plant["temperature_C_threshold_lower"]:
          air_temperature_status = "air_temperature_too_low"
        elif realtimeData.temperature > plant["temperature_C_threshold_upper"]:
          air_temperature_status = "air_temperature_too_high"
        else:
          air_temperature_status = "air_temperature_good"

        if realtimeData.conductivity < plant["fertility_us_cm_threshold_lower"]:
          fertilizer_status = "fertilizer_too_low"
        elif realtimeData.conductivity > plant["fertility_us_cm_threshold_upper"]:
          fertilizer_status = "fertilizer_too_high"
        else:
          fertilizer_status = "fertilizer_good"

        if realtimeData.light < plant["light_lux_threshold_lower"]:
          light_status = "light_too_low"
        elif realtimeData.light > plant["light_lux_threshold_upper"]:
          light_status = "light_too_high"
        else:
          light_status = "light_good"

        if realtimeData.moisture < plant["moisture_threshold_lower"]:
          watering_status = "soil_moisture_too_low"
        elif realtimeData.moisture > plant["moisture_threshold_upper"]:
          watering_status = "soil_moisture_too_high"
        else:
          watering_status = "soil_moisture_good"

        broadcastHomiePropertie(configuration, sensorId + "/battery", "Battery", "%", "integer", battery)

        broadcastHomiePropertie(configuration, sensorId + "/air_temperature", "Air temperature", "C", "float", realtimeData.temperature)
        broadcastHomiePropertie(configuration, sensorId + "/air_temperature_status", "Air temperature status", "", "string", air_temperature_status)

        broadcastHomiePropertie(configuration, sensorId + "/fertilizer", "Fertilizer", "uS/cm", "integer", realtimeData.conductivity)
        broadcastHomiePropertie(configuration, sensorId + "/fertilizer_status", "Fertilizer status", "", "string", fertilizer_status)

        broadcastHomiePropertie(configuration, sensorId + "/light", "Light", "lux", "integer", realtimeData.light)
        broadcastHomiePropertie(configuration, sensorId + "/light_status", "Light status", "", "string", light_status)

        broadcastHomiePropertie(configuration, sensorId + "/watering", "Watering", "", "integer", realtimeData.moisture)
        broadcastHomiePropertie(configuration, sensorId + "/watering_status", "Watering status", "", "string", watering_status)

        now = datetime.utcnow()
        broadcastHomiePropertie(configuration, sensorId + "/last_utc", "Last update", "", "string", now.strftime("%Y-%m-%dT%H:%M:%SZ"))

  broadcastHomie(configuration, "$state", "ready")

  #broadcastHomie(configuration, "$state", "disconnected")

if __name__ == "__main__":
  main(sys.argv)