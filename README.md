vpsdeploy
![](https://img.shields.io/badge/python%20-%203.7-brightgreen.svg)
========
> vps deploy tool 

## `Run`
1. 登陆vps
```
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
*/1 * * * * cd /root/pp && sh bohao.sh >log/bohao.log 2>&1
*/1 * * * * cd /root/pp && python heartbeat.py 
*/1 * * * * cd /root/pp && python pyproxy.py --log-file=log/pyproxy.log 
```

