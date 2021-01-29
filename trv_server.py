#!/usr/bin/env python3

from eq3bt import Thermostat
import bluepy
import paho.mqtt.client as mqtt
import json
import logging
import time
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
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

remote_workers = ["pi-btlerelay-1"]

#logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.INFO)

def send_mqtt(topic,trv_obj):
    message = json.dumps(trv_obj)
    logging.debug("Sending MQTT message...")
    logging.debug(json.dumps(trv_obj, indent=4, sort_keys=True))
    mqttc.reconnect()
    mqttc.publish(topic,message)
    mqttc.loop(2)
    mqttc.disconnect()

class S(BaseHTTPRequestHandler):
    sys_version = "0.00"
    server_version = "BTLE TRV Server/"

    def _set_response(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        logging.debug("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response(400)
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        global process_post
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        status,obj = process_post(self.path,post_data.decode('utf-8'))
        self._set_response(status)
        json_str = json.dumps(obj)
        self.wfile.write(json_str.encode('utf-8'))

def process_post(path, data):
    logging.info("Processing POSTed data")
    try:
        json_data = json.loads(data)
        logging.debug(json.dumps(json_data))
    except:
        logging.error("Failed to parse POSTed JSON")
        return 400,{"result":False}
    if path == "/read_device":
        if "MAC" in json_data:
            mac = json_data["MAC"]
            global read_device # ?
            status = read_device(mac) # XXX rename me from status
            if status == False:
                return 404,{"result":False}
            elif isinstance(status, dict):
                # If we got a dict back, then the read must have worked
                return 200, status
            else:
                return 500, {"result":False}
    elif path == "/set_device":
        return 202,""
    else:
        return 404,""

def read_device(mac):
    logging.debug("Trying to read from TRV...")
    thermo = Thermostat(mac)
    try:
        thermo.update()
        obj = {
            "mac": mac,
            "valve" : thermo.valve_state,
            "target_temperature" : thermo.target_temperature,
            "low_battery" : thermo.low_battery,
            "locked" : thermo.locked
        }
        return obj
    except bluepy.btle.BTLEDisconnectError:
        logging.error("Failed to talk to device.")
        return False


def run(server_class=HTTPServer, handler_class=S, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd.. on port '+str(port)+'.\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    t = Thread(target=run)
    t.start()
    mqttc = mqtt.Client("python_pub")
    mqttc.connect("calculon.whizzy.org", 1883)
    logging.info("Connected to MQTT broker")

    while True:
        for mac in trv_lookup.keys():
            logging.debug("Starting read for MAC: "+mac)
            human_name = trv_lookup[mac]
            trv = read_device(mac)
            if trv is not False:
                send_mqtt("trv/"+human_name, trv)
                #time.sleep(0.5)
            elif trv is False:
                # Reading of data failed, so send it to the proxies
                logging.debug("Locally connection failed, trying remote.")
                for each in remote_workers:
                    logging.debug("Trying remote worker: "+each)
                    message = {"MAC":mac}
                    r = requests.post("http://"+each+":8080/read_device", json=message)
                    if r.status_code == 200:
                        logging.debug("Got successful reply from remote worker.")
                        send_mqtt("trv/"+human_name, r.json())
                        break
                    else:
                        logging.debug("Didn't get a good reply.")
        logging.debug("Completed this run.  Sleeping for 10 mins")
        time.sleep(10 * 60)


