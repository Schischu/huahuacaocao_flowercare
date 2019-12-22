import sys
import json
import time
from datetime import datetime

from prometheus_client import CollectorRegistry, Gauge, Summary, Enum, push_to_gateway
from influxdb import InfluxDBClient

from miflora import Miflora, MifloraScanner

def main(argv):

  print "Starting"

  configuration = json.load(open('configuration.json'))
  if configuration.has_key("prometheuspush-client") is False:
    configuration["prometheuspush-client"] = "Miflora-Prometheus"

  if configuration.has_key("prometheuspush-server") is False:
    configuration["prometheuspush-server"] = "127.0.0.1"

  if configuration.has_key("prometheuspush-port") is False:
    configuration["prometheuspush-port"] = 9091

  if configuration.has_key("prometheuspush-prefix") is False:
    configuration["prometheuspush-prefix"] = "flower"

  if configuration.has_key("influxdb-client") is False:
    configuration["influxdb-client"] = "Miflora-Influxdb"

  if configuration.has_key("influxdb-server") is False:
    configuration["influxdb-server"] = "127.0.0.1"

  if configuration.has_key("influxdb-username") is False:
    configuration["influxdb-username"] = "influxdb"

  if configuration.has_key("influxdb-password") is False:
    configuration["influxdb-password"] = "influxdb"

  if configuration.has_key("influxdb-port") is False:
    configuration["influxdb-port"] = 8086

  if configuration.has_key("influxdb-database") is False:
    configuration["influxdb-database"] = "measurements"

  if configuration.has_key("influxdb-policy") is False:
    configuration["influxdb-policy"] = "sensor"

  if configuration.has_key("influxdb-prefix") is False:
    configuration["influxdb-prefix"] = "flower"

  print "Configuration:"
  print "Prometheus Push Client:   ", configuration["prometheuspush-client"]
  print "Prometheus Push Server:   ", configuration["prometheuspush-server"]
  print "Prometheus Push Port:     ", configuration["prometheuspush-port"]
  print "Prometheus Push Prefix   :", configuration["prometheuspush-prefix"]

  print "Influxdb Push Client:     ", configuration["influxdb-client"]
  print "Influxdb Push Username:   ", configuration["influxdb-username"]
  print "Influxdb Push Password:   ", configuration["influxdb-password"]
  print "Influxdb Push Server:     ", configuration["influxdb-server"]
  print "Influxdb Push Port:       ", configuration["influxdb-port"]
  print "Influxdb Push Database    ", configuration["influxdb-database"]
  print "Influxdb Push Policy      ", configuration["influxdb-policy"]
  print "Influxdb Push Prefix      ", configuration["influxdb-prefix"]

  plants = []
  sensors = []
  if configuration.has_key("miflora"):
    miflora = configuration["miflora"]
    if miflora.has_key("plants"):
      plants = miflora["plants"]

    if miflora.has_key("sensors"):
      sensors = miflora["sensors"]

  #print plants
  #print sensors

  scanner = MifloraScanner()
  devices = scanner.discoverAll()

  influxDbClient = InfluxDBClient(configuration["influxdb-server"], configuration["influxdb-port"], 
    configuration["influxdb-username"], configuration["influxdb-password"], configuration["influxdb-database"])

  try:
    influxDbClient.create_database(configuration["influxdb-database"])
  except InfluxDBClientError, ex:
    print "InfluxDBClientError", ex

    # Drop and create
    #client.drop_database(DBNAME)
    #client.create_database(DBNAME)

  influxDbClient.create_retention_policy(configuration["influxdb-policy"], 'INF', 3, default=True)

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

      print "devicePlant", devicePlant

      if devicePlant is not None:
        eventData = device.getEventData()
        observed = 1
        for i in range(0,10):
          if eventData is not None:
            #print "eventData", eventData
            dataToPrometheus(sensorId, eventData.battery, eventData, configuration, devicePlant, influxDbClient)
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

          dataToPrometheus(sensorId, battery, realtimeData, configuration, devicePlant, influxDbClient)

          time.sleep(0.2)

def dataToPrometheus(sensorId, battery, realtimeData, configuration, plant, influxDbClient):
  flower = {}

  flower["plant"] = ("Plant", str(plant["name"]))

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

  registry = CollectorRegistry()
  for key in flower.keys():

    if type(flower[key][1]) is str:
      if len(flower[key]) == 3:
        e = Enum(configuration["prometheuspush-prefix"]  + '_' + key + '_total',
          flower[key][0], ['sensorid'],
          states=flower[key][2],
          registry=registry)

        e.labels(sensorid=sensorId).state(flower[key][1])
    else:
      g = Gauge(configuration["prometheuspush-prefix"]  + '_' + key + '_total',
        flower[key][0], ['sensorid'],
        registry=registry)

      g.labels(sensorid=sensorId).set(flower[key][1])

    print "Pushing", sensorId, ":", configuration["prometheuspush-prefix"] + '_' + key + '_total', "=", flower[key]

  try:
    push_to_gateway(configuration["prometheuspush-server"] + ":" + configuration["prometheuspush-port"],
      job=configuration["prometheuspush-client"] + "_" + sensorId,
      registry=registry)
  except:
    print "Prometheus not available"

  influxDbJson = [
  {
    "measurement": configuration["influxdb-prefix"],
    "tags": {
        "sensor": sensorId,
    },
    "time": lastUtc[1],
    "fields": {
    }
  }]
  for key in flower.keys():
    influxDbJson[0]["fields"][key] = flower[key][1]

  print "Pushing", influxDbJson
  try:
    influxDbClient.write_points(influxDbJson, retention_policy=configuration["influxdb-policy"])
  except:
    print "Influxdb not available"

if __name__ == "__main__":
  main(sys.argv)