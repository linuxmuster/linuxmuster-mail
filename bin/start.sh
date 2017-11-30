#!/bin/sh

RC=0
cd /srv/docker/linuxmuster-mail
chown docker:docker maildata -R
/usr/bin/docker-compose up -d mail || RC=1
exit $RC
