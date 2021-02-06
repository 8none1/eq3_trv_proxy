#!/usr/bin/env python3

from python_eq3bt import Thermostat
import bluepy
import paho.mqtt.client as mqtt
import json
import logging
import time
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from random import randint
import sys

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

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.ERROR)

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
    mqttc = mqtt.Client("trv_server")
    mqttc.connect("calculon.whizzy.org", 1883)
    logging.info("Connected to MQTT broker")

    while True:
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
        logging.info("Completed this run.  Sleeping for 10 mins")
        sys.stdout.flush()
        time.sleep(10 * 60 + randint(1,30)) # apply a little jitter
        good_list = [] 
        naughty_list = []

httpd.server_close()
logging.info('Stopping httpd...\n')