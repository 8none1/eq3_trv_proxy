#!/usr/bin/env python3
#
# TRV worker node
#

import eq3bt
import bluepy
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.DEBUG)

MODE_LOOKUP = { # From the eq3bt library
    "on" : 1,
    "off" : 0,
    "boost" : 5,
    "auto" : 2,
    "manual" : 3
}

class S(BaseHTTPRequestHandler):
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
        logging.error("    Failed to parse JSON")
        return 400,{"result":False, "message":"Failed to parse JSON"}
    if path == "/read_device":
        if "MAC" in json_data:
            mac = json_data["MAC"]
            logging.info("    Trying to read MAC: "+mac)
            thermo_state = read_device(mac)
            if thermo_state == False:
                return 404,{"result":False}
            elif isinstance(thermo_state, dict):
                # If we got a dict back, then the read must have worked
                return 200, thermo_state
            else:
                return 500, {"result":False}
        return 400,{"result",False}
    elif path == "/set_device":
        # We expect a JSON object as a dict
        # { "MAC": mac,
        #   "mode": ["manual"|"auto"|"boost"|"off"|"on", # On would have no timeout, but might still be useful
        #   "temperature" : float,
        #   "lock" : [True|False]
        # }
        logging.info("    Doing SET device...")
        if "MAC" in json_data:
            mac = json_data["MAC"]
            thermo = eq3bt.Thermostat(mac)
            try:
                if "mode" in json_data:
                    mode = MODE_LOOKUP[json_data["mode"]]
                    thermo.mode = mode
                    logging.info("    ✓ Set mode: %s" % mode)
                if "temperature" in json_data:
                    thermo.target_temperature = json_data["temperature"]
                    logging.info("    ✓ Set temperature: %s" % json_data["temperature"])
                if "lock" in json_data:
                    thermo.locked = json_data["lock"]
                    logging.info("    ✓ Set lock: %s" % json_data["lock"])  
                return 200,{"result":True,"MAC":mac}
            except bluepy.btle.BTLEDisconnectError:
                logging.error("    Failed to talk to device: %s" % mac)
                return 404,{"result":False, "message":"Couldn't connect to device", "MAC":mac}
            except bluepy.btle.BTLETimeoutError:
                logging.info("    Timed out talking to device: %s" % mac)
                return 404,{"result":False, "MAC":mac,"message":"Time out"}
            except:
                logging.error("    Something went wrong trying to set device: %s" % mac)
                return 500,{"result":False,"message":"Failed to set device", "MAC":mac}
        else:
            logging.error("    No mac")
            return 500, {"result":False,
              "message":"MAC address not supplied", "MAC":mac}
    elif path == "/scan":
        # Not implemented
        return 202,{"result":True}
    else:
        return 404,{"result":False,"message":"Unknown or unsupported path"}

def read_device(mac):
    thermo = eq3bt.Thermostat(mac)
    try:
        thermo.update()
        # thermo.query_id() # I don't think we actually do anything with this
        try:
            print(f"Mode: {thermo.mode_readable}")
        except:
            print("Nope")
        obj = {
            "mac": mac,
            "valve" : thermo.valve_state,
            "target_temperature" : thermo.target_temperature,
            "low_battery" : thermo.low_battery,
            "locked" : thermo.locked
        }
        logging.info(json.dumps(obj))
        return obj
    except bluepy.btle.BTLEDisconnectError:
        logging.error("    Failed to talk to device.")
        return False
    except bluepy.btle.BTLETimeoutError:
        logging.error("    Timedout when trying to connect to device.")
        return False


def run(server_class=HTTPServer, handler_class=S, port=8021):
    logging.basicConfig(level=logging.INFO)
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
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
