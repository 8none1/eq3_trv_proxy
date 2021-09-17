# What

A client and server which allows for a LAN distributed system to query eq3 BT LE TRVs and return the data to MQTT.

# How

1. Create a python venv
1. From pip install requests, paho-mqtt, python-eq3bt
1. From pip install `python -m pip install git+https://github.com/IanHarvey/bluepy.git`

It's important to install bluepy from Git because there are some essential fixes in the master branch that are not in the latest release.

