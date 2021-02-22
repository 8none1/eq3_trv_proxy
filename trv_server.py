#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import json
import logging
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import time



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
        logging.debug("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response(400)
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        logging.debug("POST request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
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
        logging.debug(json.dumps(json_data))
    except:
        logging.error("Failed to parse JSON")
        return 400,{"result":False, "message":"Failed to parse JSON"}
    
    if "MAC" not in json_data:
        logging.error("No MAC provided")
        return 500,{"result":False,
          "message":"No MAC address provided"}
    
    mac = json_data["MAC"]
    human_name = trv_lookup[mac]
        
    if path == "/query_device":
        r = dispatch_request("read_device",{"MAC":mac})
        if r is False:
            return 404,{"result":False, "message":"Failed to query device", "MAC":mac, "human_name":human_name}
        else:
            send_mqtt("trv/"+mac, r.json())
            return 200,{"result":True, "MAC":mac, "human_name":human_name}

    elif path == "/set_device":
        # We expect a JSON object as a dict
        # { "MAC": mac,
        #   "mode": ["manual"|"auto"|"boost"|"off"|"on", # On would have no timeout, but might still be useful
        #   "temperature" : float,
        #   "lock" : [True|False]
        # }
        r = dispatch_request("set_device",json_data)
        if r is False:
            return 404,{"result":False, "message":"Failed to query device", "MAC":mac, "human_name":human_name}
        else:
            message = r.json()
            meta = {'message':"Set completed successfully.", 
                       "results":True, "human_name":human_name}
            reply = {**message, **meta} # Join to dicts in Python 3.5+.
            return r.status_code,reply

    elif path == "/scan":
        # Not implemented
        return 202,{"result":True}
    else:
        return 404,{"result":False}

def dispatch_request(endpoint,message):
    for each in remote_workers:
        url = "http://"+each+":8021/"+endpoint
        human_name = trv_lookup[message['MAC']]
        logging.info("    Trying remote worker: "+each)
        try:
            r = requests.post(url, json=message)
            if r.status_code == 200:
                logging.info("        Got successful reply from remote worker "+each+" for "+human_name)
                if endpoint == "read_device":
                    send_mqtt("trv/"+human_name, r.json())
                return r
            else:
                logging.info("        Didn't get a good reply from remote worker for "+human_name)
        except:
            logging.info("        Failed to connect to remote worker: "+each)
    logging.info("        Failed to get a result from any remote worker.")
    return False

def poll_all_trvs():
    good_list = []
    naughty_list = []
    retry_list = [] # Using a new list because I'm lazy.  If this turns out to be useful, fix it.
    for mac in trv_lookup.keys():
        time.sleep(0.5) # Just to let bluepy helper settle
        human_name = trv_lookup[mac]
        logging.info("Starting read for MAC: "+mac+".  Name: "+human_name)
        r = dispatch_request("read_device",{"MAC":mac})
        if r is False:
            naughty_list.append(human_name)
            retry_list.append(mac)
            logging.info("    Failed to read device: "+human_name)
            #continue
        elif r.status_code == 200:
            logging.info("    Correctly read device: %s" % human_name)
            #send_mqtt("trv/"+human_name, r.json())
            good_list.append(human_name)
        else:
            logging.error("Something went wrong polling this device "+human_name)

    logging.info("Good list:")
    for each in good_list:
        logging.info("    "+each)
    logging.info("Naughty list:")
    for each in naughty_list:
        logging.info("    "+each)
    logging.info("Retrying naughty list:")
    for mac in retry_list:
        logging.info("    Retrying: %s" % trv_lookup[mac])
        r = dispatch_request("read_device",{"MAC":mac})
        if r is False:
            logging.info("  Failed again. :(")
        elif r.status_code == 200:
            logging.info("  Great success!")

def send_mqtt(topic,trv_obj):
    message = json.dumps(trv_obj)
    logging.info("Sending MQTT message...")
    logging.debug(json.dumps(trv_obj, indent=4, sort_keys=True))
    try:
        mqttc.connect("calculon.whizzy.org", 1883)
    except:
        logging.error("Couldnt connect to MQTT server?  WHY?!")
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
            logging.debug("Sleeping for 10 mins")
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

