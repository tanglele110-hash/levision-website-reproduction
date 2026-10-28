# 交接契约 / Pack contract

Minimum useful pack:

```text
DESIGN.md               nine YAML fields + five numbered sections
scope.json              agreed routes, states, devices, exclusions, tolerances
manifest.json           document hash + obtained/missing asset records
assets/                 actual files; no sessions, profiles or secrets
evidence/               measurements, state observations, source pointers
screenshots/            original-size captures with condition records
```

An existing pack may use its own layout/schema. Inspect and explicitly map it; do not silently overwrite its manifest or modify authority files to match this helper. Keep original identifiers, provenance and refined text. Full owned source is a separate delivery, never included inside the reusable Skill itself.

## 许可源码本地化 / Licensed-source localization

仅在许可覆盖本次用途、且用户没有要求独立重写时选择此模式。公开可下载不等于具有复用许可。记录实际读过的许可文件与适用版本，保留所需版权/许可文本；依赖与独立素材分别核对，仓库许可不能自动替第三方素材背书。许可不明确的部分标为待核验，继续已获准的取证与独立工作。
Choose this mode only when reuse is permitted and the user has not requested independent reimplementation. Public availability is not permission. Record license evidence and version, preserve required notices, and check dependencies and separately licensed assets. Keep uncertainty scoped to the affected material.

- 固定上游提交或发布版本，保存原件、文件清单与哈希；通过现有受限采集边界核对部署页实际加载文件。仅对已比较的文件声称版本相符，不能用默认分支或仓库更新时间替代部署版本证据。
  Pin a commit/release and preserve originals, inventory and hashes. Compare observed deployed files using the existing guarded capture path; claim a match only for compared files, never from a default branch or timestamp.
- 记录原件到本地文件的变更清单。CDN地址改成本地路径时携带页面实际需要的准确版本及传递依赖、许可；不能借用工作区其他版本后称依赖一致。保持真实目录布局并映射清单，无须强迁为统一assets目录。
  Record original-to-local changes. Vendor the exact required version and transitive dependencies with licenses when localizing CDN paths; do not substitute the workspace's different version. Map the actual layout rather than relocating everything merely for uniformity.
- 声称离线可运行前，冷启动并只允许交付服务的明确本地origin，检查所有必需资源和交互。此隔离本地模式不能扩大公开URL采集的allowlist。
  Before claiming offline operation, cold-load with only the explicit delivery origin allowed and verify required resources and interactions. This local mode must not widen the public-capture allowlist.
- 报告区分“源码本地化”与“依据证据独立实现”。源码一致支持来源和实现核对，不替代真实界面、交互、动效验收，也不证明独立重建能力。
  Distinguish source localization from evidence-based independent implementation. Identical source supports provenance checks, not runtime acceptance or a claim of independent reconstruction.

## DESIGN.md schema

Exactly `version`, `name`, `description`, `omitted`, `colors`, `typography`, `rounded`, `spacing`, `components`; version is `alpha`, name/description nonempty strings, omitted is an array of nonempty strings, the remaining five fields are mappings. Mapping values preserve observed CSS types/units; unknown maps can be empty with corresponding omitted entries. Body sections in order are global rules, page regions, components/interactions, assets/implementation, acceptance (numbered 1–5; Chinese or English titles).

Use `assets/DESIGN.md`. Remove template prompts before delivery. For each omission identify the missing evidence, affected requirement and recovery condition in the body. Avoid `[object Object]`, `undefined`, `NaN`, guessed values or empty omitted arrays concealing pending acceptance. Machine validation cannot prove completeness.

## Manifest for validate_pack.py

The manifest's parent is the pack root. All obtained paths must stay inside it after realpath resolution (including links). Hash the exact UTF-8 DESIGN.md bytes, not normalized text. No embedded credentials or signed access URLs.

```json
{
  "documentSha256": "64 lowercase hexadecimal characters",
  "assets": [
    {
      "id": "hero",
      "status": "obtained",
      "path": "assets/hero.svg",
      "mime": "image/svg+xml",
      "bytes": 123,
      "sha256": "64 lowercase hexadecimal characters",
      "source": "owned source or public unsigned URL",
      "usage": "hero illustration",
      "license": "owned / license evidence / unverified"
    },
    {
      "id": "font-regular",
      "status": "missing",
      "source": "public source or provided filename",
      "reason": "actual failure",
      "impact": "affected text and fidelity",
      "recovery": "file or access evidence required"
    }
  ]
}
```

No extra fake asset rows when the page has none. `assets: []` is valid for a genuinely asset-free page. Procedural geometry, textures, shaders and synthesized audio still require their actual generator modules and dependencies in the delivery inventory; no downloaded image files does not mean no assets. Missing rows must also appear in `omitted` by asset ID. MIME, decoding, licensing and browser loading require separate evidence; matching bytes/hash alone does not establish them.

## Helpers and return codes

- `validate_pack.py`: Python 3.11+ + PyYAML. Exit 0 structural/integrity checks passed, exit 1 invalid pack, exit 2 command/dependency/input error. JSON report to stdout; contains `acceptance: not_assessed` even when valid. No file writes or network.
- `compare_images.py`: Python 3.11+ + Pillow. Inputs must have equal pixel dimensions. Compares RGBA channels, reports raw mismatch ratio and per-channel absolute error; writes a visible RGB difference map and JSON to explicitly new paths. It never rescales, crops, masks or alters inputs. Exit 0 means metrics were produced, not that images match; dimension mismatch is exit 1. Numerical tolerance belongs to the agreed acceptance plan.

For screenshots, align viewport/DPR/scroll/fonts/state/time before comparison. Pixel metrics are sensitive to rendering and anti-aliasing; inspect actual images and affected regions. Do not convert a pixel ratio into a reproduction percentage.
