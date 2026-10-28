# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Capture explicit cases in fresh Chromium contexts through guarded HTTP."""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from guarded_http import CaptureBlocked, GuardedHTTP, safe_url

IDENTIFIER = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
ACTIONS = {'click', 'tap', 'hover', 'fill', 'press', 'scroll', 'wait'}
PROBES = {'text', 'visible', 'count', 'attribute', 'value', 'geometry', 'imageLoaded', 'canvasChanging'}
SNAPSHOT = """() => ({
 title: document.title, viewport: {width: innerWidth, height: innerHeight, dpr: devicePixelRatio},
 scroll: {x: scrollX, y: scrollY}, document: {width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight},
 reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
 fonts: document.fonts.status,
 elements: [...document.querySelectorAll('body *')].filter(e => !['SCRIPT','STYLE','NOSCRIPT'].includes(e.tagName)).slice(0,300).map(e => {
   const r=e.getBoundingClientRect(), s=getComputedStyle(e);
   return {tag:e.tagName,id:e.id,role:e.getAttribute('role'),text:(e.children.length ? '' : e.textContent).slice(0,600),
    rect:{x:r.x,y:r.y,width:r.width,height:r.height}, computed:{display:s.display,color:s.color,background:s.backgroundColor,
    fontFamily:s.fontFamily,fontSize:s.fontSize,fontWeight:s.fontWeight,lineHeight:s.lineHeight,gap:s.gap,padding:s.padding,
    transform:s.transform,transition:s.transition,animation:s.animation}};
 }),
 elementLimitReached: document.querySelectorAll('body *').length > 300,
 cssDeclarations: [...document.styleSheets].slice(0,30).map(s => {try {return [...s.cssRules].slice(0,200).map(r=>r.cssText).join('\\n').slice(0,20000)}catch{return '[cross-origin stylesheet; see captured asset]'}})
})"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def scenario_signature(case):
    # Selectors may differ between implementations; actions and probe meanings may not.
    contract = {
        'actions': [{k: v for k, v in item.items() if k not in ('selector', 'safe')} for item in case.get('actions', [])],
        'probes': [{k: v for k, v in item.items() if k != 'selector'} for item in case.get('probes', [])],
    }
    return sha(json.dumps(contract, sort_keys=True, ensure_ascii=False).encode())


def validate_plan(plan):
    if plan.get('schemaVersion') != 1 or not isinstance(plan.get('url'), str):
        raise ValueError('Capture plan requires schemaVersion=1 and url')
    cases = plan.get('cases')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 32:
        raise ValueError('Use 1..32 explicit capture cases')
    ids = set()
    for case in cases:
        if not IDENTIFIER.fullmatch(case.get('id', '')) or case['id'] in ids:
            raise ValueError('Case ids must be unique portable identifiers')
        ids.add(case['id'])
        view = case.get('viewport', {})
        if (type(view.get('width')) is not int or type(view.get('height')) is not int
                or not 320 <= view['width'] <= 2560 or not 320 <= view['height'] <= 1600
                or view.get('dpr', 1) not in (1, 2)):
            raise ValueError('Unsupported viewport or DPR')
        if case.get('motion', 'no-preference') not in ('reduce', 'no-preference'):
            raise ValueError('Unsupported motion preference')
        if len(case.get('actions', [])) > 20 or len(case.get('probes', [])) > 30:
            raise ValueError('Case action/probe budget exceeded')
        probe_ids = set()
        for action in case.get('actions', []):
            if action.get('type') not in ACTIONS:
                raise ValueError('Unsupported action; arbitrary code is not accepted')
            if action['type'] in ('click', 'tap', 'fill', 'press') and action.get('safe') is not True:
                raise ValueError('Active inputs require safe=true after reviewing their actual purpose')
            if action['type'] == 'wait' and not 0 <= action.get('ms', 0) <= 1500:
                raise ValueError('Wait budget exceeded')
        for probe in case.get('probes', []):
            if not IDENTIFIER.fullmatch(probe.get('id', '')) or probe['id'] in probe_ids or probe.get('kind') not in PROBES:
                raise ValueError('Invalid/duplicate probe')
            if probe.get('kind') == 'attribute' and not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]*', probe.get('name', '')):
                raise ValueError('Attribute name required')
            probe_ids.add(probe['id'])
    return plan


def unique(page, selector):
    if not isinstance(selector, str) or not selector or len(selector) > 500:
        raise ValueError('A bounded CSS selector is required')
    locator = page.locator('css=' + selector)
    if locator.count() != 1:
        raise ValueError('Selector must identify exactly one element')
    return locator


def action(page, item):
    kind = item['type']
    if kind == 'wait':
        page.wait_for_timeout(item.get('ms', 100))
    elif kind == 'scroll':
        page.mouse.wheel(0, max(-1600, min(1600, int(item.get('y', 600)))))
        page.wait_for_timeout(120)
    else:
        target = unique(page, item.get('selector'))
        if not target.is_visible() or not target.is_enabled():
            raise ValueError('Action target must be visible and enabled')
        if kind == 'press':
            if item.get('key') not in ('Tab', 'Enter', 'Space', 'Escape', 'ArrowLeft', 'ArrowRight'):
                raise ValueError('Unsupported key')
            target.press(item['key'])
        elif kind == 'fill':
            if target.evaluate('(e) => e.type === "password" || e.type === "file"'):
                raise ValueError('Sensitive/file inputs are excluded')
            target.fill(str(item.get('value', ''))[:200])
        else:
            getattr(target, kind)()


def probe(page, item):
    kind = item['kind']
    if kind == 'count':
        return page.locator('css=' + item['selector']).count()
    target = unique(page, item['selector'])
    if kind == 'visible':
        return target.is_visible()
    if kind == 'text':
        return target.inner_text()[:2000]
    if kind == 'attribute':
        return target.get_attribute(item['name'])
    if kind == 'value':
        if target.evaluate('(e) => e.type === "password" || e.type === "file"'):
            raise ValueError('Sensitive inputs are excluded')
        return target.input_value()[:200]
    if kind == 'geometry':
        return target.bounding_box()
    if kind == 'imageLoaded':
        return target.evaluate('(e) => e instanceof HTMLImageElement && e.complete && e.naturalWidth > 0')
    if kind == 'canvasChanging':
        first = target.evaluate('(e) => {if (!(e instanceof HTMLCanvasElement)) throw Error("canvas required"); return e.toDataURL()}')
        page.wait_for_timeout(180)
        second = target.evaluate('(e) => e.toDataURL()')
        return first != second
    raise ValueError('Unsupported probe')


def capture(plan, output, *, mode, local_origin=None, executable=None, dns_mode='system'):
    from playwright.sync_api import sync_playwright
    validate_plan(plan)
    guard = GuardedHTTP(mode, local_origin, **plan.get('budget', {}))
    if dns_mode not in ('system', 'cloudflare') or (mode != 'public' and dns_mode != 'system'):
        raise ValueError('Public DNS selection applies only to public capture')
    resolver = None
    if dns_mode == 'cloudflare':
        from public_dns import CloudflareResolver
        resolver = CloudflareResolver(guard.remaining)
        guard.resolver = resolver
    # URL/DNS checks happen inside the bounded transport, including initial navigation.
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'assets').mkdir()
    cases, assets, missing, events = [], {}, {}, []
    files = []

    def save(name, data):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        row = {'path': name, 'bytes': len(data), 'sha256': sha(data)}
        files.append(row)
        return row

    with sync_playwright() as runtime:
        options = {'headless': True, 'chromium_sandbox': True}
        if executable:
            options['executable_path'] = executable
        browser = runtime.chromium.launch(**options)
        try:
            for case in plan['cases']:
                result = {'id': case['id'], 'status': 'failed', 'viewport': case['viewport'],
                          'motion': case.get('motion', 'no-preference'), 'scenarioSha256': scenario_signature(case),
                          'probes': {}, 'actions': [], 'runtime': {}}
                cases.append(result)
                context = None
                case_events = []
                js_errors = []
                try:
                    guard.remaining()
                    view = case['viewport']
                    context = browser.new_context(viewport={k: view[k] for k in ('width', 'height')},
                        device_scale_factor=view.get('dpr', 1), has_touch=view.get('touch', False),
                        reduced_motion=result['motion'], service_workers='block', accept_downloads=False,
                        permissions=[], ignore_https_errors=False, locale='en-US', color_scheme='light')
                    context.set_default_timeout(min(5000, guard.remaining() * 1000))
                    # Prevent browser APIs that bypass HTTP interception. The transport remains the authority.
                    context.add_init_script("""for (const name of ['WebSocket','EventSource','RTCPeerConnection','webkitRTCPeerConnection']) {
                      Object.defineProperty(globalThis,name,{value:class {constructor(){throw Error('Capture policy blocks '+name)}},configurable:false});
                    }""")
                    page = context.new_page()
                    page.on('pageerror', lambda _: js_errors.append('page_error'))
                    page.on('console', lambda msg: js_errors.append('console_error') if msg.type == 'error' else None)
                    page.on('dialog', lambda dialog: dialog.dismiss())
                    page.on('download', lambda download: download.cancel())
                    context.on('page', lambda popup: popup.close() if popup != page else None)
                    # Routing without connect_to_server never opens an upstream socket.
                    # Avoid close() inside the sync callback: Chromium/Playwright can deadlock there.
                    context.route_web_socket('**/*', lambda _: case_events.append({'reason': 'websocket_blocked', 'url': '[websocket]'}))

                    def route_request(route):
                        request = route.request
                        def record_issue(reason):
                            source = safe_url(request.url)
                            case_events.append({'reason': reason, 'url': source})
                            if request.resource_type in ('document', 'script', 'stylesheet', 'image', 'font', 'media'):
                                key = sha(source.encode())[:16]
                                missing[key] = {'id': 'missing-' + key, 'status': 'missing', 'source': source,
                                    'reason': reason, 'usage': request.resource_type,
                                    'impact': 'This response was unavailable in at least one captured case; related fidelity remains unverified.',
                                    'recovery': 'Obtain an authorized local copy or retry within the same capture safeguards, then reassess affected cases.'}
                        try:
                            if request.resource_type in ('eventsource', 'websocket'):
                                raise CaptureBlocked('streaming_protocol')
                            if request.is_navigation_request() and request.frame.page != page:
                                raise CaptureBlocked('popup_navigation')
                            status, headers, body = guard.fetch(request.url, request.method)
                            mime = headers.get('content-type', '').split(';')[0]
                            if status >= 400:
                                record_issue('http_' + str(status))
                            if status == 200 and body and request.resource_type in ('document', 'script', 'stylesheet', 'image', 'font', 'media'):
                                digest = sha(body)
                                if digest not in assets:
                                    file = save('assets/' + digest + '.bin', body)
                                    assets[digest] = {**file, 'id': 'asset-' + digest[:16], 'status': 'obtained',
                                        'source': safe_url(request.url), 'mime': mime or 'application/octet-stream',
                                        'usage': request.resource_type, 'license': plan.get('assetLicense', 'unverified')}
                            route.fulfill(status=status, headers=headers, body=body)
                        except Exception as error:
                            reason = str(error) if isinstance(error, CaptureBlocked) else type(error).__name__
                            record_issue(reason)
                            route.abort('blockedbyclient')

                    context.route('**/*', route_request)
                    result['phase'] = 'document_navigation'
                    response = page.goto(plan['url'], wait_until='commit', timeout=min(15000, guard.time_left() * 1000))
                    if response is None or not 200 <= response.status < 300:
                        raise ValueError('Initial page did not return a successful document')
                    result['phase'] = 'page_loading'
                    page.wait_for_load_state('load', timeout=guard.time_left() * 1000)
                    result['phase'] = 'readiness'
                    if case.get('ready'):
                        selector = case['ready']
                        if not isinstance(selector, str) or len(selector) > 500:
                            raise ValueError('A bounded readiness selector is required')
                        page.locator('css=' + selector).wait_for(state='visible', timeout=guard.time_left() * 1000)
                        unique(page, selector)
                    page.wait_for_function('document.fonts.status === "loaded"', timeout=min(4000, guard.remaining() * 1000))
                    result['phase'] = 'actions_and_probes'
                    for item in case.get('actions', []):
                        guard.remaining()
                        action(page, item)
                        result['actions'].append({'type': item['type'], 'status': 'executed'})
                    for item in case.get('probes', []):
                        guard.remaining()
                        try:
                            result['probes'][item['id']] = {'status': 'observed', 'value': probe(page, item)}
                        except Exception as error:
                            result['probes'][item['id']] = {'status': 'unverified', 'reason': type(error).__name__}
                    snapshot = page.evaluate(SNAPSHOT)
                    snapshot['url'] = safe_url(page.url)
                    result['snapshot'] = save('evidence/' + case['id'] + '.json', json.dumps(snapshot, ensure_ascii=False, indent=2).encode())
                    # Full-page captures are bounded; record truncation rather than allocating an unbounded image.
                    full = snapshot['document']['height'] <= 8000
                    result['phase'] = 'screenshot'
                    result['screenshot'] = save('screenshots/' + case['id'] + '.png', page.screenshot(full_page=full, timeout=min(10000, guard.time_left() * 1000)))
                    result['runtime'] = {'jsErrors': len(js_errors), 'networkIssues': len(case_events),
                                         'horizontalOverflow': snapshot['document']['width'] > view['width'],
                                         'fullPage': full, 'elementLimitReached': snapshot['elementLimitReached'],
                                         'scroll': snapshot['scroll']}
                    result['status'] = 'captured'
                    result['phase'] = 'complete'
                except Exception as error:
                    result['reason'] = str(error) if isinstance(error, CaptureBlocked) else type(error).__name__
                    result['runtime'] = {'jsErrors': len(js_errors), 'networkIssues': len(case_events)}
                finally:
                    if context:
                        context.close()
                    events.extend({'case': case['id'], **event} for event in case_events)
        finally:
            browser.close()
    report = {'schemaVersion': 1, 'source': safe_url(plan['url']), 'mode': mode,
              'planSha256': sha(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()),
              'dns': resolver.stats if resolver else {'mode': 'system'},
              'browser': browser.version, 'cases': cases, 'files': files,
              'assets': list(assets.values()) + list(missing.values()), 'networkEvents': events,
              'requests': guard.requests, 'receivedBytes': guard.bytes, 'transientRetries': guard.retries,
              'acceptance': 'not_assessed'}
    (output / 'capture.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    # This is intentionally a draft. It never overwrites a refined handoff document.
    import yaml
    data = {'version': 'alpha', 'name': 'Captured website evidence', 'description': 'Measured evidence draft; interpretation and acceptance remain incomplete.',
            'omitted': ['capture-draft: complete section specifications and acceptance still require review']
                       + [row['id'] + ': ' + row['reason'] + '; ' + row['impact'] + ' ' + row['recovery'] for row in missing.values()],
            'colors': {}, 'typography': {}, 'rounded': {}, 'spacing': {}, 'components': {}}
    sections = [
        ('Global rules', 'See capture.json for the source, browser and explicit viewport/state cases.'),
        ('Page regions', 'See evidence/*.json for measured geometry, computed styles and sampled CSS declarations; the DOM inventory is bounded.'),
        ('Interactions', 'Only actions and probes recorded as executed/observed were exercised. Unlisted states remain unverified.'),
        ('Assets', 'manifest.json lists actual response bytes. These are evidence files, not an independently runnable reconstruction; rights require review.'),
        ('Acceptance', 'No visual or behavioral equivalence has been established by capture alone. Use scope requirements and a candidate capture for assessment.'),
    ]
    document = '---\n' + yaml.safe_dump(data, allow_unicode=True, sort_keys=False) + '---\n\n'
    document += '\n\n'.join(f'## {i}. {title}\n\n{body}' for i, (title, body) in enumerate(sections, 1)) + '\n'
    (output / 'DESIGN.md').write_text(document, encoding='utf-8')
    (output / 'manifest.json').write_text(json.dumps({'documentSha256': sha((output / 'DESIGN.md').read_bytes()), 'assets': report['assets']}, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('public', 'local'), required=True)
    parser.add_argument('--local-origin')
    parser.add_argument('--acknowledge-public-scripts', action='store_true')
    parser.add_argument('--browser-executable')
    parser.add_argument('--dns-mode', choices=('system', 'cloudflare'), default='system')
    args = parser.parse_args()
    if args.mode == 'public' and not args.acknowledge_public_scripts:
        parser.error('Public capture requires prior research/script-execution authorization and --acknowledge-public-scripts')
    try:
        report = capture(json.loads(args.plan.read_text(encoding='utf-8-sig')), args.out,
                         mode=args.mode, local_origin=args.local_origin, executable=args.browser_executable, dns_mode=args.dns_mode)
        good = sum(case['status'] == 'captured' for case in report['cases'])
        print(json.dumps({'casesCaptured': good, 'cases': len(report['cases']), 'assets': len(report['assets']), 'acceptance': 'not_assessed'}))
        return 0 if good == len(report['cases']) else 1
    except Exception as error:
        print(json.dumps({'error': type(error).__name__, 'detail': str(error) if isinstance(error, (CaptureBlocked, ValueError)) else 'See environment and input requirements'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
