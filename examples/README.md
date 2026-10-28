# 原创回归示例 / Original regression examples

三个完整的自有示例随本包采用 MIT，署名木渡川（Tanglele）。每个目录包含 `reference/`、`replica/`、`DESIGN.md`、`capture-plan.json` 和 `scope.json`，无远程图片、字体、第三方网站代码或用户数据。

| Example | Cases on each side | Required behavior |
| --- | --- | --- |
| [responsive](responsive/DESIGN.md) | 3 | Desktop/tablet/phone layout, content, image decoding and original SVG bytes |
| [interaction](interaction/DESIGN.md) | 21 | Default, menu, tabs, empty state, detail, dialog, Escape/focus restoration on three viewports |
| [canvas](canvas/DESIGN.md) | 15 | Moving baseline, pause, resume, reset, reduced motion on three viewports |

从 Skill 根目录执行，依赖准备见 [工具说明](../references/tooling.md)：

```text
python examples/run_examples.py --out ../example-results
python examples/run_examples.py --only interaction --out ../interaction-results
python tests/browser_checks.py --out ../browser-checks
python tests/negative_examples.py --out ../negative-results
```

The runner serves only this example directory on its own ephemeral numeric loopback origin, cold-loads both sides, then closes that server. Output must be new and outside the Skill. Capture records, actual response bytes, screenshots, manifests and requirement decisions are saved under the output directory; `SUMMARY.json` aggregates decisions without hiding failures. No browser binaries or run caches are shipped.

These pairs deliberately share tokens and behavior code while varying section wrappers. They are authored regression fixtures, **not independently reconstructed blind benchmarks**. They test the capture/assessment workflow and its failure detection, not arbitrary-site generation quality. All screenshots use emulated viewports. Moving Canvas frames are excluded from raw-pixel equivalence; real motion/stasis observations are still mandatory. Reset/reduce have deterministic visual checks.

负例脚本复制自有示例到新输出目录，分别制造标题尺寸偏差和菜单失效；必须检测到视觉失败与交互失败。它不修改本包原例，也不调整容差以获得通过。守卫检查用另一份自有页面验证请求方法、重定向、协议、下载、弹窗及缺失素材记录。

Open `reference/index.html` and `replica/index.html` to inspect an example directly, or serve this directory using your host's approved local preview. A successful automated run means ready for review; it does not replace visual inspection or user acceptance.
