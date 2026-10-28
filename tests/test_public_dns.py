# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
import socket,ssl,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from guarded_http import GuardedHTTP,CaptureBlocked,validate_url
from public_dns import CloudflareResolver,parse_answer


def response(host,record,addresses):
    return {'Status':0,'Question':[{'name':host+'.','type':record}],
            'Answer':[{'type':record,'data':address,'TTL':30} for address in addresses]}


class PublicDnsTests(unittest.TestCase):
    def test_public_ipv4_ipv6_and_short_cache(self):
        queries=[]
        def query(host,record):
            queries.append(record)
            return response(host,record,['8.8.8.8'] if record==1 else ['2606:4700:4700::1111'])
        resolver=CloudflareResolver(lambda:6,query=query)
        url,address=validate_url('https://example.org/','public',resolver=resolver)
        self.assertTrue(address);resolver('example.org',443)
        self.assertEqual(queries,[1,28]);self.assertEqual(resolver.stats['cacheHits'],1)
        resolver.cache['example.org']=(time.monotonic()-1,['8.8.8.8'])
        resolver('example.org',443);self.assertEqual(queries,[1,28,1,28])

    def test_mixed_private_reserved_and_mapped_answers_fail(self):
        for address in ['127.0.0.1','198.18.1.2','169.254.169.254','10.0.0.1','::ffff:8.8.8.8','fc00::1']:
            with self.subTest(address=address),self.assertRaises(CaptureBlocked):
                parse_answer(response('example.org',1,['8.8.8.8',address]),'example.org',1)

    def test_question_status_and_truncation_fail_closed(self):
        good=response('example.org',1,['8.8.8.8'])
        for data in [dict(good,Status=3),dict(good,TC=True),dict(good,Question=[]),response('different.org',1,['8.8.8.8'])]:
            with self.assertRaises(CaptureBlocked):parse_answer(data,'example.org',1)

    def test_dns_failure_never_falls_back_to_system_or_partial_answer(self):
        def query(host,record):
            if record==28:raise ssl.SSLCertVerificationError('untrusted fixture certificate')
            return response(host,record,['8.8.8.8'])
        resolver=CloudflareResolver(lambda:6,query=query)
        with patch('socket.getaddrinfo',side_effect=AssertionError('No fallback allowed')):
            with self.assertRaises(ssl.SSLCertVerificationError):resolver('example.org',443)

    def test_local_and_ambiguous_host_rejected(self):
        resolver=CloudflareResolver(lambda:6,query=lambda *_:self.fail('query must not run'))
        for host in ['localhost','test.local','test.internal','test..org','bad_name.org','singlelabel']:
            with self.subTest(host=host),self.assertRaises(CaptureBlocked):resolver(host,443)

    def test_public_literal_still_rejected_before_dns(self):
        resolver=CloudflareResolver(lambda:6,query=lambda *_:self.fail('query must not run'))
        with self.assertRaises(CaptureBlocked):validate_url('https://127.0.0.1/','public',resolver=resolver)

    def test_dns_query_budget_prevents_connection(self):
        resolver=CloudflareResolver(lambda:6);resolver.stats['queries']=32
        with patch('socket.create_connection',side_effect=AssertionError('No connection allowed')):
            with self.assertRaisesRegex(CaptureBlocked,'query_budget'):resolver._query('example.org',1)

    def test_socket_cap_separate_from_unchanged_run_deadline(self):
        guard=GuardedHTTP('public',seconds=90)
        self.assertLessEqual(guard.remaining(),6);self.assertGreater(guard.time_left(),80)
        guard.deadline=0
        with self.assertRaises(CaptureBlocked):guard.time_left()
        with self.assertRaises(CaptureBlocked):guard.remaining()

    def test_transient_retry_is_opt_in_and_bounded(self):
        for attempts in [1,2]:
            guard=GuardedHTTP('public',max_attempts=attempts)
            deadline=guard.deadline
            with patch.object(guard,'_fetch',side_effect=TimeoutError) as fetch:
                with self.assertRaises(TimeoutError):guard.fetch('https://example.org/')
                self.assertEqual(fetch.call_count,attempts)
            self.assertEqual(guard.retries,attempts-1);self.assertEqual(guard.deadline,deadline)

    def test_tls_policy_and_elapsed_errors_are_never_retried(self):
        for error in [ssl.SSLCertVerificationError('fixture'),CaptureBlocked('non_public_address'),CaptureBlocked('elapsed_budget')]:
            guard=GuardedHTTP('public',max_attempts=2)
            with patch.object(guard,'_fetch',side_effect=error) as fetch:
                with self.assertRaises(type(error)):guard.fetch('https://example.org/')
                self.assertEqual(fetch.call_count,1)

    def test_transient_retry_cannot_exceed_request_budget(self):
        guard=GuardedHTTP('public',max_attempts=2,max_requests=1)
        with patch('socket.create_connection',side_effect=TimeoutError) as connection:
            with self.assertRaisesRegex(CaptureBlocked,'request_budget'):guard.fetch('https://8.8.8.8/')
            self.assertEqual(connection.call_count,1)

    def test_dns_timeout_retry_still_revalidates_and_keeps_deadline(self):
        guard=GuardedHTTP('public',max_attempts=2)
        deadline=guard.deadline
        with patch.object(guard,'_fetch',side_effect=[CaptureBlocked('dns_timeout'),CaptureBlocked('non_public_address')]) as fetch:
            with self.assertRaisesRegex(CaptureBlocked,'non_public_address'):guard.fetch('https://example.org/')
            self.assertEqual(fetch.call_count,2)
        self.assertEqual(guard.retries,1);self.assertEqual(guard.deadline,deadline)


if __name__=='__main__':unittest.main()
