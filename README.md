vpsdeploy
![](https://img.shields.io/badge/python%20-%203.7-brightgreen.svg)
========
> vps deploy tool 

## `Run`
1. 登陆vps
```
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
```

1. set vps name
```
echo name > .name
```

2. crontab
```
*/1 * * * * cd /root/deploy && sh bohao.sh >log/bohao.log 2>&1
*/1 * * * * cd /root/deploy && python heartbeat.py 
*/1 * * * * cd /root/deploy && python pyproxy.py --log-file=log/pyproxy.log 
```

