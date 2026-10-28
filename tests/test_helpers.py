# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Offline behavior tests using newly generated, MIT-licensed synthetic fixtures."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SKILL = Path(__file__).resolve().parents[1]
DOCUMENT = """---
version: alpha
name: Synthetic helper fixture
description: A minimal document for structural tests, not website evidence.
omitted: []
colors: {}
typography: {}
rounded: {}
spacing: {}
components: {}
---

## 1. Global rules
This synthetic fixture does not specify a real website.
## 2. Sections
A generated plain-text asset exercises file integrity.
## 3. Interactions
No website interaction is claimed by this fixture.
## 4. Assets
The manifest pairs the text asset and this document by hash.
## 5. Acceptance
Helper success is not visual or behavioral acceptance.
"""


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='website reproduction 测试 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pack = self.root / 'pack'
        self.pack.mkdir()
        self.doc = self.pack / 'DESIGN.md'
        self.doc.write_text(DOCUMENT, encoding='utf-8')
        self.asset = self.pack / 'asset.txt'
        self.asset.write_bytes(b'Synthetic test asset. MIT License.\n')
        self.manifest = self.pack / 'manifest.json'
        self.data = {
            'documentSha256': hashlib.sha256(self.doc.read_bytes()).hexdigest(),
            'assets': [{
                'id': 'text', 'status': 'obtained', 'path': 'asset.txt',
                'mime': 'text/plain', 'bytes': self.asset.stat().st_size,
                'sha256': hashlib.sha256(self.asset.read_bytes()).hexdigest(),
                'source': 'generated synthetic test fixture',
                'usage': 'helper integrity test', 'license': 'MIT',
            }],
        }
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.data), encoding='utf-8')

    def run_helper(self, script, *args, cwd=None):
        return subprocess.run(
            [sys.executable, '-X', 'utf8', str(SKILL / 'scripts' / script),
             *map(str, args)], cwd=cwd or self.root, capture_output=True,
            text=True, encoding='utf-8', timeout=30,
        )

    def validate(self):
        return self.run_helper('validate_pack.py', self.doc, '--manifest', self.manifest)

    def assert_failure(self, message):
        result = self.validate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(message, result.stdout)

    def images(self, actual_size=(8, 8)):
        a, b = self.root / 'a.png', self.root / 'b.png'
        Image.new('RGBA', (8, 8), (20, 30, 40, 255)).save(a)
        Image.new('RGBA', actual_size, (20, 30, 40, 255)).save(b)
        return a, b

    def compare(self, a, b, stem='result'):
        return self.run_helper('compare_images.py', a, b,
                               '--diff', self.root / (stem + '.png'),
                               '--report', self.root / (stem + '.json'))

    def test_valid_pack_is_not_acceptance(self):
        before = {p.name: p.read_bytes() for p in self.pack.iterdir()}
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['valid'])
        self.assertEqual(report['acceptance'], 'not_assessed')
        self.assertEqual(report['assetsChecked'], 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.pack.iterdir()})

    def test_relative_manifest_from_foreign_cwd(self):
        result = self.run_helper('validate_pack.py', 'DESIGN.md', '--manifest',
                                 'manifest.json', cwd=self.pack)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_corrupted_asset(self):
        self.asset.write_bytes(self.asset.read_bytes() + b'corruption')
        self.assert_failure('SHA-256 mismatch')

    def test_parent_escape(self):
        self.data['assets'][0]['path'] = '../outside.txt'
        self.write_manifest()
        self.assert_failure('escapes pack root')

    def test_document_pairing(self):
        self.data['documentSha256'] = '0' * 64
        self.write_manifest()
        self.assert_failure('not paired')

    def test_duplicate_yaml_key(self):
        self.doc.write_text(DOCUMENT.replace('version: alpha', 'version: alpha\nversion: beta'), encoding='utf-8')
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Duplicate YAML key', result.stdout)

    def test_extra_top_level_field(self):
        self.doc.write_text(DOCUMENT.replace('colors: {}', 'extra: true\ncolors: {}'), encoding='utf-8')
        self.assert_failure('nine top-level')

    def test_section_order(self):
        self.doc.write_text(DOCUMENT.replace('## 3.', '## 7.'), encoding='utf-8')
        self.assert_failure('ordered level-two')

    def test_missing_asset_requires_omission(self):
        self.data['assets'] = [{
            'id': 'missing-font', 'status': 'missing', 'source': 'synthetic',
            'reason': 'not supplied', 'impact': 'glyphs unverified',
            'recovery': 'supply licensed font file',
        }]
        self.write_manifest()
        self.assert_failure('absent from omitted')
        self.doc.write_text(DOCUMENT.replace('omitted: []', 'omitted: [missing-font unavailable]'), encoding='utf-8')
        self.data['documentSha256'] = hashlib.sha256(self.doc.read_bytes()).hexdigest()
        self.write_manifest()
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['acceptance'], 'not_assessed')
        self.assertTrue(report['warnings'])

    def test_boolean_byte_count_is_invalid(self):
        self.data['assets'][0]['bytes'] = True
        self.write_manifest()
        self.assert_failure('byte count mismatch')

    def test_identical_images(self):
        result = self.compare(*self.images())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['differentPixels'], 0)
        self.assertEqual(report['acceptance'], 'not_assessed')

    def test_alpha_difference_visible_without_automatic_failure(self):
        a, b = self.images()
        with Image.open(b) as original:
            changed = original.convert('RGBA')
        changed.putpixel((2, 2), (20, 30, 40, 0))
        changed.save(b)
        result = self.compare(a, b)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['differentPixels'], 1)
        with Image.open(self.root / 'result.png') as diff:
            self.assertEqual(diff.getpixel((2, 2)), (255, 255, 255))

    def test_existing_output_preserved(self):
        a, b = self.images()
        target = self.root / 'result.png'
        target.write_bytes(b'existing user file')
        result = self.compare(a, b)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), b'existing user file')
        self.assertFalse((self.root / 'result.json').exists())

    def test_input_cannot_be_output(self):
        a, b = self.images()
        before = a.read_bytes()
        result = self.run_helper('compare_images.py', a, b, '--diff', a,
                                 '--report', self.root / 'metrics.json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(a.read_bytes(), before)

    def test_outputs_must_be_distinct(self):
        a, b = self.images()
        output = self.root / 'shared'
        result = self.run_helper('compare_images.py', a, b, '--diff', output, '--report', output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_unequal_dimensions_no_resize(self):
        result = self.compare(*self.images(actual_size=(7, 8)))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse((self.root / 'result.png').exists())
        self.assertFalse((self.root / 'result.json').exists())


if __name__ == '__main__':
    unittest.main()
