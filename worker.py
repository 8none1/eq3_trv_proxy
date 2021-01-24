#!/usr/bin/env python3
#
# TRV worker node
#

#from eq3bt import Thermostat
#import bluepy
import json
import logging
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

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

class S(BaseHTTPRequestHandler):
    def _set_response(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response(400)
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                str(self.path), str(self.headers), post_data.decode('utf-8'))
        self._set_response(202)
        self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))
        status = process_post(self.path,post_data.decode('utf-8'))
        print("Did processes")
        print(status)


def process_post(path, data):
    print("=====")
    print(path)
    print(data)
    print("xxx")
    try:
        json_data = json.loads(data)
        print(json.dumps(json_data))
    except:
        logging.error("Failed to parse JSON")
        return 400
    if path == "/read_device":
        if "MAC" in json_data and "return_addr" in json_data:
            return_addr = json_data["return_addr"]
            for each in json_data["MAC"]:
                print(each)
                status = read_device(each)
                if status == False:
                    return_obj = {"MAC":each, "data":{"result":False}}
                    requests.post(return_addr, json=return_obj)
                if isinstance(status, dict):
                    # If we got a dict back, then the read must have worked
                    return_obj = {"MAC":each, "data":status}
                    requests.post(return_addr, json=return_obj)
            return 202
        else:
            return 400
    elif path == "/set_device":
        return 202
    elif path == "/scan":
        return 202
    else: return 404

def read_device(mac):
    return False
    thermo = Thermostat(mac)
    try:
        thermo.update()
        thermo.query_id()
        obj = {
            "result": True,
            "valve" : thermo.valve_state,
            "target_temperature" : thermo.target_temperature,
            "low_battery" : thermo.low_battery,
            "locked" : thermo.locked
        }
        #obj_json = json.dumps(obj)
        return obj_json
    except bluepy.btle.BTLEDisconnectError:
        logging.error("Failed to talk to device.")
        return False


def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()