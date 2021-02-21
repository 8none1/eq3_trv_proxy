cd /etc/systemd/system/
sudo rm eq3*
cd /etc/systemd/system/
sudo ln -s /home/pi/trv_server/eq3_trv_proxy/eq3_worker.service eq3_worker.service
sudo systemctl enable eq3_worker.service
sudo systemctl start eq3_worker.service
