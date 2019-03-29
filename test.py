# coding: utf8 
import sys
import requests


url = 'https://www.cnblogs.com/dzqdzq/p/9822187.html'
if len(sys.argv) > 1:
    url = sys.argv[1]

host = 'localhost'
host = '113.128.24.147'
proxies = {'http': 'http://{}:8899'.format(host), 
        'https': 'http://{}:8899'.format(host)}
r = requests.get(url, proxies=proxies)
print(r.status_code)
print(len(r.content))

