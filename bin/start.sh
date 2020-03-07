#!/bin/sh

cd /srv/docker/linuxmuster-mail
chown docker:docker maildata -R
/usr/bin/docker-compose up -d
