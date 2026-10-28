#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 木渡川（Tanglele）
"""Original-size RGBA image metrics, without thresholds or acceptance claims."""
import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:
    print("Pillow is required. Use an existing approved environment; no automatic install.", file=sys.stderr)
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--diff", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    inputs = {args.reference.resolve(), args.actual.resolve()}
    outputs = [args.diff.resolve(), args.report.resolve()]
    if len(set(outputs)) != 2 or any(path in inputs or path.exists() for path in outputs):
        parser.error("Output paths must be distinct new files, never an input")
    try:
        with Image.open(args.reference) as source, Image.open(args.actual) as target:
            source.load()
            target.load()
            if source.size != target.size:
                print(json.dumps({"error": "Pixel dimensions differ; no resize performed", "reference": source.size, "actual": target.size}))
                return 1
            diff = ImageChops.difference(source.convert("RGBA"), target.convert("RGBA"))
        channels = diff.split()
        maximum = channels[0]
        for channel in channels[1:]:
            maximum = ImageChops.lighter(maximum, channel)
        total = diff.width * diff.height
        changed = total - maximum.histogram()[0]
        stats = ImageStat.Stat(diff)
        result = {"acceptance": "not_assessed", "width": diff.width, "height": diff.height,
                  "pixels": total, "differentPixels": changed, "differentPixelRatio": changed / total,
                  "meanAbsoluteErrorRGBA": stats.mean, "maxAbsoluteErrorRGBA": [item[1] for item in diff.getextrema()],
                  "reference": str(args.reference), "actual": str(args.actual)}
        # Alpha-only differences must remain visible in the diagnostic RGB map.
        visible = Image.merge("RGB", tuple(ImageChops.lighter(c, channels[3]) for c in channels[:3]))
        for path in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
        with args.diff.open("xb") as stream:
            visible.save(stream, format="PNG")
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
