#!/bin/sh

apt-get update -y
apt-get install -y python3.9 python3-pip clamav clamav-daemon clamav-freshclam clamdscan
apt-get autoclean -y
apt-get autoremove -y
apt-get clean
freshclam
service clamav-daemon start

python3 -u ./main.py