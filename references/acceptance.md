# 对照验收 / Acceptance

Use `assets/ACCEPTANCE.md`. A scope may be a component, one route or a multi-page journey. Agree its mandatory requirements before testing; include all applicable states, not only default screenshots. For each check record source/implementation evidence, exact conditions, result and discrepancy. Results are `pass`, `fail`, `unverified`, `not_applicable` (last requires rationale).

## Comparison conditions

Match viewport CSS width/height, DPR, browser/rendering environment, zoom, loaded fonts, locale/theme, content, input state, reduced-motion preference, scroll coordinates and animation/media time. Cold-load desktop/tablet/phone individually and test relevant breakpoint neighbors. Record touch emulation separately from real hardware. Avoid network-idle assumptions for continuously active sites; use observed readiness conditions plus bounded timeouts.

| Layer | Evidence required | Does not prove |
| --- | --- | --- |
| Document | YAML/type/section validation; traceable parameters and omissions | Sufficient specification or runnable reproduction |
| Assets | Hash/path/bytes pairing; decoded image/font/media; glyphs and actual network loads | Visual fidelity or permission to redistribute |
| Visual/layout | Same-condition original-size screenshots + region geometry, real text/wrap/crop/layers; top/middle/bottom; repeated first/middle/last | Untested widths, states or motion |
| Interaction | Real mouse/touch/keyboard inputs, state transitions, focus, back/reset, relevant errors/empty states | Backend behavior not actually exercised |
| Motion/media | Aligned phase/time frames, interruption/reversal/reduce; declared parameters separately; media mapping/seek/stop and output comparison if applicable | Audio equivalence from playback success or frame equivalence from duration alone |
| Runnable delivery | Fresh start in isolated workspace, dependencies/assets load, clean console, reproducible URL/instructions | Production deployment |

## State coverage

### 有效测试前提 / Effective test prerequisites

先记录原站的起始状态、真实输入、预期结果与证据位置，再测试实现。重置/切换预设可能隐含后续动作，不能凭按钮名称猜测。断言失败时先核对源站行为和版本：若测试预期错误，保留失败、修订预期并定向复验；不要修改正确实现迎合错误断言。
Record the source start state, actual input, expected outcome and evidence before testing the implementation. Presets or resets may include follow-on actions. On failure, distinguish a wrong expectation from an implementation defect using source/version evidence; preserve the failure and retest the corrected assertion.

暂停测试先证明时间或运动推进，再确认暂停停止、恢复继续；reduce测试先进入普通模式下动画实际触发的状态，再在相同条件下切换偏好并核对对应效果。动画原本未触发时观察到none，不能作为reduce通过证据。区分仅CSS装饰停止与3D/媒体仍运行，按已知源站行为复现，不擅自扩大或削弱行为。
For pause, establish progression, then cessation and resumption. For reduced motion, first trigger the effect under normal preferences, then compare the same conditions after switching. An effect already absent is not a passing suppression test. Record CSS, simulation and media behavior separately and preserve the evidenced source contract.

内部状态或诊断接口仅辅助只读核验；真实点击/拖动/键盘输入及可见结果仍须验证，不能调用内部动作函数、设置完成标记或改DOM来代替用户路径。
Read-only diagnostics may support assertions, but do not replace real input and visible outcomes with internal action calls, completion flags or DOM edits.

Enumerate default, hover, focus, active, expanded, collapsed, disabled, loading, empty, error, success and return/reset where applicable. A local deterministic error fixture can verify implementation behavior but is not evidence of the remote site's error response. Record this distinction.

For navigation, verify the exact route/title and native browser back/forward; confirm restoration of scroll, filters and selection only if required by evidence. For dialogs/menus, verify close button, outside click if present, Escape and focus return; test Tab sequence/trapping where applicable. For drag/media, verify start/move/end/cancel, bounds, playback/seek/volume/pause versus stop as scoped. Do not label untested optional-looking states not applicable without a reason.

## Difference repair

Rank discrepancies by blocked main path, missing content/assets, layout/typography, states, motion, then minor decoration. Repair evidence-backed causes. Keep first-run failures; rerun changed states and shared behavior affected by the fix. Stop once agreed evidence passes; do not run unrelated site inventories.

Independent mode: freeze the exact documents and assets before handing them to an implementer who has not seen the source. Evaluator retains source and comparison captures. Record input hashes, implementation revision/files and any evidence additions; a later corrected pack is a new version. Source copying is not an independent reproduction experiment.

## 打开与展示 / Opening and presentation

用户要求打开页面时，核对实际URL和可见内容后再报告已打开；queued或请求已发送只算中间状态。双屏展示可使用实时iframe，但验收尺寸是iframe内部视口，不是外框的CSS缩放尺寸；说明触摸模拟与真实设备的区别，并提供直接页面入口。不要把展示壳或截图当成实现本体。
When asked to open the result, verify the actual URL and visible content; queued requests are intermediate states. Live iframes can present multiple viewports, but measure their internal viewport rather than the scaled outer frame, label emulation, and provide the direct page URL. Presentation wrappers and screenshots are not the implementation itself.

## Final decision

“Complete within scope” requires all mandatory checks passed, all necessary assets loaded, no unresolved in-scope omissions, and actual same-condition visual + interaction/motion evidence. A tolerance can be agreed for rendering differences, but cannot remove missing behavior. Report counts of compared/failed/unverified checks, not a reproduction percentage.

If input access, backend, auth, resources or time budgets block a requirement, retain `omitted`, explain impact and exact recovery condition, and deliver completed independent parts. Do not weaken guards or silently emulate private services to obtain a passing verdict.
