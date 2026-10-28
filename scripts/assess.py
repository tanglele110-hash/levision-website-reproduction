# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Assess explicit scope requirements against paired, hash-checked captures."""
import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inside(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Portable relative evidence path required')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Evidence absent or outside report root')
    return path


def load_capture(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('schemaVersion') != 1 or not isinstance(data.get('cases'), list):
        raise ValueError('Unsupported capture schema')
    files = {}
    for row in data.get('files', []):
        evidence = inside(path.parent, row.get('path'))
        if row['path'] in files or row.get('bytes') != evidence.stat().st_size or row.get('sha256') != digest(evidence):
            raise ValueError('Evidence inventory duplicate or hash mismatch')
        files[row['path']] = evidence
    cases = {case['id']: case for case in data['cases']}
    if len(cases) != len(data['cases']):
        raise ValueError('Duplicate capture case')
    return {'data': data, 'root': path.parent, 'files': files, 'cases': cases, 'sha256': digest(path)}


def image_metrics(left, right):
    with Image.open(left) as a, Image.open(right) as b:
        if a.size != b.size:
            return {'dimensionsMatch': False, 'reference': list(a.size), 'candidate': list(b.size)}
        diff = ImageChops.difference(a.convert('RGBA'), b.convert('RGBA'))
    peak = diff.getchannel(0)
    for channel in diff.split()[1:]:
        peak = ImageChops.lighter(peak, channel)
    changed = diff.width * diff.height - peak.histogram()[0]
    return {'dimensionsMatch': True, 'differentPixels': changed,
            'differentPixelRatio': changed / (diff.width * diff.height),
            'meanAbsoluteErrorRGBA': ImageStat.Stat(diff).mean}


def close_values(left, right, tolerance):
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(close_values(left[key], right[key], tolerance) for key in left)
    if type(left) in (int, float) and type(right) in (int, float):
        return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance
    return type(left) is type(right) and left == right


def assess(scope, reference, candidate, manual=None):
    requirements = scope.get('requirements')
    if scope.get('schemaVersion') != 1 or not isinstance(requirements, list) or not requirements:
        raise ValueError('schemaVersion=1 and nonempty requirements required; legacy scopes need explicit mapping')
    ids, rows = set(), []
    for req in requirements:
        identifier = req.get('id')
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError('Unique requirement ids required')
        ids.add(identifier)
        kind = req.get('kind')
        if kind not in ('visual', 'probe', 'runtime', 'asset', 'manual'):
            raise ValueError('Unsupported requirement kind')
        if type(req.get('required', True)) is not bool:
            raise ValueError('required must be boolean')
        result = {'id': identifier, 'kind': kind, 'required': req.get('required', True),
                  'status': 'unverified', 'reason': 'evidence_missing'}
        rows.append(result)
        if kind == 'manual':
            evidence = (manual or {}).get('checks', {}).get(identifier)
            if evidence:
                if evidence.get('status') not in ('pass', 'fail', 'unverified') or not evidence.get('reason'):
                    raise ValueError('Manual decision requires supported status and reason')
                paths = evidence.get('evidence', [])
                if evidence['status'] in ('pass', 'fail') and not paths:
                    raise ValueError('Manual pass/fail requires file evidence')
                files = [{'path': name, 'sha256': digest(inside(manual['_root'], name))} for name in paths]
                result.update(status=evidence['status'], reason=evidence['reason'], evidence=files)
            continue
        case_id = req.get('case')
        source = reference['cases'].get(case_id)
        target = candidate['cases'].get(case_id)
        result['case'] = case_id
        if not source or source.get('status') != 'captured':
            result['reason'] = 'reference_case_unavailable'
            continue
        if not target or target.get('status') != 'captured':
            result['reason'] = 'candidate_case_unavailable'
            continue
        if source['viewport'] != target['viewport'] or source['motion'] != target['motion']:
            result.update(status='fail', reason='comparison_conditions_differ')
            continue
        if not source.get('scenarioSha256') or not target.get('scenarioSha256'):
            result['reason'] = 'scenario_contract_missing'
            continue
        if source['scenarioSha256'] != target['scenarioSha256'] or reference['data'].get('browser') != candidate['data'].get('browser'):
            result.update(status='fail', reason='scenario_or_browser_differs')
            continue
        if kind == 'probe':
            key = req.get('probe')
            a, b = source.get('probes', {}).get(key, {}), target.get('probes', {}).get(key, {})
            if a.get('status') != 'observed' or b.get('status') != 'observed':
                continue
            if 'referenceExpected' in req and a['value'] != req['referenceExpected']:
                result.update(reason='reference_baseline_not_established', observed=a['value'])
                continue
            tolerance = req.get('tolerance', 0)
            if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0:
                raise ValueError('Nonnegative finite probe tolerance required')
            passed = close_values(a['value'], b['value'], tolerance)
            result.update(status='pass' if passed else 'fail', reason='observed_values_compared', reference=a['value'], candidate=b['value'])
        elif kind == 'runtime':
            expected = {'jsErrors': 0, 'networkIssues': 0, 'horizontalOverflow': False}
            if any(source.get('runtime', {}).get(k) != v for k, v in expected.items()):
                result['reason'] = 'reference_runtime_not_clean'
                continue
            passed = all(target.get('runtime', {}).get(k) == v for k, v in expected.items())
            result.update(status='pass' if passed else 'fail', reason='runtime_checked', candidate=target.get('runtime'))
        elif kind == 'visual':
            if (not source.get('runtime', {}).get('fullPage') or not target.get('runtime', {}).get('fullPage')
                    or source.get('runtime', {}).get('scroll') != target.get('runtime', {}).get('scroll')):
                result['reason'] = 'full_page_or_scroll_not_aligned'
                continue
            limit = req.get('maxDifferentPixelRatio')
            if type(limit) not in (int, float) or not math.isfinite(limit) or not 0 <= limit <= 1:
                result['reason'] = 'explicit_visual_tolerance_required'
                continue
            a = reference['files'].get(source.get('screenshot', {}).get('path'))
            b = candidate['files'].get(target.get('screenshot', {}).get('path'))
            if not a or not b:
                continue
            metrics = image_metrics(a, b)
            passed = metrics['dimensionsMatch'] and metrics['differentPixelRatio'] <= limit
            result.update(status='pass' if passed else 'fail', reason='raw_same_size_pixels', metrics=metrics)
        elif kind == 'asset':
            suffix = req.get('sourceSuffix')
            if not isinstance(suffix, str) or not suffix:
                raise ValueError('Asset sourceSuffix is required')
            matches = [[a for a in report['data'].get('assets', []) if a.get('status') == 'obtained' and a.get('source', '').endswith(suffix)] for report in (reference, candidate)]
            if any(len(items) != 1 for items in matches):
                result['reason'] = 'asset_missing_or_ambiguous'
                continue
            a, b = matches[0][0], matches[1][0]
            if any(row['path'] not in report['files'] for row, report in ((a, reference), (b, candidate))):
                continue
            result.update(status='pass' if a['sha256'] == b['sha256'] else 'fail', reason='asset_bytes_compared')
    counts = dict(Counter(row['status'] for row in rows))
    required = [row for row in rows if row['required']]
    if not required:
        raise ValueError('At least one required check is necessary')
    ready = all(row['status'] == 'pass' for row in required)
    return {'schemaVersion': 1, 'status': 'ready_for_user_review' if ready else 'needs_work',
            'userAcceptance': 'not_assessed', 'referenceCaptureSha256': reference['sha256'],
            'candidateCaptureSha256': candidate['sha256'], 'counts': counts, 'checks': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--manual', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError('Output must be a new file')
        scope = json.loads(args.scope.read_text(encoding='utf-8-sig'))
        manual = None
        if args.manual:
            manual = json.loads(args.manual.read_text(encoding='utf-8-sig'))
            if manual.get('scopeSha256') != digest(args.scope):
                raise ValueError('Manual evidence is not paired with this scope')
            manual['_root'] = args.manual.resolve().parent
        report = assess(scope, load_capture(args.reference), load_capture(args.candidate), manual)
        report['scopeSha256'] = digest(args.scope)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'status': report['status'], 'counts': report['counts'], 'userAcceptance': 'not_assessed'}))
        return 0 if report['status'] == 'ready_for_user_review' else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'error': type(error).__name__, 'detail': str(error)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
