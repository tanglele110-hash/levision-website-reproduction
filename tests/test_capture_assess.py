# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
import hashlib
import http.server
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from guarded_http import CaptureBlocked, GuardedHTTP, public_address, safe_url, validate_url
from capture import validate_plan
from assess import assess, load_capture


class TransportTests(unittest.TestCase):
    def test_reserved_and_alternate_addresses(self):
        for address in ['127.0.0.1', '0.0.0.0', '10.0.0.1', '100.64.0.1', '169.254.1.1',
                        '172.16.0.1', '192.168.0.1', '192.0.0.9', '198.18.0.1',
                        '224.0.0.1', '::1', 'fc00::1', 'fe80::1', '::ffff:8.8.8.8',
                        '2001:db8::1', '2002:0808:0808::1', '3fff::1']:
            with self.subTest(address=address):
                self.assertFalse(public_address(address))
        self.assertTrue(public_address('8.8.8.8'))
        self.assertTrue(public_address('2606:4700:4700::1111'))

    def test_credentials_ports_and_schemes(self):
        for url in ['file:///etc/passwd', 'http://user:pass@example.org', 'https://example.org:8080',
                    'http://localhost', 'https://example.org/?token=secret', 'https://example.org/logout']:
            with self.subTest(url=url), self.assertRaises(CaptureBlocked):
                validate_url(url, 'public')

    def test_mixed_dns_and_rebinding_rechecked(self):
        replies = iter([[(socket.AF_INET, 1, 6, '', ('8.8.8.8', 443))],
                        [(socket.AF_INET, 1, 6, '', ('127.0.0.1', 443))]])
        resolver = lambda *_args, **_kwargs: next(replies)
        self.assertEqual(validate_url('https://example.org', 'public', resolver=resolver)[1], '8.8.8.8')
        with self.assertRaises(CaptureBlocked):
            validate_url('https://example.org', 'public', resolver=resolver)
        with self.assertRaises(CaptureBlocked):
            validate_url('https://example.org', 'public', resolver=lambda *_a, **_k: [
                (2, 1, 6, '', ('8.8.8.8', 443)), (2, 1, 6, '', ('10.0.0.1', 443))])

    def test_local_origin_never_expands(self):
        base = 'http://127.0.0.1:8765'
        validate_url(base + '/index.html', 'local', base)
        for url in ['http://127.0.0.1:8766', 'http://localhost:8765', 'https://example.org']:
            with self.assertRaises(CaptureBlocked):
                validate_url(url, 'local', base)
        with self.assertRaises(CaptureBlocked):
            validate_url(base, 'public')

    def test_redacted_record_url(self):
        self.assertEqual(safe_url('https://user:pass@example.org/a?q=personal#secret'), 'https://example.org/a')

    def test_actual_http_limits_methods_redirect_and_cookies(self):
        observed = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                observed.append((self.command, self.path, self.headers.get('Cookie')))
                if self.path == '/redirect':
                    self.send_response(302); self.send_header('Location', 'http://127.0.0.1:1/private'); self.end_headers(); return
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream' if self.path == '/events' else 'text/plain')
                self.send_header('Set-Cookie', 'never=persist')
                if self.path == '/large': self.send_header('Content-Length', '10000')
                self.end_headers()
                if self.path != '/large': self.wfile.write(b'x' * (200 if self.path == '/chunked' else 5))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            guard = GuardedHTTP('local', base, per_resource_bytes=100, total_bytes=300)
            status, headers, body = guard.fetch(base + '/')
            self.assertEqual((status, body), (200, b'xxxxx'))
            self.assertNotIn('set-cookie', headers)
            with self.assertRaises(CaptureBlocked): guard.fetch(base + '/', 'POST')
            self.assertEqual(len(observed), 1)
            self.assertEqual(guard.fetch(base + '/redirect')[0], 302)
            with self.assertRaises(CaptureBlocked): guard.fetch('http://127.0.0.1:1/private')
            for path in ['/events', '/large', '/chunked']:
                with self.subTest(path=path), self.assertRaises(CaptureBlocked): guard.fetch(base + path)
            self.assertTrue(all(row[2] is None for row in observed))
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)

    def test_expired_and_request_budgets(self):
        guard = GuardedHTTP('local', 'http://127.0.0.1:8765', max_requests=1)
        guard.requests = 1
        with self.assertRaisesRegex(CaptureBlocked, 'request_budget'): guard.fetch('http://127.0.0.1:8765')
        guard.deadline = 0
        with self.assertRaisesRegex(CaptureBlocked, 'elapsed_budget'): guard.fetch('http://127.0.0.1:8765')


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='website-assess-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.captures = []
        for name in ['reference', 'candidate']:
            folder = self.root / name; folder.mkdir()
            image = folder / 'view.png'; Image.new('RGBA', (8, 8), 'white').save(image)
            report = {'schemaVersion':1, 'files':[{'path':'view.png','bytes':image.stat().st_size,'sha256':hashlib.sha256(image.read_bytes()).hexdigest()}],
                      'cases':[{'id':'phone','status':'captured','viewport':{'width':390,'height':844},'motion':'no-preference',
                                'scenarioSha256':'same-fixture-contract',
                                'probes':{'active':{'status':'observed','value':True}},'runtime':{'jsErrors':0,'networkIssues':0,'horizontalOverflow':False,'fullPage':True,'scroll':{'x':0,'y':0}},'screenshot':{'path':'view.png'}}]}
            path=folder/'capture.json';path.write_text(json.dumps(report),encoding='utf-8')
            self.captures.append(load_capture(path))
        self.scope={'schemaVersion':1,'requirements':[{'id':'visual','kind':'visual','case':'phone','maxDifferentPixelRatio':0},
            {'id':'interaction','kind':'probe','case':'phone','probe':'active','referenceExpected':True}]}

    def test_paired_success_is_not_user_acceptance(self):
        report=assess(self.scope,*self.captures)
        self.assertEqual(report['status'],'ready_for_user_review')
        self.assertEqual(report['userAcceptance'],'not_assessed')

    def test_behavior_failure_not_hidden_by_perfect_pixels(self):
        self.captures[1]['cases']['phone']['probes']['active']['value']=False
        report=assess(self.scope,*self.captures)
        self.assertEqual(report['status'],'needs_work')
        self.assertEqual(report['counts'],{'pass':1,'fail':1})

    def test_missing_case_is_unverified(self):
        self.captures[1]['cases'].clear()
        report=assess(self.scope,*self.captures)
        self.assertEqual(report['counts'],{'unverified':2})

    def test_inactive_reference_cannot_prove_suppression(self):
        for capture in self.captures: capture['cases']['phone']['probes']['active']['value']=False
        self.assertEqual(assess(self.scope,*self.captures)['checks'][1]['reason'],'reference_baseline_not_established')

    def test_different_viewports_fail(self):
        self.captures[1]['cases']['phone']['viewport']['width']=400
        self.assertEqual(assess(self.scope,*self.captures)['counts'],{'fail':2})

    def test_visual_tolerance_must_be_explicit(self):
        self.scope['requirements'][0].pop('maxDifferentPixelRatio')
        self.assertEqual(assess(self.scope,*self.captures)['checks'][0]['status'],'unverified')

    def test_different_actions_cannot_pass_identical_pixels(self):
        self.captures[1]['cases']['phone']['scenarioSha256']='different-actions'
        self.assertEqual(assess(self.scope,*self.captures)['counts'],{'fail':2})

    def test_truncated_capture_is_not_full_visual_acceptance(self):
        self.captures[1]['cases']['phone']['runtime']['fullPage']=False
        self.assertEqual(assess(self.scope,*self.captures)['checks'][0]['status'],'unverified')

    def test_changed_and_escaped_evidence_rejected(self):
        capture=self.root/'candidate/capture.json'
        image=self.root/'candidate/view.png';image.write_bytes(image.read_bytes()+b'changed')
        with self.assertRaises(ValueError):load_capture(capture)
        data=json.loads(capture.read_text());data['files'][0]['path']='../reference/view.png'
        capture.write_text(json.dumps(data))
        with self.assertRaises(ValueError):load_capture(capture)

    def test_duplicate_requirements_rejected(self):
        self.scope['requirements'].append(self.scope['requirements'][0])
        with self.assertRaises(ValueError):assess(self.scope,*self.captures)

    def test_manual_missing_evidence_cannot_pass(self):
        self.scope['requirements'].append({'id':'audio','kind':'manual'})
        self.assertEqual(assess(self.scope,*self.captures)['checks'][-1]['status'],'unverified')
        with self.assertRaises(ValueError):assess(self.scope,*self.captures,manual={'checks':{'audio':{'status':'pass','reason':'heard','evidence':[]}},'_root':self.root})

    def test_capture_plan_rejects_arbitrary_code_and_unsafe_actions(self):
        plan={'schemaVersion':1,'url':'https://example.org','cases':[{'id':'desktop','viewport':{'width':1440,'height':900},'actions':[{'type':'evaluate','code':'danger'}]}]}
        with self.assertRaises(ValueError):validate_plan(plan)
        plan['cases'][0]['actions']=[{'type':'click','selector':'button'}]
        with self.assertRaises(ValueError):validate_plan(plan)


if __name__=='__main__':unittest.main()
