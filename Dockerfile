FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y
RUN apt-get install -y python3.9 python3-pip clamav clamav-daemon clamav-freshclam clamdscan
RUN apt-get autoclean -y
RUN apt-get autoremove -y
RUN apt-get clean
RUN update-rc.d clamav-daemon enable
RUN update-rc.d clamav-freshclam enable
RUN freshclam
RUN service clamav-freshclam start
RUN service clamav-daemon start

COPY ./requirements.txt /app/requirements.txt
COPY ./clamd.conf /etc/clamav/clamd.conf

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

COPY commands.sh /scripts/commands.sh
RUN ["chmod", "+x", "/scripts/commands.sh"]
ENTRYPOINT ["/scripts/commands.sh"]
