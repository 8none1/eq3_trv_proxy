# What

A client and server which allows for a LAN distributed system to query eq3 BT LE TRVs and return the data to MQTT.

# How

1. Create a python venv
1. From pip install requests, paho-mqtt
1. From pip install `python3 -m pip install git+https://github.com/IanHarvey/bluepy.git`
1. From pip install `python3 -m pip install git+https://github.com/8none1/python-eq3bt.git@will`

It's important to install bluepy from Git because there are some essential fixes in the master branch that are not in the latest release.

The version of eq3bt from my fork adds timeouts to the BTLE connection.  This speeds up polling of multiple devices.


