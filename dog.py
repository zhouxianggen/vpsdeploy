# coding=utf-8
""" 判断是由有版本更新 
"""
import os
from subprocess import Popen, PIPE
import requests
import vps_config
import vps_utils


CWD = os.path.dirname(os.path.abspath(__file__))
REMOTE_VERSION = 'https://raw.githubusercontent.com/zhouxianggen/vpsdeploy/master/vpsdeploy/.version'
DEPLOY_SCRIPT = 'https://raw.githubusercontent.com/zhouxianggen/vpsdeploy/master/vpsdeploy/deploy.sh'


def open_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        print('打开链接[{}]失败'.format(url))
        return False
    return r.content


def get_remote_version():
    c = open_url(REMOTE_VERSION)
    if c:
        return float(c)
    return 0


def get_local_version():
    path = '{}/.version'.format(CWD)
    if os.path.isfile():
        return float(open(path, 'rb').read().strip())
    return 0


def main():
    remote_version = get_remote_version() 
    local_version = get_local_version()
    print('远端版本[{}], 本地版本[{}]'.format(remote_version, 
            local_version))
    
    if remote_version > local_version:
        print('更新版本')
        content = open_url(DEPLOY_SCRIPT)
        tmpfile = '%s/tmp.sh' % CWD
        open(tmpfile, 'wb').write(content)
        cmd = "/usr/bin/sh %s" % tmpfile
        process = Popen(cmd, shell=True, stdout=PIPE)
        stdout, stderr = process.communicate()
        print('部署结果：')
        print(stdout)
    print('运行结束')


if __name__ == '__main__':
    main()

