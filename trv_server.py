
from eq3bt import Thermostat
import bluepy
import paho.mqtt.client as mqtt
import json
import logging
import time

trv_lookup = {
"00:1A:22:0C:27:A9" : "Front_door",
"00:1A:22:0C:28:9B" : "Old_Dining_Rm",
"00:1A:22:0C:28:B3" : "Dining_Rm",
"00:1A:22:0C:2A:8E" : "Ted",
"00:1A:22:0C:2A:A3" : "Lounge",
"00:1A:22:0C:2C:B5" : "Master_Bed",
"00:1A:22:0C:2C:BB" : "Sam",
"00:1A:22:0C:2C:C8" : "Matty",
"00:1A:22:0D:A3:6B" : "Study"

}

#logging.basicConfig(level=logging.DEBUG)

def send_mqtt(topic,message):
	mqttc.reconnect()
	mqttc.publish(topic,message)
	mqttc.loop(2)
	mqttc.disconnect()


mqttc = mqtt.Client("python_pub")
mqttc.connect("calculon.whizzy.org", 1883)
print("Connected to MQTT broker")


with open('/home/pi/trv_control/trvs_in_range.txt') as fp:
    trvs = fp.readlines()

for each in trvs:
    each.strip()
    if each[0] == "#":
        print("Skipping "+each)
        continue
    mac = each.split(' ')[0]
    thermo = Thermostat(mac)
    try:
        human_name = trv_lookup[mac]
    except:
        human_name = "Unknown"
    try:
        thermo.update()
        thermo.query_id()
        obj = {"mac" : mac,
"valve" : thermo.valve_state,
"target_temperature" : thermo.target_temperature,
"low_battery" : thermo.low_battery,
"locked" : thermo.locked}
        obj_json = json.dumps(obj)
        print("        TRV: %s" % human_name)
        print("        MAC: %s" % mac)
        print(" SW Version: %s" % thermo.firmware_version)
        print("     Serial: %s" % thermo.device_serial)
        print("      Valve: %s" % thermo.valve_state)
        print("       Mode: %s" % thermo.mode)
        print("Target temp: %s" % thermo.target_temperature)
        print("     Locked: %s" % thermo.locked)
        print("Low battery: %s" % thermo.low_battery)
        print("\n\n------\n\n")
        time.sleep(3) # Let the radio settle
        send_mqtt("trv/"+human_name, obj_json)
        time.sleep(0.5)
        #thermo.locked=True
    except bluepy.btle.BTLEDisconnectError:
        print("Failed to talk to %s.  Name: %s" % (each,human_name))
