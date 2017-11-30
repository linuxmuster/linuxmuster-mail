#!/bin/sh

RC=0
/usr/bin/docker stop mail || RC=1
exit $RC
