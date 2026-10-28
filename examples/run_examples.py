# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Run the original examples locally; write all observations outside the Skill."""
import argparse
import functools
import http.server
import json
import sys
import threading
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'scripts'))
from capture import capture
from assess import assess, load_capture, digest


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.allowed_path():
            super().do_GET()

    def do_HEAD(self):
        if self.allowed_path():
            super().do_HEAD()

    def allowed_path(self):
        requested = (ROOT / unquote(urlsplit(self.path).path).lstrip('/')).resolve()
        if not requested.is_relative_to(ROOT) or any(part.startswith('.') for part in requested.relative_to(ROOT).parts):
            self.send_error(403)
            return False
        return True

    def list_directory(self, _):
        self.send_error(403)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--only', choices=('responsive', 'interaction', 'canvas'))
    parser.add_argument('--browser-executable')
    args = parser.parse_args()
    output = args.out.resolve()
    if output.is_relative_to(ROOT.parent):
        parser.error('Output must be outside the Skill folder')
    output.mkdir(parents=True, exist_ok=False)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    summaries = []
    try:
        for name in ([args.only] if args.only else ['responsive', 'interaction', 'canvas']):
            directory = output / name
            directory.mkdir()
            template = json.loads((ROOT / name / 'capture-plan.json').read_text(encoding='utf-8-sig'))
            for side in ('reference', 'replica'):
                plan = dict(template, url=origin + '/' + name + '/' + side + '/')
                print(f'{name}: capturing {side}, {len(plan["cases"])} cases', flush=True)
                capture(plan, directory / side, mode='local', local_origin=origin, executable=args.browser_executable)
            scope_path = ROOT / name / 'scope.json'
            report = assess(json.loads(scope_path.read_text(encoding='utf-8-sig')),
                            load_capture(directory / 'reference/capture.json'), load_capture(directory / 'replica/capture.json'))
            report['scopeSha256'] = digest(scope_path)
            (directory / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            summary = {'example': name, 'status': report['status'], 'counts': report['counts']}
            summaries.append(summary)
            print(json.dumps(summary), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    (output / 'SUMMARY.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    return 0 if all(row['status'] == 'ready_for_user_review' for row in summaries) else 1


if __name__ == '__main__':
    sys.exit(main())
