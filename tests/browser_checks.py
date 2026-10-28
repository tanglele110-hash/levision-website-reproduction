# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Opt-in browser/transport integration checks; no external services or user data."""
import argparse
import http.server
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from capture import capture
from validate_pack import validate

PAGE = b'''<!doctype html><html><body><h1>Capture boundary fixture</h1><output id="result">waiting</output>
<img src="/missing.png" alt="Intentionally unavailable"><script>
(async()=>{
 const observed={};
 for(const name of ['WebSocket','EventSource','RTCPeerConnection']) {
  try {new globalThis[name](name==='WebSocket'?location.origin.replace('http','ws')+'/socket':'/events');observed[name]='constructed'}
  catch {observed[name]='blocked'}
 }
 document.cookie='fixture=must-not-be-forwarded';
 await Promise.all([navigator.serviceWorker.register('/sw.js').then(async()=>observed.serviceWorker=(await navigator.serviceWorker.getRegistrations()).length===0?'blocked':'unexpected',()=>observed.serviceWorker='blocked'), ...['/write','/redirect','/stream','/download','/oversize','/cookie'].map(async path=>{
  try {const r=await fetch(path,{method:path==='/write'?'POST':'GET'});observed[path]=await r.text()}
  catch {observed[path]='blocked'}
 })]);
 window.open('/popup');
 document.querySelector('#result').textContent=JSON.stringify(observed);
 document.body.dataset.ready='true';
})();</script></body></html>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--browser-executable')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    received=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def do_POST(self):
            received.append(('POST',self.path));self.send_response(500);self.end_headers()
        def do_GET(self):
            received.append(('GET',self.path))
            if self.path=='/redirect':
                self.send_response(302);self.send_header('Location','http://127.0.0.1:1/private');self.end_headers();return
            body=PAGE if self.path=='/' else b'fixture'
            if self.path=='/cookie':body=b'cookie-leaked' if self.headers.get('Cookie') else b'no-cookie'
            self.send_response(404 if self.path=='/missing.png' else 200)
            self.send_header('Content-Type','text/event-stream' if self.path=='/stream' else 'text/html')
            self.send_header('Set-Cookie','response=must-not-be-forwarded')
            if self.path=='/download':self.send_header('Content-Disposition','attachment; filename="blocked.txt"')
            self.send_header('Content-Length',str(999999 if self.path=='/oversize' else len(body)))
            self.end_headers()
            if self.path!='/oversize':self.wfile.write(body)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    origin=f'http://127.0.0.1:{server.server_port}'
    plan={'schemaVersion':1,'url':origin+'/','budget':{'per_resource_bytes':8000,'seconds':60},'cases':[
        {'id':'guards','viewport':{'width':800,'height':600,'dpr':1},'ready':'body[data-ready="true"]',
         'actions':[{'type':'wait','ms':150}],'probes':[{'id':'results','kind':'text','selector':'#result'}]}]}
    try:
        report=capture(plan,args.out/'local',mode='local',local_origin=origin,executable=args.browser_executable)
        case=report['cases'][0]
        assert case['status']=='captured',case
        observed=json.loads(case['probes']['results']['value'])
        assert all(observed[key]=='blocked' for key in ['EventSource','RTCPeerConnection','/write','/redirect','/stream','/download','/oversize']),observed
        assert observed['WebSocket']=='blocked' or any(row['reason']=='websocket_blocked' for row in report['networkEvents']),observed
        assert observed['/cookie']=='no-cookie',observed
        assert observed['serviceWorker']=='blocked',observed
        assert not any(method=='POST' or path in ('/popup','/private','/socket','/sw.js') for method,path in received),received
        assert any(row['status']=='missing' for row in report['assets']),report['assets']
        pack=validate(args.out/'local/DESIGN.md',args.out/'local/manifest.json')
        assert pack['valid'],pack
        before=len(received)
        public=capture(dict(plan,url='http://127.0.0.1/'),args.out/'public-reject',mode='public',executable=args.browser_executable)
        assert public['cases'][0]['status']=='failed',public['cases']
        assert len(received)==before,'public mode reached loopback'
        assert any(row['reason']=='non_public_address' for row in public['networkEvents']),public['networkEvents']
        summary={'status':'pass','checks':['GET-only','redirect revalidation','exact local origin','public rejects loopback',
            'WebSocket blocked','EventSource blocked','WebRTC blocked','SSE blocked','download blocked','response byte cap',
            'cookies not forwarded','popup not fetched','Service Worker blocked','missing assets paired with omissions'],
            'observed':observed,'received':received}
        (args.out/'RESULT.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(json.dumps({'status':'pass','checks':len(summary['checks'])}))
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':main()
