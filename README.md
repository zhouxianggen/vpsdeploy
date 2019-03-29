vpsdeploy
![](https://img.shields.io/badge/python%20-%203.7-brightgreen.svg)
========
> vps deploy tool 

## `Run`

1. 登陆vps

```
curl 'https://raw.githubusercontent.com/zhouxianggen/vpsdeploy/master/init.sh' > init.sh
sh init.sh
sh deploy.sh
echo {name} > .name
```

2. 设置 crontab
```
*/2 * * * * cd /root/deploy && sh bohao.sh >log/bohao.log 2>&1
*/1 * * * * cd /root/deploy && python heartbeat.py 
*/1 * * * * cd /root/deploy && python pyproxy.py --log-file=log/pyproxy.log 
```

