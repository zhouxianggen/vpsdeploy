#!/bin/bash

firewall-cmd --add-port=8899/tcp --permanent
iptables -F

yum -y install wget

wget 'https://raw.githubusercontent.com/zhouxianggen/vpsdeploy/master/setuptools-23.1.0.tar.gz'
tar -zxf setuptools-23.1.0.tar.gz
cd setuptools-23.1.0
python setup.py build
python setup.py install

easy_install requests

wget 'https://raw.githubusercontent.com/zhouxianggen/vpsdeploy/master/deploy.sh' -O deploy.sh
