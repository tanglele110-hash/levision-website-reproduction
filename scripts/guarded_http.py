# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Bounded, address-pinned HTTP transport. No proxy, cookies or automatic redirects."""
import http.client
import ipaddress
import re
import queue
import socket
import ssl
import threading
import time
from urllib.parse import urlsplit, urlunsplit


class CaptureBlocked(ValueError):
    pass


def public_address(value):
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast or address.is_reserved:
        return False
    if address.version == 6:
        return (address in ipaddress.ip_network('2000::/3')
                and address not in ipaddress.ip_network('2001::/23')
                and address not in ipaddress.ip_network('2001:db8::/32')
                and address not in ipaddress.ip_network('2002::/16')
                and address not in ipaddress.ip_network('3fff::/20'))
    return not any(address in ipaddress.ip_network(cidr) for cidr in (
        '192.0.0.0/24', '192.0.2.0/24', '192.88.99.0/24',
        '198.18.0.0/15', '198.51.100.0/24', '203.0.113.0/24'))


def safe_url(value):
    """Never persist query values, fragments, or userinfo in transport records."""
    try:
        url = urlsplit(value)
        host = url.hostname or ''
        if ':' in host:
            host = '[' + host + ']'
        port = ':' + str(url.port) if url.port else ''
        return urlunsplit((url.scheme, host + port, url.path, '', ''))
    except ValueError:
        return '[invalid URL]'


def origin(value):
    url = urlsplit(value)
    return url.scheme, url.hostname, url.port or (443 if url.scheme == 'https' else 80)


def validate_url(value, mode, local_origin=None, resolver=socket.getaddrinfo):
    try:
        url = urlsplit(value)
        port = url.port or (443 if url.scheme == 'https' else 80)
    except ValueError as error:
        raise CaptureBlocked('invalid_url') from error
    if url.scheme not in ('http', 'https') or not url.hostname:
        raise CaptureBlocked('http_only')
    if url.username or url.password or '\\' in value or '%' in url.hostname:
        raise CaptureBlocked('credentials_or_ambiguous_host')
    if re.search(r'(?i)(?:token|secret|password|credential|session|signature|api.?key|auth)[^=&]*=', url.query):
        raise CaptureBlocked('sensitive_query')
    if re.search(r'(?i)/(?:logout|delete|remove|purchase|checkout)(?:/|$)', url.path):
        raise CaptureBlocked('side_effect_navigation')
    host = url.hostname.rstrip('.').lower()
    if mode == 'local':
        if not local_origin or origin(value) != origin(local_origin):
            raise CaptureBlocked('outside_local_origin')
        try:
            address = ipaddress.ip_address(host)
        except ValueError as error:
            raise CaptureBlocked('numeric_loopback_required') from error
        if not address.is_loopback:
            raise CaptureBlocked('numeric_loopback_required')
        return url, str(address)
    if mode != 'public' or port not in (80, 443):
        raise CaptureBlocked('public_standard_ports_only')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise CaptureBlocked('private_host')
    try:
        addresses = [str(ipaddress.ip_address(host))]
    except ValueError:
        try:
            addresses = sorted({row[4][0] for row in resolver(host, port, type=socket.SOCK_STREAM)})
        except OSError as error:
            raise CaptureBlocked('dns_failed') from error
    if not addresses or not all(public_address(address) for address in addresses):
        raise CaptureBlocked('non_public_address')
    return url, addresses[0]


class GuardedHTTP:
    def __init__(self, mode, local_origin=None, *, max_requests=120,
                 per_resource_bytes=4 * 1024 * 1024, total_bytes=24 * 1024 * 1024,
                 seconds=90, resolver=socket.getaddrinfo, max_attempts=1):
        if (not 1 <= max_requests <= 500 or not 1 <= per_resource_bytes <= 8 * 1024 * 1024
                or not 1 <= total_bytes <= 64 * 1024 * 1024 or not 1 <= seconds <= 180):
            raise ValueError('Capture budget outside supported bounds')
        if mode not in ('public', 'local'):
            raise ValueError('Explicit capture mode required')
        if type(max_attempts) is not int or max_attempts not in (1, 2):
            raise ValueError('Use one attempt, or explicitly permit one transient retry')
        if mode == 'local':
            validate_url(local_origin or '', mode, local_origin)
        self.mode, self.local_origin, self.resolver = mode, local_origin, resolver
        self.max_requests, self.per_resource_bytes, self.total_bytes = max_requests, per_resource_bytes, total_bytes
        self.deadline = time.monotonic() + seconds
        self.requests = self.bytes = 0
        self.max_attempts, self.retries = max_attempts, 0

    def time_left(self):
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise CaptureBlocked('elapsed_budget')
        return left

    def remaining(self):
        return min(6, self.time_left())

    def fetch(self, value, method='GET'):
        for attempt in range(self.max_attempts):
            try:
                return self._fetch(value, method)
            except (TimeoutError, ConnectionResetError, ConnectionAbortedError, CaptureBlocked) as error:
                if isinstance(error, CaptureBlocked) and str(error) != 'dns_timeout':
                    raise
                if attempt + 1 == self.max_attempts:
                    raise
                self.time_left()
                self.retries += 1

    def _fetch(self, value, method):
        self.remaining()
        if method not in ('GET', 'HEAD'):
            raise CaptureBlocked('read_only_methods')
        self.requests += 1
        if self.requests > self.max_requests:
            raise CaptureBlocked('request_budget')
        def bounded_resolver(*args, **kwargs):
            replies = queue.Queue(maxsize=1)
            def resolve():
                try:
                    replies.put((True, self.resolver(*args, **kwargs)))
                except Exception as error:
                    replies.put((False, error))
            threading.Thread(target=resolve, daemon=True).start()
            try:
                success, result = replies.get(timeout=self.remaining())
            except queue.Empty as error:
                raise CaptureBlocked('dns_timeout') from error
            if not success:
                if isinstance(result, TimeoutError):
                    raise CaptureBlocked('dns_timeout') from result
                raise CaptureBlocked('dns_failed')
            return result
        url, address = validate_url(value, self.mode, self.local_origin, bounded_resolver)
        port = url.port or (443 if url.scheme == 'https' else 80)
        # Connect to the checked literal address, never resolve the hostname again.
        connection = http.client.HTTPConnection(url.hostname, port, timeout=self.remaining())
        try:
            connection.sock = socket.create_connection((address, port), timeout=self.remaining())
            if url.scheme == 'https':
                connection.sock = ssl.create_default_context().wrap_socket(connection.sock, server_hostname=url.hostname)
            transport_socket = connection.sock
            path = url.path or '/'
            if url.query:
                path += '?' + url.query
            connection.request(method, path, headers={'Accept-Encoding': 'identity', 'User-Agent': 'WebsiteReproduction/0.2', 'Connection': 'close'})
            response = connection.getresponse()
            mime = response.getheader('Content-Type', '').split(';')[0].lower()
            if mime == 'text/event-stream' or 'attachment' in response.getheader('Content-Disposition', '').lower():
                raise CaptureBlocked('stream_or_download')
            if response.getheader('Content-Encoding', 'identity').lower() not in ('', 'identity'):
                raise CaptureBlocked('encoded_body_unsupported')
            length = response.getheader('Content-Length')
            if length and (int(length) > self.per_resource_bytes or int(length) + self.bytes > self.total_bytes):
                raise CaptureBlocked('declared_byte_budget')
            chunks, received = [], 0
            while True:
                if response.isclosed():
                    break
                remaining = self.remaining()
                transport_socket.settimeout(remaining)
                chunk = response.read1(min(65536, self.per_resource_bytes - received + 1))
                if not chunk:
                    break
                received += len(chunk)
                self.bytes += len(chunk)
                if received > self.per_resource_bytes or self.bytes > self.total_bytes:
                    raise CaptureBlocked('streamed_byte_budget')
                chunks.append(chunk)
            # Preserve CSP and CORS. Never import response cookies or authentication.
            excluded = {'set-cookie', 'set-cookie2', 'www-authenticate', 'proxy-authenticate',
                        'connection', 'transfer-encoding', 'content-length', 'content-encoding'}
            headers = {k.lower(): v for k, v in response.getheaders() if k.lower() not in excluded}
            return response.status, headers, b''.join(chunks)
        finally:
            connection.close()
