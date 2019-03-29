#!/bin/bash

PATH=/root/perl5/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin:/bin
HOME=/root
HOSTNAME=localhost.localdomain
LANG=en_US.UTF-8
LD_LIBRARY_PATH=/root/lib64:
LOGNAME=root
MAIL=/var/spool/mail/root
PWD=/root
SHELL=/bin/bash
SHLVL=1
USER=root

echo "now restarting..."
echo $(hostname -I)
/bin/systemctl stop NetworkManager.service
ps aux | grep "pppoe" | grep -v "grep" | awk '{ print $2; }' | xargs sudo kill -SIGTERM
pppoe-stop
sleep 1
pppoe-start
echo $(hostname -I)
echo "finished"
