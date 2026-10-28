# 来源与署名 / Attribution and provenance

作者与维护者 / Author and maintainer：**木渡川（Tanglele）**

Copyright (c) 2026 木渡川（Tanglele）. 本包中由作者有权许可的文档、模板、脚本及测试采用 [MIT License](LICENSE)。

## 本包来源 / Package origin

- 核心模板来自作者在个人设计系统中持续维护的 `docs/templates/website-design.md`，沿用九个 YAML 顶层字段与五章正文。该路径是来源标识，不是运行时依赖；本包已提供完整模板。
- 工作流结合该项目的 `docs/02_execution/website-reproduction-capture.md`、采集实现和实际资料包审阅经验整理，后续补充源码本地化、动态场景就绪、有效测试前提和响应式验收。
- 文档整理、通用辅助脚本和测试在作者指导下使用 AI 辅助编写并经本地验证。这里的署名表达作者与维护者身份，不将通用方法、第三方作品或所有 AI 输出的权利笼统归于作者。
- Boba Bar 是迭代工作流时的一项验证案例。本包不包含该网站源码、图片、字体、音频、截图、页面文案或 Three.js，也不以本包署名替代原作者署名。
- `examples/` 三个页面及配对实现是本次原创的回归资料，随本包采用 MIT。它们不取自外部网站，也不是独立盲测复刻案例。

The core template comes from the maintainer's existing design-document workflow. Capture and acceptance practices were refined through local implementation and review, with AI-assisted drafting and coding. The website used as a validation case is not distributed here. Historical provenance of every sentence before the maintained project template has not been independently established.

## 外部依赖 / External dependencies

以下为可选辅助脚本依赖，安装后按各自许可证使用。本包只声明版本，不分发依赖本体；若再打包依赖或二进制分发物，应保留其适用的许可文件和第三方声明。

These optional helper dependencies are not vendored. Their own licenses and applicable notices continue to apply if they are redistributed.

| 依赖 / Dependency | 实测版本 / Tested version | 许可 / License | 用途 / Purpose |
| --- | --- | --- | --- |
| PyYAML | 6.0.3 | [MIT](https://github.com/yaml/pyyaml/blob/6.0.3/LICENSE) | YAML 结构解析 / YAML parsing |
| Pillow | 12.1.1 | [MIT-CMU and included component notices](https://github.com/python-pillow/Pillow/blob/12.1.1/LICENSE) | 图像读取与像素差分 / Image metrics |
| Playwright for Python | 1.59.0 | [Apache-2.0](https://github.com/microsoft/playwright-python/blob/v1.59.0/LICENSE) | 可选浏览器采集 / Optional browser capture |

浏览器二进制不随包提供；安装或再分发 Chromium 时须处理其自身许可与组件声明。Browser binaries are not bundled; their own licenses and component notices remain separate.

## 方法对照 / Workflow references

本轮对照过 [Jane 的 web-clone Skill](https://github.com/Jane-xiaoer/claude-skill-web-clone) 的源码与采集分工，以及 [Perfect Web Clone Skill](https://github.com/ericshang98/perfect-web-clone-skill) 的状态和验收流程。采用的是明确采集计划、实际文件、状态证据等方法层面的启发；本包脚本与示例独立编写，未复制上述仓库的代码或模板。

These projects informed the comparison of workflow approaches. They are not runtime dependencies; no source or template from them is distributed in this package. The implementation retains its own DESIGN.md schema and does not adopt arbitrary-code actions, automatic acceptance scores or a framework requirement.

公共 DNS 可选解析器按 [Cloudflare 官方 DNS JSON API 文档](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/) 独立编写，只在显式选择时访问该服务；未包含其文档或实现代码。该服务不是本包许可证所涵盖的内容，也不改变第三方页面的权利边界。

## 使用结果的权利 / Rights in outputs

Skill 的许可只覆盖有权授予的本包内容，不为被采集网站或复刻产物提供统一授权。公开可访问、可下载或标注“开源”不足以证明所有素材可再分发；逐项记录代码、字体、图片、音视频等的来源与许可证。

The package license does not relicense captured websites, reference material or generated deliverables. Preserve source-specific notices and verify rights for any third-party material you redistribute. Credit in this file is not a substitute for permission.
