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
  mqttc.publish(topic, data)

  mqttc.loop(2)

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
      flower = {}
      flower["plant_name"]  = devicePlant["name"]
      flower["sensor_name"] = deviceSensor["name"]
      sensorId = flower["sensor_name"][-4:].lower()

      broadcastMqtt(
        configuration["mqtt-client"], 
        configuration["mqtt-server"], 
        configuration["mqtt-port"], 
        configuration["mqtt-prefix"], 
        sensorId + "/name",
        json.dumps(flower))

      time.sleep(1)

      if device.connectAndSetup() is True:

        battery =  device.getBattery()
        realtimeData = device.getRealtimeData()

        flower = {}
        flower["sensor_name"] = deviceSensor["name"]
        sensorId = flower["sensor_name"][-4:].lower()

        if battery >= 0:
          flower["battery"] = battery

        if realtimeData.temperature >= 0:
          flower["air_temperature"] = realtimeData.temperature
          if realtimeData.temperature < plant["temperature_C_threshold_lower"]:
            flower["air_temperature_status"] = "air_temperature_too_low"
          elif realtimeData.temperature > plant["temperature_C_threshold_upper"]:
            flower["air_temperature_status"] = "air_temperature_too_high"
          else:
            flower["air_temperature_status"] = "air_temperature_good"

        if realtimeData.conductivity >= 0:
          flower["fertilizer"] = realtimeData.conductivity
          if realtimeData.conductivity < plant["fertility_us_cm_threshold_lower"]:
            flower["fertilizer_status"] = "fertilizer_too_low"
          elif realtimeData.conductivity > plant["fertility_us_cm_threshold_upper"]:
            flower["fertilizer_status"] = "fertilizer_too_high"
          else:
            flower["fertilizer_status"] = "fertilizer_good"

        if realtimeData.light >= 0:
          flower["light"] = realtimeData.light
          if realtimeData.light < plant["light_lux_threshold_lower"]:
            flower["light_status"] = "light_too_low"
          elif realtimeData.light > plant["light_lux_threshold_upper"]:
            flower["light_status"] = "light_too_high"
          else:
            flower["light_status"] = "light_good"

        if realtimeData.moisture >= 0:
          flower["watering"] = realtimeData.moisture
          if realtimeData.moisture < plant["moisture_threshold_lower"]:
            flower["watering_status"] = "soil_moisture_too_low"
          elif realtimeData.moisture > plant["moisture_threshold_upper"]:
            flower["watering_status"] = "soil_moisture_too_high"
          else:
            flower["watering_status"] = "soil_moisture_good"

        now = datetime.utcnow()
        flower["last_utc"] = now.strftime("%Y-%m-%dT%H:%M:%SZ") #2017-11-13T17:44:11Z

        broadcastMqtt(
          configuration["mqtt-client"], 
          configuration["mqtt-server"], 
          configuration["mqtt-port"], 
          configuration["mqtt-prefix"], 
          sensorId + "/update",
          json.dumps(flower))

        time.sleep(1)

if __name__ == "__main__":
  main(sys.argv)