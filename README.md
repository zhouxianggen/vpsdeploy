vpsdeploy
![](https://img.shields.io/badge/python%20-%203.7-brightgreen.svg)
========
> vps deploy tool 

## `Run`

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
