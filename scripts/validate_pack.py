#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Read-only DESIGN.md schema and paired asset-integrity checks; never acceptance."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required. Use an existing approved environment; no automatic install.", file=sys.stderr)
    sys.exit(2)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"Duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
FIELDS = {"version", "name", "description", "omitted", "colors", "typography", "rounded", "spacing", "components"}
MAPS = {"colors", "typography", "rounded", "spacing", "components"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(document, manifest=None):
    errors, warnings = [], []
    document = document.resolve()
    # Resolve the file first. In some Windows virtualized working directories,
    # resolving the relative parent '.' independently duplicates its leaf name.
    if manifest is not None:
        manifest = manifest.resolve()
    raw = document.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Document exceeds 8 MiB validation bound")
    text = raw.decode("utf-8-sig")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)\Z", text, re.S)
    if not match:
        return {"valid": False, "acceptance": "not_assessed", "errors": ["Missing YAML frontmatter"], "warnings": []}
    data = yaml.load(match[1], Loader=UniqueLoader)
    if not isinstance(data, dict):
        data = {}
        errors.append("Frontmatter must be a mapping")
    if set(data) != FIELDS:
        errors.append("Exactly nine top-level fields required")
    if data.get("version") != "alpha":
        errors.append("version must equal alpha")
    for field in ("name", "description"):
        if not nonempty(data.get(field)):
            errors.append(f"{field} must be a nonempty string")
    omissions = data.get("omitted")
    if not isinstance(omissions, list) or not all(nonempty(item) for item in omissions):
        errors.append("omitted must be a list of nonempty strings")
        omissions = []
    for field in MAPS:
        if not isinstance(data.get(field), dict):
            errors.append(f"{field} must be a mapping")
    # Fenced historical samples do not become live section headings.
    body = re.sub(r"(?ms)^```[^\n]*\n.*?^```\s*$", "", match[2])
    headings = re.findall(r"(?m)^##\s+(\d+)\.\s+(.+)$", body)
    if [number for number, _ in headings] != ["1", "2", "3", "4", "5"]:
        errors.append("Expected five ordered level-two sections numbered 1. through 5.")
    for index, (number, title) in enumerate(headings):
        start = body.index(f"## {number}. {title}") + len(f"## {number}. {title}")
        end = body.find("\n## ", start)
        if not body[start:end if end >= 0 else len(body)].strip():
            errors.append(f"Section {number} is empty")
    if re.search(r"\[object Object\]|\bundefined\b|\bNaN\b", body):
        errors.append("Object serialization or undefined-value residue in body")
    if re.search(r"<[^<>\r\n]*(?:待填|网站 / 页面名|CSS色|元素名|素材 ID|区块名|准确 URL)[^<>\r\n]*>", text):
        errors.append("Unfilled template prompts")
    checked = 0
    if manifest:
        bundle = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(bundle, dict):
            raise ValueError("Manifest must be an object")
        if bundle.get("documentSha256") != hashlib.sha256(raw).hexdigest():
            errors.append("documentSha256 mismatch: document and pack are not paired")
        rows = bundle.get("assets")
        if not isinstance(rows, list):
            raise ValueError("manifest.assets must be an array")
        root, ids, paths = manifest.parent, set(), set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"Asset {index} must be an object")
                continue
            asset_id = row.get("id")
            if not nonempty(asset_id) or asset_id in ids:
                errors.append(f"Asset {index} has missing or duplicate id")
                continue
            ids.add(asset_id)
            if not nonempty(row.get("source")):
                errors.append(f"{asset_id}: missing source")
            if row.get("status") == "missing":
                for key in ("reason", "impact", "recovery"):
                    if not nonempty(row.get(key)):
                        errors.append(f"{asset_id}: missing {key}")
                if not any(asset_id in omission for omission in omissions):
                    errors.append(f"{asset_id}: missing asset absent from omitted")
                warnings.append(f"{asset_id}: asset unavailable; fidelity remains unresolved")
                continue
            if row.get("status") != "obtained":
                errors.append(f"{asset_id}: status must be obtained or missing")
                continue
            relative = row.get("path")
            if not nonempty(relative) or "\\" in relative or ":" in relative:
                errors.append(f"{asset_id}: use a portable relative path")
                continue
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or path == root:
                errors.append(f"{asset_id}: path escapes pack root")
                continue
            if path in paths:
                errors.append(f"{asset_id}: duplicate resolved asset path")
                continue
            paths.add(path)
            if not path.is_file():
                errors.append(f"{asset_id}: file absent")
                continue
            if type(row.get("bytes")) is not int or row["bytes"] < 0 or path.stat().st_size != row["bytes"]:
                errors.append(f"{asset_id}: byte count mismatch")
            if not isinstance(row.get("sha256"), str) or not HEX.fullmatch(row["sha256"]) or digest(path) != row["sha256"]:
                errors.append(f"{asset_id}: SHA-256 mismatch")
            for key in ("mime", "usage", "license"):
                if not nonempty(row.get(key)):
                    errors.append(f"{asset_id}: missing {key}")
            checked += 1
    else:
        warnings.append("No manifest supplied: asset integrity not checked")
    if omissions:
        warnings.append(f"{len(omissions)} omitted entries remain; structure is not completeness")
    return {"valid": not errors, "acceptance": "not_assessed", "assetsChecked": checked,
            "documentSha256": hashlib.sha256(raw).hexdigest(), "errors": errors, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.document, args.manifest)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as error:
        print(json.dumps({"valid": False, "acceptance": "not_assessed", "errors": [str(error)]}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
