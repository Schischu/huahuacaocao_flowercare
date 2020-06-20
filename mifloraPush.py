import sys
import json
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from prometheus_client import CollectorRegistry, Gauge, Summary, Enum, push_to_gateway
from influxdb import InfluxDBClient

from miflora import Miflora, MifloraScanner

def broadcastMqtt(client, server, port, prefix, postfix, data):
  # Publishing the results to MQTT
  mqttc = mqtt.Client(client)
  mqttc.connect(server, port)

  topic = prefix + "/" + postfix

  #print "MQTT Publish", topic, data
  mqttc.publish(topic, data)

  mqttc.loop(2)

def main(argv):

  print "Starting"

  configuration = json.load(open('configuration.json'))

  if configuration.has_key("mqtt"):
    try:
      if configuration["mqtt"].has_key("client") is False:
        configuration["mqtt"]["client"] = "Ruuvi-Mqtt"

      if configuration["mqtt"].has_key("server") is False:
        configuration["mqtt"]["server"] = "127.0.0.1"

      if configuration["mqtt"].has_key("port") is False:
        configuration["mqtt"]["port"] = 1883

      if configuration["mqtt"].has_key("prefix") is False:
        configuration["mqtt"]["prefix"] = "weather"

      if configuration["mqtt"].has_key("enabled") is False:
        configuration["mqtt"]["enabled"] = True

      print "MQTT Configuration:"
      print "MQTT Client:   ", configuration["mqtt"]["client"]
      print "MQTT Server:   ", configuration["mqtt"]["server"]
      print "MQTT Port:     ", configuration["mqtt"]["port"]
      print "MQTT Prefix:   ", configuration["mqtt"]["prefix"]
      print "MQTT Enabled:  ", configuration["mqtt"]["enabled"]

    except Exception, ex:
      print "Error parsing mqtt configuration", ex
      configuration["mqtt"]["enabled"] = False
  else:
    configuration["mqtt"] = {}
    configuration["mqtt"]["enabled"] = False

  if configuration.has_key("prometheuspush"):
    try:
      if configuration["prometheuspush"].has_key("server") is False:
        configuration["prometheuspush"]["server"] = "127.0.0.1"

      if configuration["prometheuspush"].has_key("port") is False:
        configuration["prometheuspush"]["port"] = 9091

      if configuration["prometheuspush"].has_key("client") is False:
        configuration["prometheuspush"]["client"] = "Ruuvi-Prometheus"

      if configuration["prometheuspush"].has_key("prefix") is False:
        configuration["prometheuspush"]["prefix"] = "weather"

      if configuration["prometheuspush"].has_key("enabled") is False:
        configuration["prometheuspush"]["enabled"] = True

      print "Prometheus Push Configuration:"
      print "Prometheus Push Client:   ", configuration["prometheuspush"]["client"]
      print "Prometheus Push Server:   ", configuration["prometheuspush"]["server"]
      print "Prometheus Push Port:     ", configuration["prometheuspush"]["port"]
      print "Prometheus Push Prefix:   ", configuration["prometheuspush"]["prefix"]
      print "Prometheus Push Enabled:  ", configuration["prometheuspush"]["enabled"]

    except Exception, ex:
      print "Error parsing prometheuspush configuration", ex
      configuration["prometheuspush"]["enabled"] = False
  else:
    configuration["prometheuspush"] = {}
    configuration["prometheuspush"]["enabled"] = False

  if configuration.has_key("influxdb"):
    try:
      if configuration["influxdb"].has_key("client") is False:
        configuration["influxdb"]["client"] = "Ruuvi-Influxdb"

      if configuration["influxdb"].has_key("server") is False:
        configuration["influxdb"]["server"] = "127.0.0.1"

      if configuration["influxdb"].has_key("username") is False:
        configuration["influxdb"]["username"] = "influxdb"

      if configuration["influxdb"].has_key("password") is False:
        configuration["influxdb"]["password"] = "influxdb"

      if configuration["influxdb"].has_key("port") is False:
        configuration["influxdb"]["port"] = 8086

      if configuration["influxdb"].has_key("database") is False:
        configuration["influxdb"]["database"] = "measurements"

      if configuration["influxdb"].has_key("policy") is False:
        configuration["influxdb"]["policy"] = "sensor"

      if configuration["influxdb"].has_key("prefix") is False:
        configuration["influxdb"]["prefix"] = "weather"

      if configuration["influxdb"].has_key("enabled") is False:
        configuration["influxdb"]["enabled"] = True

      print "Influxdb Configuration:"
      print "Influxdb Client:     ", configuration["influxdb"]["client"]
      print "Influxdb Username:   ", configuration["influxdb"]["username"]
      print "Influxdb Password:   ", configuration["influxdb"]["password"]
      print "Influxdb Server:     ", configuration["influxdb"]["server"]
      print "Influxdb Port:       ", configuration["influxdb"]["port"]
      print "Influxdb Database:   ", configuration["influxdb"]["database"]
      print "Influxdb Policy:     ", configuration["influxdb"]["policy"]
      print "Influxdb Prefix:     ", configuration["influxdb"]["prefix"]
      print "Influxdb Enabled:    ", configuration["influxdb"]["enabled"]

    except Exception, ex:
      print "Error parsing influxdb configuration", ex
      configuration["influxdb"]["enabled"] = False
  else:
    configuration["influxdb"] = {}
    configuration["influxdb"]["enabled"] = False

  plants = []
  sensors = []
  if configuration.has_key("miflora"):
    miflora = configuration["miflora"]
    if miflora.has_key("plants"):
      plants = miflora["plants"]

    if miflora.has_key("sensors"):
      sensors = miflora["sensors"]

  scanner = MifloraScanner()
  devices = scanner.discoverAll()

  if configuration["influxdb"]["enabled"]:
    influxDbClient = InfluxDBClient(configuration["influxdb"]["server"], configuration["influxdb"]["port"], 
      configuration["influxdb"]["username"], configuration["influxdb"]["password"], configuration["influxdb"]["database"])

    try:
      influxDbClient.create_database(configuration["influxdb"]["database"])
    except InfluxDBClientError, ex:
      print "InfluxDBClientError", ex

    influxDbClient.create_retention_policy(configuration["influxdb"]["policy"], 'INF', 3, default=True)

  if devices is not None:
    for device in devices:
      print device

      deviceSensor = None
      for sensor in sensors:
        if sensor.has_key("name") and sensor["name"] == device.name:
          deviceSensor = sensor

      print "deviceSensor", deviceSensor
      sensorId = str(deviceSensor["name"][-4:].lower())
      plantName = deviceSensor["plant-name"]

      devicePlant = None
      if deviceSensor is not None and deviceSensor.has_key("plant-name"):
        for plant in plants:
          if plant.has_key("name") and plant["name"] == deviceSensor["plant-name"]:
            devicePlant = plant

            if deviceSensor.has_key("location"):
              devicePlant["location"] = deviceSensor["location"]

      print "devicePlant", devicePlant

      if devicePlant is not None:
        eventData = device.getEventData()
        observed = 1
        for i in range(0,10):
          if eventData is not None:
            #print "eventData", eventData
            pushData(sensorId, eventData.battery, eventData, configuration, devicePlant, influxDbClient)
            eventData = None
            observed = observed + 1

          tmpDevices = scanner.discover(sensorId.upper())
          if tmpDevices is not None:
            tmpDevice = tmpDevices[0]
            eventData = tmpDevice.getEventData()
            time.sleep(3) #Broadcast happens every 1sec, however value doesnt change that often

          time.sleep(0.2) #Broadcast happens every 1sec, however value doesnt change that often


        # Makes only sense to connect if we observed at least 5 adv packages (bad signal)
        if observed > 5 and device.connectAndSetup() is True:

          battery =  device.getBattery()
          realtimeData = device.getRealtimeData()

          pushData(sensorId, battery, realtimeData, configuration, devicePlant, influxDbClient)

          time.sleep(0.2)

def pushData(sensorId, battery, realtimeData, configuration, plant, influxDbClient):
  flower = {}

  flower["plant"] = ("Plant", str(plant["name"]))
  flower["location"] = ("Location", str(plant["location"]))

  if battery is not None:
    flower["battery"] = ("Battery", battery)

  if realtimeData.battery is not None:
    flower["battery"] = ("Battery", int(realtimeData.battery))

  if realtimeData.temperature is not None:
    flower["air_temperature"] = ("Temperature", float(realtimeData.temperature))
    flower["air_temperature_status"] = ["Temperature Status", "good", ["good", "too_low", "too_high"]]

    if realtimeData.temperature < plant["temperature_C_threshold_lower"]:
      flower["air_temperature_status"][1] = "too_low"
    elif realtimeData.temperature > plant["temperature_C_threshold_upper"]:
      flower["air_temperature_status"][1] = "too_high"

  if realtimeData.conductivity is not None:
    flower["fertilizer"] = ("Fertilizer", float(realtimeData.conductivity))
    flower["fertilizer_status"] = ["Fertilizer Status", "good", ["good", "too_low", "too_high"]]

    if realtimeData.conductivity < plant["fertility_us_cm_threshold_lower"]:
      flower["fertilizer_status"][1] = "too_low"
    elif realtimeData.conductivity > plant["fertility_us_cm_threshold_upper"]:
      flower["fertilizer_status"][1] = "too_high"

  if realtimeData.light is not None:
    flower["light"] = ("Light", float(realtimeData.light))
    flower["light_status"] = ["Light Status", "good", ["good", "too_low", "too_high"]]

    if realtimeData.light < plant["light_lux_threshold_lower"]:
      flower["light_status"][1] = "too_low"
    elif realtimeData.light > plant["light_lux_threshold_upper"]:
      flower["light_status"][1] = "too_high"

  if realtimeData.moisture is not None:
    flower["watering"] = ("Moisture", float(realtimeData.moisture))
    flower["watering_status"] = ["Moisture Status", "good", ["good", "too_low", "too_high"]]

    if realtimeData.moisture < plant["moisture_threshold_lower"]:
      flower["watering_status"][1] = "too_low"
    elif realtimeData.moisture > plant["moisture_threshold_upper"]:
      flower["watering_status"][1] = "too_high"

  now = datetime.utcnow()
  lastUtc = ("Updated", now.strftime("%Y-%m-%dT%H:%M:%SZ")) #2017-11-13T17:44:11Z

  if configuration["mqtt"]["enabled"]:
    print "Pushing Mqtt", sensorId, ":", configuration["mqtt"]["prefix"], flower
    try:
      broadcastMqtt(
        configuration["mqtt"]["client"], 
        configuration["mqtt"]["server"], 
        configuration["mqtt"]["port"], 
        configuration["mqtt"]["prefix"], 
        sensorId + "/update",
        json.dumps(flower))
    except Exception, ex:
      print "Error on mqtt broadcast", ex

  if configuration["prometheuspush"]["enabled"]:
    registry = CollectorRegistry()
    for key in flower.keys():

      if type(flower[key][1]) is str:
        if len(flower[key]) == 3:
          e = Enum(configuration["prometheuspush"]["prefix"]  + '_' + key + '_total',
            flower[key][0], ['sensorid'],
            states=flower[key][2],
            registry=registry)

          e.labels(sensorid=sensorId).state(flower[key][1])
      else:
        g = Gauge(configuration["prometheuspush"]["prefix"]  + '_' + key + '_total',
          flower[key][0], ['sensorid'],
          registry=registry)

        g.labels(sensorid=sensorId).set(flower[key][1])

    print "Pushing Prometheus", sensorId, ":", configuration["prometheuspush"]["prefix"] + '_' + key + '_total', "=", flower[key]
    try:
      push_to_gateway(configuration["prometheuspush"]["server"] + ":" + configuration["prometheuspush"]["port"],
        job=configuration["prometheuspush"]["client"] + "_" + sensorId,
        registry=registry)
    except Exception, ex:
      print "Error on prometheus push", ex

  if configuration["influxdb"]["enabled"]:
    influxDbJson = [
    {
      "measurement": configuration["influxdb"]["prefix"],
      "tags": {
          "sensor": sensorId,
      },
      "time": lastUtc[1],
      "fields": {
      }
    }]
    for key in flower.keys():
      influxDbJson[0]["fields"][key] = flower[key][1]

    print "Pushing InfluxDb", influxDbJson
    try:
      influxDbClient.write_points(influxDbJson, retention_policy=configuration["influxdb"]["policy"])
    except Exception, ex:
      print "Error on influxdb write_points", ex

if __name__ == "__main__":
  main(sys.argv)