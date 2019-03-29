#!/bin/bash

GITHOME='https://raw.githubusercontent.com/zhouxianggen/vpsdeploy/master/vpsdeploy'
WDIR="$HOME/deploy"

if [ ! -d $WDIR ];then
    echo "创建工作目录" 
    mkdir $WDIR
fi


cd $WDIR
mkdir log
echo "下载服务脚本" 
wget "${GITHOME}/heartbeat.py" -O heartbeat.py
wget "${GITHOME}/pyproxy.py" -O pyproxy.py
wget "${GITHOME}/dog.py" -O dog.py
wget "${GITHOME}/vps/bohao.sh" -O bohao.sh
wget "${GITHOME}/vps/.version" -O .version

echo "部署成功"
