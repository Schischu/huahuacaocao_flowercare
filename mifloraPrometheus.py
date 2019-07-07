import sys
import json
from prometheus_client import CollectorRegistry, Gauge, Summary, Enum, push_to_gateway
import time
from datetime import datetime

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

  print "Configuration:"
  print "Prometheus Push Client:   ", configuration["prometheuspush-client"]
  print "Prometheus Push Server:   ", configuration["prometheuspush-server"]
  print "Prometheus Push Port:     ", configuration["prometheuspush-port"]
  print "Prometheus Push Prefix   :", configuration["prometheuspush-prefix"]

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
      if device.connectAndSetup() is True:

        battery =  device.getBattery()
        realtimeData = device.getRealtimeData()
        sensorId = deviceSensor["name"][-4:].lower()

        flower = {}

        #flower["plant_name"] = ("Plant", devicePlant["name"])

        flower["battery"] = ("Battery", battery)

        flower["air_temperature"] = ("Temperature", realtimeData.temperature)
        flower["air_temperature_status"] = ["Temperature Status", "good", ["good", "too_low", "too_high"]]

        if realtimeData.temperature < plant["temperature_C_threshold_lower"]:
          flower["air_temperature_status"][1] = "too_low"
        elif realtimeData.temperature > plant["temperature_C_threshold_upper"]:
          flower["air_temperature_status"][1] = "too_high"

        flower["fertilizer"] = ("Fertilizer", realtimeData.conductivity)
        flower["fertilizer_status"] = ["Fertilizer Status", "good", ["good", "too_low", "too_high"]]

        if realtimeData.conductivity < plant["fertility_us_cm_threshold_lower"]:
          flower["fertilizer_status"][1] = "too_low"
        elif realtimeData.conductivity > plant["fertility_us_cm_threshold_upper"]:
          flower["fertilizer_status"][1] = "too_high"

        flower["light"] = ("Light", realtimeData.light)
        flower["light_status"] = ["Light Status", "good", ["good", "too_low", "too_high"]]

        if realtimeData.light < plant["light_lux_threshold_lower"]:
          flower["light_status"][1] = "too_low"
        elif realtimeData.light > plant["light_lux_threshold_upper"]:
          flower["light_status"][1] = "too_high"

        flower["watering"] = ("Moisture", realtimeData.moisture)
        flower["watering_status"] = ["Moisture Status", "good", ["good", "too_low", "too_high"]]

        if realtimeData.moisture < plant["moisture_threshold_lower"]:
          flower["watering_status"][1] = "too_low"
        elif realtimeData.moisture > plant["moisture_threshold_upper"]:
          flower["watering_status"][1] = "too_high"

        #now = datetime.utcnow()
        #flower["last_utc"] = ("Updated", now.strftime("%Y-%m-%dT%H:%M:%SZ")) #2017-11-13T17:44:11Z

        registry = CollectorRegistry()
        for key in flower.keys():

          if type(flower[key][1]) is str:
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

        push_to_gateway(configuration["prometheuspush-server"] + ":" + configuration["prometheuspush-port"], 
          job=configuration["prometheuspush-client"] + "_" + sensorId, 
          registry=registry)

        time.sleep(1)

if __name__ == "__main__":
  main(sys.argv)