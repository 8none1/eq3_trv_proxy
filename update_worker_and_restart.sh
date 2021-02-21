#!/bin/bash
git pull 
sudo systemctl restart eq3_worker.service 
journalctl -u eq3_worker.service -f
