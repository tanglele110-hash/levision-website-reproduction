# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Prove real layout and behavior regressions are detected; mutate only output copies."""
import argparse
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from capture import capture
from assess import assess,load_capture,digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--browser-executable')
    args=parser.parse_args()
    output=args.out.resolve()
    if output.is_relative_to(ROOT):parser.error('Output must be outside the Skill')
    output.mkdir(parents=True,exist_ok=False)
    source=(ROOT/'examples/interaction/reference/index.html').read_text(encoding='utf-8')
    marker="$('#menu').onclick=()=>{"
    assert marker in source and 'h1{font-size:56px' in source
    fixtures=output/'fixtures';fixtures.mkdir()
    versions={'reference':source,'layout':source.replace('h1{font-size:56px','h1{font-size:72px'),
              'behavior':source.replace(marker,marker+'return;')}
    for name,text in versions.items():(fixtures/(name+'.html')).write_text(text,encoding='utf-8')
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*_):pass
        def list_directory(self,_):self.send_error(403);return None
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(fixtures)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    origin=f'http://127.0.0.1:{server.server_port}'
    template=json.loads((ROOT/'examples/interaction/capture-plan.json').read_text(encoding='utf-8'))
    template['cases']=[case for case in template['cases'] if case['id'] in ('desktop-default','desktop-menu')]
    scope=json.loads((ROOT/'examples/interaction/scope.json').read_text(encoding='utf-8'))
    scope['requirements']=[row for row in scope['requirements'] if row.get('case') in ('desktop-default','desktop-menu')]
    (output/'scope.json').write_text(json.dumps(scope,indent=2),encoding='utf-8')
    summaries=[]
    try:
        for name in versions:
            print('capturing negative fixture: '+name,flush=True)
            capture(dict(template,url=origin+'/'+name+'.html'),output/name,mode='local',local_origin=origin,executable=args.browser_executable)
        reference=load_capture(output/'reference/capture.json')
        for name,expected_kind in [('layout','visual'),('behavior','probe')]:
            report=assess(scope,reference,load_capture(output/name/'capture.json'))
            assert report['status']=='needs_work',report
            assert any(row['kind']==expected_kind and row['status']=='fail' for row in report['checks']),report
            assert not any(row['status']=='unverified' for row in report['checks']),report
            report['scopeSha256']=digest(output/'scope.json')
            (output/(name+'-acceptance.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
            summaries.append({'fixture':name,'expectedFailureDetected':expected_kind,'counts':report['counts']})
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
    (output/'RESULT.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    print(json.dumps(summaries))


if __name__=='__main__':main()
