# coding: utf8 
""" python proxy server
refer: https://github.com/abhinavsingh/proxy.py
"""
import os
import sys
import time
import logging
import logging.handlers
import argparse
import threading
import socket
import select
from collections import namedtuple
if os.name != 'nt':
    import resource


PY3 = sys.version_info[0] == 3
if PY3: 
    from urllib import parse as urlparse
else:
    import urlparse


CRLF, COLON, SPACE = b'\r\n', b':', b' '

PROXY_TUNNEL_ESTABLISHED_RESPONSE_PKT = CRLF.join([
    b'HTTP/1.1 200 Connection established',
    CRLF
])

BAD_GATEWAY_RESPONSE_PKT = CRLF.join([
    b'HTTP/1.1 502 Bad Gateway',
    b'Content-Length: 11',
    b'Connection: close',
    CRLF
]) + b'Bad Gateway'

PROXY_AUTHENTICATION_REQUIRED_RESPONSE_PKT = CRLF.join([
    b'HTTP/1.1 407 Proxy Authentication Required',
    b'Content-Length: 29',
    b'Connection: close',
    CRLF
]) + b'Proxy Authentication Required'


class LogObject(object):
    def __init__(self, log_file=None, log_level=logging.INFO):
        self.log_file = log_file
        self.log_level = log_level
        self.log = logging.getLogger(self.__class__.__name__)
        if not self.log.handlers:
            if log_file:
                handler = logging.handlers.RotatingFileHandler(
                        log_file, maxBytes=1024*1024*500, backupCount=10)
            else:
                handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                    '[%(name)-18s %(threadName)-10s %(levelname)-8s '
                    '%(asctime)s] %(message)s'))
            self.log.addHandler(handler)
        self.log.setLevel(log_level)


class ChunkParser(object):
    """HTTP chunked encoding response parser."""

    states = namedtuple('ChunkParserStates', (
        'WAITING_FOR_SIZE',
        'WAITING_FOR_DATA',
        'COMPLETE'
    ))(1, 2, 3)

    def __init__(self):
        self.state = ChunkParser.states.WAITING_FOR_SIZE
        self.body = b''     # Parsed chunks
        self.chunk = b''    # Partial chunk received
        self.size = None    # Expected size of next following chunk


    def parse(self, data):
        more = True if len(data) > 0 else False
        while more:
            more, data = self.process(data)


    def process(self, data):
        if self.state == ChunkParser.states.WAITING_FOR_SIZE:
            # Consume prior chunk in buffer
            # in case chunk size without CRLF was received
            data = self.chunk + data
            self.chunk = b''
            # Extract following chunk data size
            line, data = HttpParser.split(data)
            if not line:    # CRLF not received
                self.chunk = data
                data = b''
            else:
                self.size = int(line, 16)
                self.state = ChunkParser.states.WAITING_FOR_DATA
        elif self.state == ChunkParser.states.WAITING_FOR_DATA:
            remaining = self.size - len(self.chunk)
            self.chunk += data[:remaining]
            data = data[remaining:]
            if len(self.chunk) == self.size:
                data = data[len(CRLF):]
                self.body += self.chunk
                if self.size == 0:
                    self.state = ChunkParser.states.COMPLETE
                else:
                    self.state = ChunkParser.states.WAITING_FOR_SIZE
                self.chunk = b''
                self.size = None
        return len(data) > 0, data


class HttpParser(LogObject):
    """HTTP request/response parser."""

    states = namedtuple('HttpParserStates', (
        'INITIALIZED',
        'LINE_RCVD',
        'RCVING_HEADERS',
        'HEADERS_COMPLETE',
        'RCVING_BODY',
        'COMPLETE'))(1, 2, 3, 4, 5, 6)

    types = namedtuple('HttpParserTypes', (
        'REQUEST_PARSER',
        'RESPONSE_PARSER'
    ))(1, 2)

    def __init__(self, parser_type, log_file=''):
        LogObject.__init__(self, log_file)
        assert parser_type in (HttpParser.types.REQUEST_PARSER, 
                HttpParser.types.RESPONSE_PARSER)
        self.type = parser_type
        self.state = HttpParser.states.INITIALIZED

        self.raw = b''
        self.buffer = b''

        self.headers = dict()
        self.body = None

        self.method = None
        self.url = None
        self.code = None
        self.reason = None
        self.version = None

        self.chunk_parser = None


    def is_chunked_encoded_response(self):
        return (self.type == HttpParser.types.RESPONSE_PARSER and 
            b'transfer-encoding' in self.headers and 
            self.headers[b'transfer-encoding'][1].lower() == b'chunked')

        
    def parse(self, data):
        self.raw += data
        data = self.buffer + data
        self.buffer = b''

        more = True if len(data) > 0 else False
        while more:
            more, data = self.process(data)
        self.buffer = data


    def process(self, data):
        self.log.debug('process [{}]'.format(self.state))
        if (self.state in (HttpParser.states.HEADERS_COMPLETE,
                          HttpParser.states.RCVING_BODY,
                          HttpParser.states.COMPLETE) and 
                (self.method == b'POST' or 
                        self.type == HttpParser.types.RESPONSE_PARSER)):
            if not self.body:
                self.body = b''

            if b'content-length' in self.headers:
                self.state = HttpParser.states.RCVING_BODY
                self.body += data
                if len(self.body) >= int(self.headers[b'content-length'][1]):
                    self.state = HttpParser.states.COMPLETE
            elif self.is_chunked_encoded_response():
                if not self.chunk_parser:
                    self.chunk_parser = ChunkParser()
                self.chunk_parser.parse(data)
                if self.chunk_parser.state == ChunkParser.states.COMPLETE:
                    self.body = self.chunk_parser.body
                    self.state = HttpParser.states.COMPLETE
            return False, b''

        line, remain = HttpParser.split(data)
        if line is False:
            return line, remain

        if self.state == HttpParser.states.INITIALIZED:
            self.process_line(line)
        elif self.state in (HttpParser.states.LINE_RCVD, 
                HttpParser.states.RCVING_HEADERS):
            self.process_header(line)

        # fixed bug: when client send CONNECT with 2 pkg 
        if (self.state == HttpParser.states.RCVING_HEADERS and 
                self.type == HttpParser.types.REQUEST_PARSER and 
                self.method == b'CONNECT' and 
                not remain):
            self.state = HttpParser.states.COMPLETE
        elif (self.state == HttpParser.states.LINE_RCVD and 
                self.type == HttpParser.types.REQUEST_PARSER and 
                self.method == b'CONNECT' and 
                remain == CRLF):
            self.state = HttpParser.states.COMPLETE
        elif (self.state == HttpParser.states.HEADERS_COMPLETE and 
                self.type == HttpParser.types.REQUEST_PARSER and 
                self.method != b'POST' and 
                self.raw.endswith(CRLF * 2)):
            self.state = HttpParser.states.COMPLETE
        elif (self.state == HttpParser.states.HEADERS_COMPLETE and 
                self.type == HttpParser.types.REQUEST_PARSER and 
                self.method == b'POST' and 
                (b'content-length' not in self.headers or
                 (b'content-length' in self.headers and
                  int(self.headers[b'content-length'][1]) == 0)) and 
                self.raw.endswith(CRLF * 2)):
            self.state = HttpParser.states.COMPLETE
        return len(remain) > 0, remain


    def process_line(self, data):
        self.log.debug('process_line')
        line = data.split(SPACE)
        if self.type == HttpParser.types.REQUEST_PARSER:
            self.method = line[0].upper()
            self.url = urlparse.urlsplit(line[1])
            self.version = line[2]
            self.log.debug('[{}][{}][{}]'.format(self.method, self.url, 
                    self.version))
        else:
            self.version = line[0]
            self.code = line[1]
            self.reason = b' '.join(line[2:])
        self.state = HttpParser.states.LINE_RCVD


    def process_header(self, data):
        self.log.debug('process_header [{}]'.format(data))
        if len(data) == 0:
            if self.state == HttpParser.states.RCVING_HEADERS:
                self.state = HttpParser.states.HEADERS_COMPLETE
            elif self.state == HttpParser.states.LINE_RCVD:
                self.state = HttpParser.states.RCVING_HEADERS
        else:
            self.state = HttpParser.states.RCVING_HEADERS
            parts = data.split(COLON)
            key = parts[0].strip()
            value = COLON.join(parts[1:]).strip()
            self.headers[key.lower()] = (key, value)


    def build_url(self):
        if not self.url:
            return b'/None'

        url = self.url.path
        if url == b'':
            url = b'/'
        if not self.url.query == b'':
            url += b'?' + self.url.query
        if not self.url.fragment == b'':
            url += b'#' + self.url.fragment
        return url


    def build(self, del_headers=None, add_headers=None):
        req = b' '.join([self.method, self.build_url(), self.version])
        req += CRLF

        if not del_headers:
            del_headers = []
        for k in self.headers:
            if k not in del_headers:
                req += self.build_header(self.headers[k][0], 
                        self.headers[k][1]) + CRLF

        if not add_headers:
            add_headers = []
        for k in add_headers:
            req += self.build_header(k[0], k[1]) + CRLF

        req += CRLF
        if self.body:
            req += self.body

        return req


    @staticmethod
    def build_header(k, v):
        return k + b': ' + v


    @staticmethod
    def split(data):
        pos = data.find(CRLF)
        if pos == -1:
            return False, data
        line = data[:pos]
        data = data[pos + len(CRLF):]
        return line, data


class Connection(LogObject):
    """TCP server/client connection abstraction."""

    def __init__(self, what, log_file=''):
        LogObject.__init__(self, log_file)
        self.conn = None
        self.buffer = b''
        self.closed = False
        self.what = what  # server or client


    def send(self, data):
        # TODO: Gracefully handle BrokenPipeError exceptions
        return self.conn.send(data)


    def recv(self, bufsiz=8192):
        try:
            data = self.conn.recv(bufsiz)
            self.log.info('rcvd [{}] bytes from [{}]'.format(
                    len(data), self.what))
            if len(data) == 0:
                return None
            return data
        except Exception as e:
            self.log.exception(e)
            return None


    def close(self):
        self.conn.close()
        self.closed = True


    def buffer_size(self):
        return len(self.buffer)


    def has_buffer(self):
        return self.buffer_size() > 0


    def queue(self, data):
        self.buffer += data


    def flush(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]


class Server(Connection):
    def __init__(self, host, port, log_file=''):
        super(Server, self).__init__('server', log_file)
        self.addr = (host, int(port))

    def __del__(self):
        if self.conn:
            self.close()

    def connect(self):
        self.conn = socket.create_connection((self.addr[0], self.addr[1]))


class Client(Connection):
    def __init__(self, conn, addr, log_file=''):
        super(Client, self).__init__('client', log_file)
        self.conn = conn
        self.addr = addr


class ProxyError(Exception):
    pass


class ProxyConnectionFailed(ProxyError):
    def __init__(self, host, port, reason):
        self.host = host
        self.port = port
        self.reason = reason

    def __str__(self):
        return '<ProxyConnectionFailed - {}:{} - {}>'.format(self.host, 
                self.port, self.reason)


class ProxyAuthenticationFailed(ProxyError):
    pass


def get_response_pkt_by_exception(e):
    if e.__class__.__name__ == 'ProxyAuthenticationFailed':
        return PROXY_AUTHENTICATION_REQUIRED_RESPONSE_PKT
    if e.__class__.__name__ == 'ProxyConnectionFailed':
        return BAD_GATEWAY_RESPONSE_PKT


class Tunnel(threading.Thread, LogObject):
    """ act as a tunnel between client and server.
    """

    def __init__(self, client, server_recvbuf_size=8192, 
            client_recvbuf_size=8192, log_file=''):
        LogObject.__init__(self, log_file=log_file)
        threading.Thread.__init__(self)
        self.daemon = True

        self.start_time = time.time()
        self.last_activity = self.start_time
        self.client = client
        self.client_recvbuf_size = client_recvbuf_size
        self.server = None
        self.server_recvbuf_size = server_recvbuf_size

        self.request = HttpParser(HttpParser.types.REQUEST_PARSER, self.log_file)
        self.response = HttpParser(HttpParser.types.RESPONSE_PARSER, self.log_file)


    def _is_inactive(self):
        return (time.time() - self.last_activity) > 30


    def run(self):
        try:
            self._process()
        except Exception as e:
            self.log.exception(e)
        finally:
            self.log.info('close client connection')
            self.client.close()
    
    
    def _process(self):
        while True:
            self.log.debug('_process')
            rlist, wlist, xlist = self._get_waitable_lists()
            r, w, x = select.select(rlist, wlist, xlist, 1)

            self._process_wlist(w)
            if self._process_rlist(r):
                break

            if self.client.buffer_size() == 0:
                if self.response.state == HttpParser.states.COMPLETE:
                    self.log.info('client buffer empty and response complete')
                    break

                if self._is_inactive():
                    self.log.info('client buffer empty and inactivity')
                    break


    def _get_waitable_lists(self):
        rlist, wlist, xlist = [self.client.conn], [], []
        if self.client.has_buffer():
            wlist.append(self.client.conn)
        if self.server and not self.server.closed:
            rlist.append(self.server.conn)
        if self.server and not self.server.closed and self.server.has_buffer():
            wlist.append(self.server.conn)
        return rlist, wlist, xlist


    def _process_wlist(self, w):
        if self.client.conn in w:
            self.log.info('client is ready for writes, flushing client buffer')
            self.client.flush()

        if self.server and not self.server.closed and self.server.conn in w:
            self.log.info('server is ready for writes, flushing server buffer')
            self.server.flush()
    
    
    def _process_rlist(self, r):
        """Returns True if connection to client must be closed."""
        if self.client.conn in r:
            self.log.info('client is ready for reads')
            self.last_activity = time.time()
            data = self.client.recv(self.client_recvbuf_size)
            if not data:
                self.log.info('client closed connection')
                return True

            try:
                self._process_request(data)
            except (ProxyAuthenticationFailed, ProxyConnectionFailed) as e:
                self.log.exception(e)
                self.client.queue(get_response_pkt_by_exception(e))
                self.client.flush()
                return True

        if self.server and not self.server.closed and self.server.conn in r:
            self.log.info('server is ready for reads')
            self.last_activity = time.time()
            data = self.server.recv(self.server_recvbuf_size)
            if not data:
                self.log.info('server closed connection')
                self.server.close()
            else:
                self._process_response(data)
        return False


    def _process_request(self, data):
        self.log.debug('_process_request [{}]'.format(self.request.state))
        # redirect data to server once connected
        if self.server and not self.server.closed:
            self.server.queue(data)
            return

        # parse http request
        self.request.parse(data)

        if self.request.state == HttpParser.states.COMPLETE:
            self.log.info('request parser is in state complete')
            if self.request.method == b'CONNECT':
                host, port = self.request.url.path.split(COLON)
            elif self.request.url:
                host = self.request.url.hostname
                port = self.request.url.port if self.request.url.port else 80
            else:
                raise Exception('Invalid request\n%s' % self.request.raw)

            self.server = Server(host, port, self.log_file)
            try:
                self.log.info('connecting server [{}]:[{}]'.format(host, port))
                self.server.connect()
            except Exception as e:  # TimeoutError, socket.gaierror
                self.log.exception(e)
                self.server.closed = True
                raise ProxyConnectionFailed(host, port, repr(e))

            if self.request.method == b'CONNECT':
                self.client.queue(PROXY_TUNNEL_ESTABLISHED_RESPONSE_PKT)
            else:
                self.server.queue(self.request.build(
                    del_headers=[b'proxy-authorization', b'proxy-connection', 
                            b'connection', b'keep-alive'],
                    add_headers=[(b'Connection', b'Close')]
                ))


    def _process_response(self, data):
        if not self.request.method == b'CONNECT':
            self.response.parse(data)
        self.client.queue(data)

    
class TCPServer(LogObject):
    def __init__(self, hostname='0.0.0.0', port=8899, backlog=100, log_file=''):
        LogObject.__init__(self, log_file=log_file)
        self.hostname = hostname
        self.port = port
        self.backlog = backlog
        self.socket = None


    def handle(self, client):
        raise NotImplementedError()


    def run(self):
        try:
            self.log.info('Starting server on port %d' % self.port)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.hostname, self.port))
            self.socket.listen(self.backlog)
            while True:
                conn, addr = self.socket.accept()
                client = Client(conn, addr, self.log_file)
                self.handle(client)
        except Exception as e:
            self.log.exception(e)
        finally:
            self.log.info('closing server socket')
            self.socket.close()


class PyProxy(TCPServer):
    def __init__(self, hostname='0.0.0.0', port=8899, backlog=100,
                 server_recvbuf_size=8192, client_recvbuf_size=8192, 
                 log_file=''):
        TCPServer.__init__(self, hostname, port, backlog, log_file)
        self.client_recvbuf_size = client_recvbuf_size
        self.server_recvbuf_size = server_recvbuf_size


    def handle(self, client):
        self.log.info('handle request from [{}]'.format(client.addr))
        tunnel = Tunnel(client,
                      server_recvbuf_size=self.server_recvbuf_size,
                      client_recvbuf_size=self.client_recvbuf_size, 
                      log_file=self.log_file)
        tunnel.start()


def set_open_file_limit(limit):
    if os.name != 'nt':  # resource module not available on Windows OS
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        if soft_limit < limit < hard_limit:
            resource.setrlimit(resource.RLIMIT_NOFILE, (limit, hard_limit))


def is_addr_used(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return True if result == 0 else False


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--hostname', default='0.0.0.0')
    parser.add_argument('--port', default='8899', type=int)
    parser.add_argument('--backlog', default='100', type=int)
    parser.add_argument('--server-recvbuf-size', default='8192', type=int)
    parser.add_argument('--client-recvbuf-size', default='8192', type=int)
    parser.add_argument('--open-file-limit', default='1024', type=int)
    parser.add_argument('--log-file', default='')
    args = parser.parse_args()

    if is_addr_used(args.hostname, args.port):
        print('server already run. exit ..')
        return

    set_open_file_limit(int(args.open_file_limit))
    proxy = PyProxy(hostname=args.hostname,
            port=args.port,
            backlog=args.backlog,
            server_recvbuf_size=args.server_recvbuf_size,
            client_recvbuf_size=args.client_recvbuf_size, 
            log_file=args.log_file)
    proxy.run()


if __name__ == '__main__':
    main()

