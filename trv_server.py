#!/usr/bin/env python3

import eq3bt
import bluepy
import paho.mqtt.client as mqtt
import json
import logging
import requests


trv_lookup = {
"00:1A:22:0C:27:A9" : "Front_door",
"00:1A:22:0C:28:9B" : "Old_Dining_Rm",
"00:1A:22:0C:2A:8E" : "Ted",
"00:1A:22:0C:2A:A3" : "Lounge",
"00:1A:22:0C:2C:03" : "Den",
"00:1A:22:0C:2C:B5" : "Master_Bed",
"00:1A:22:0C:2C:C8" : "Matty",
"00:1A:22:0C:28:B3" : "Dining_Rm",
"00:1A:22:0C:2C:BB" : "Sam",
"00:1A:22:0D:A3:6B" : "Study"
}

remote_workers = ["pi-btle-relay-2", "thermopi"]

#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)

def send_mqtt(topic,trv_obj):
    message = json.dumps(trv_obj)
    logging.debug("Sending MQTT message...")
    logging.debug(json.dumps(trv_obj, indent=4, sort_keys=True))
    try:
        mqttc.connect("calculon.whizzy.org", 1883)
    except:
        print("Couldnt connect to MQTT server?  WHY?!")
    mqttc.publish(topic,message)
    mqttc.loop(2)
    mqttc.disconnect()


def read_device(mac):
    logging.debug("Trying to read from TRV...")
    thermo = eq3bt.Thermostat(mac)
    obj = False
    try:
        thermo.update()
        obj = {
            "mac": mac,
            "valve" : thermo.valve_state,
            "target_temperature" : thermo.target_temperature,
            "low_battery" : thermo.low_battery,
            "locked" : thermo.locked
        }
    except bluepy.btle.BTLEDisconnectError:
        logging.error("Failed to talk to device.")
    return obj


mqttc = mqtt.Client("trv_server")
mqttc.connect("calculon.whizzy.org", 1883)
logging.info("Connected to MQTT broker")

good_list = []
naughty_list = []
for mac in trv_lookup.keys():
    human_name = trv_lookup[mac]
    print("Starting read for MAC: "+mac+".  Name: "+human_name)
    trv = read_device(mac)
    if trv is not False:
        send_mqtt("trv/"+human_name, trv)
        good_list.append(human_name)
        #time.sleep(0.5)
    elif trv is False:
        # Reading of data failed, so send it to the proxies
        logging.info("Local connection failed, trying remote for: "+human_name)
        for each in remote_workers:
            logging.debug("Trying remote worker: "+each)
            message = {"MAC":mac}
            try:
                r = requests.post("http://"+each+":8080/read_device", json=message)
                if r.status_code == 200:
                    logging.info("Got successful reply from remote worker for "+human_name)
                    send_mqtt("trv/"+human_name, r.json())
                    good_list.append(human_name)
                    break
                else:
                    logging.info("Didn't get a good reply for "+human_name)
            except:
                logging.info("Failed to connect to remote worker: "+each)
    if human_name not in good_list:
        naughty_list.append(human_name)
        logging.info("Failed to read device: "+human_name)
logging.info("Good list:")
for each in good_list:
    logging.info("    "+each)
logging.info("Naughty list:")
for each in naughty_list:
    logging.info("    "+each)

