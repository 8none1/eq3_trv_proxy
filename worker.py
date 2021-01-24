#!/usr/bin/env python3
#
# TRV worker node
#

from eq3bt import Thermostat
#import bluepy
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer


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
        status,obj = process_post(self.path,post_data.decode('utf-8'))
        self._set_response(status)
        obj = json.dumps(obj)
        self.wfile.write(obj.encode('utf-8'))

def process_post(path, data):
    try:
        json_data = json.loads(data)
        print(json.dumps(json_data))
    except:
        logging.error("Failed to parse JSON")
        return 400,{"result":False}
    if path == "/read_device":
        if "MAC" in json_data:
            mac = json_data["MAC"]
            print(mac)
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
    elif path == "/scan":
        return 202,""
    else:
        return 404,""

def read_device(mac):
    thermo = Thermostat(mac)
    try:
        thermo.update()
        thermo.query_id()
        obj = {
            "mac": mac,
            "result": True,
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