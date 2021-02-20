#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import json
import logging
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


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

remote_workers = ["localhost", "pi-btle-relay-2", "thermopi"]

#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)

class S(BaseHTTPRequestHandler):
    sys_version = "0.00"
    server_version = "eq3 TRV Coordinator/"
    def _set_response(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response(400)
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        if not self.headers: return
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        status,obj = process_post(self.path,post_data.decode('utf-8'))
        self._set_response(status)
        obj = json.dumps(obj)
        self.wfile.write(obj.encode('utf-8'))

def process_post(path, data):
    try:
        json_data = json.loads(data)
        logging.info(json.dumps(json_data))
    except:
        logging.error("Failed to parse JSON")
        return 400,{"result":False, "message":"Failed to parse JSON"}
    if path == "/query_device":
        if "MAC" in json_data:
            mac = json_data["MAC"]
            r = dispatch_request("read_device",{"MAC":"mac"})
            if r is False:
                return 404,{"result":True, "message":"Failed to query device"}
            else:
                send_mqtt("trv/"+mac, r.json())
                return 200,{"result":True}
        else:    
            return 400,{"result",False}
    elif path == "/set_device":
        # We expect a JSON object as a dict
        # { "MAC": mac,
        #   "mode": ["manual"|"auto"|"boost"|"off"|"on", # On would have no timeout, but might still be useful
        #   "temperature" : float,
        #   "lock" : [True|False]
        # }
        if "MAC" in json_data:
            r = dispatch_request("set_device",json_data)
            if r is False:
                return 404,{"result":False}
            else:
                return r.status_code,r.json
        else:
            print("No mac")
            return 500, {"result":False, 
              "message":"MAC address not supplied"}
    elif path == "/scan":
        # Not implemented
        return 202,{"result":True}
    else:
        return 404,{"result":False}

def dispatch_request(endpoint,message):
    for each in remote_workers:
        url = "http://"+each+":8021/"+endpoint
        logging.debug("Trying remote worker: "+each)
        try:
            r = requests.post(url, json=message)
            print("xxx")
            print(r)
            print(r.status_code)
            print(r.json())
            if r.status_code == 200:
                logging.info("Got successful reply from remote worker "+each+" for "+human_name)
                return r
            else:
                logging.info("Didn't get a good reply from remote worker for "+human_name)
        except:
            logging.info("Failed to connect to remote worker: "+each)
    logging.info("Failed to get a result from any remote worker.")
    return False

def poll_all_trvs():
    good_list = []
    naughty_list = []
    for mac in trv_lookup.keys():
        human_name = trv_lookup[mac]
        print("Starting read for MAC: "+mac+".  Name: "+human_name)
        r = dispatch_request("read_device",{"MAC":mac})
        if r is False:
            continue
        elif r.status_code == 200:
            send_mqtt("trv/"+human_name, r.json())
            good_list.append(human_name)
        else:
            print("Something went wrong polling this device "+human_name)
        if human_name not in good_list:
            naughty_list.append(human_name)
            logging.info("Failed to read device: "+human_name)
    logging.info("Good list:")
    for each in good_list:
        logging.info("    "+each)
    logging.info("Naughty list:")
    for each in naughty_list:
        logging.info("    "+each)

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

def run(server_class=HTTPServer, handler_class=S, port=8020):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd.. on port '+str(port)+'.\n')
    x = threading.Thread(target=httpd.serve_forever)
    x.start()
    try:
        while True:
            poll_all_trvs()
            time.sleep(10*60)
    except KeyboardInterrupt:
        x.join()
        httpd.server_close()
        logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    mqttc = mqtt.Client("trv_server")
    mqttc.connect("calculon.whizzy.org", 1883)
    logging.info("Connected to MQTT broker")
    from sys import argv
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()

