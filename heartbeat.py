# coding: utf8 
import os
import logging
import logging.handlers
import time
import socket
import json
import requests


CWD = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = '{}/log/heartbeat.log'.format(CWD)
RUN_PATH = '{}/.runtime'.format(CWD)
ADMIN_HOST = 'http://114.55.31.211:8888/_add_proxy'
PROXY_PORT = 8899


log = logging.getLogger('heartbeat')
if LOG_PATH:
    handler = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=1024*1024*500, backupCount=10)
else:
    handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
        '[%(name)-18s %(threadName)-10s %(levelname)-8s '
        '%(asctime)s] %(message)s'))
log.addHandler(handler)
log.setLevel(logging.INFO)


def read_file(path):
    return open(path).read().strip() if os.path.isfile(path) else ''


def get_name():
    return read_file('{}/.name'.format(CWD))


def is_running():
    c = read_file(RUN_PATH)
    return c and c.isdigit() and int(c) + 1 > int(time.time())


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 53))
        n = s.getsockname()
        ip = n[0] if n else None
        s.close()
        return ip
    except Exception as e:
        return None


def run():
    if is_running():
        log.info('program already running, exit..')
        return

    while True:
        time.sleep(0.1)
        open(RUN_PATH, 'wb').write(str(int(time.time())))

        ip = get_ip()
        log.info('current ip is [{}]'.format(ip))
        if not ip:
            return

        b = {'type': 'vps', 'name': get_name(), 'schemes': ['HTTP', 'HTTPS'], 
                'ip': get_ip(), 'port': PROXY_PORT }
        log.info('send heartbeat to admin')
        try:
            r = requests.post(ADMIN_HOST, 
                    data=json.dumps(b), timeout=2)
            log.info(r.status_code)
        except Exception as e:
            log.exception(e)


run()

