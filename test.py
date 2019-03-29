# coding: utf8 
import sys
import requests


url = 'https://www.cnblogs.com/dzqdzq/p/9822187.html'

host = 'localhost'
if len(sys.argv) > 1:
    host = sys.argv[1]

proxies = {'http': 'http://{}:8899'.format(host), 
        'https': 'http://{}:8899'.format(host)}
r = requests.get(url, proxies=proxies)
print(r.status_code)
print(len(r.content))

