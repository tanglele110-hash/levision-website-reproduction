# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Explicit authenticated public DNS, without changing destination validation or host DNS."""
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from urllib.parse import urlencode

from guarded_http import CaptureBlocked, public_address

PROVIDER_HOST = 'cloudflare-dns.com'
PROVIDER_ADDRESS = '1.1.1.1'


def parse_answer(payload, hostname, record):
    if not isinstance(payload, dict) or payload.get('Status') != 0 or payload.get('TC') is True:
        raise CaptureBlocked('public_dns_invalid_status')
    question = payload.get('Question', [])
    if len(question) != 1 or question[0].get('name', '').rstrip('.').lower() != hostname or question[0].get('type') != record:
        raise CaptureBlocked('public_dns_question_mismatch')
    addresses, ttls = [], []
    for row in payload.get('Answer', []):
        if row.get('type') not in (1, 28):
            continue
        try:
            value = str(ipaddress.ip_address(row['data']))
        except (ValueError, KeyError) as error:
            raise CaptureBlocked('public_dns_invalid_address') from error
        if not public_address(value):
            raise CaptureBlocked('public_dns_non_public_answer')
        addresses.append(value)
        ttl = row.get('TTL', 0)
        ttls.append(max(0, min(60, ttl)) if type(ttl) is int else 0)
    return addresses, min(ttls, default=0)


class CloudflareResolver:
    """A+AAAA, short TTL cache, fixed TLS-authenticated bootstrap, no proxy/fallback."""
    def __init__(self, remaining, *, query=None):
        self.remaining = remaining
        self.query = query or self._query
        self.cache = {}
        self.stats = {'mode': 'cloudflare', 'queries': 0, 'receivedBytes': 0, 'cacheHits': 0,
                      'maxQueries': 32, 'perResponseBytes': 65536, 'totalBytes': 524288}

    def _query(self, hostname, record):
        self.remaining()
        self.stats['queries'] += 1
        if self.stats['queries'] > self.stats['maxQueries']:
            raise CaptureBlocked('public_dns_query_budget')
        connection = http.client.HTTPConnection(PROVIDER_HOST, 443, timeout=self.remaining())
        try:
            connection.sock = socket.create_connection((PROVIDER_ADDRESS, 443), timeout=self.remaining())
            connection.sock = ssl.create_default_context().wrap_socket(connection.sock, server_hostname=PROVIDER_HOST)
            transport = connection.sock
            connection.request('GET', '/dns-query?' + urlencode({'name': hostname, 'type': record}),
                               headers={'Accept': 'application/dns-json', 'Accept-Encoding': 'identity', 'Connection': 'close'})
            response = connection.getresponse()
            if response.status != 200 or response.getheader('Content-Type', '').split(';')[0] not in ('application/dns-json', 'application/json'):
                raise CaptureBlocked('public_dns_response_rejected')
            if response.getheader('Content-Encoding', 'identity').lower() not in ('', 'identity'):
                raise CaptureBlocked('public_dns_encoding_rejected')
            declared = response.getheader('Content-Length')
            if declared and int(declared) > self.stats['perResponseBytes']:
                raise CaptureBlocked('public_dns_byte_budget')
            data = bytearray()
            while not response.isclosed():
                transport.settimeout(self.remaining())
                chunk = response.read1(min(8192, self.stats['perResponseBytes'] - len(data) + 1))
                if not chunk:
                    break
                data.extend(chunk)
                self.stats['receivedBytes'] += len(chunk)
                if len(data) > self.stats['perResponseBytes'] or self.stats['receivedBytes'] > self.stats['totalBytes']:
                    raise CaptureBlocked('public_dns_byte_budget')
            return json.loads(data)
        finally:
            connection.close()

    def __call__(self, hostname, port, **_):
        try:
            host = hostname.rstrip('.').encode('idna').decode('ascii').lower()
        except UnicodeError as error:
            raise CaptureBlocked('public_dns_hostname_rejected') from error
        if (len(host) > 253 or '.' not in host or host.endswith(('.localhost', '.local', '.internal'))
                or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in host.split('.'))):
            raise CaptureBlocked('public_dns_hostname_rejected')
        self.remaining()
        cached = self.cache.get(host)
        if cached and time.monotonic() < cached[0]:
            addresses = cached[1]
            self.stats['cacheHits'] += 1
        else:
            addresses, ttls = [], []
            for record in (1, 28):
                found, ttl = parse_answer(self.query(host, record), host, record)
                addresses.extend(found)
                if found:
                    ttls.append(ttl)
            if not addresses:
                raise CaptureBlocked('public_dns_no_addresses')
            addresses = sorted(set(addresses))
            self.cache[host] = (time.monotonic() + min(ttls, default=0), addresses)
        # GuardedHTTP still validates every returned address and pins the actual connection.
        return [(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, port)) for address in addresses]
