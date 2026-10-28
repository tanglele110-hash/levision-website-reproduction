# 动态场景 / Dynamic scenes

适用于Canvas/WebGL、程序生成素材及持续模拟。沿用capture.md的隔离与预算，不添加普通静态页不需要的检查，也不把某个站点的框架、分辨率或状态变量固化为要求。
Use for Canvas/WebGL, procedural assets and continuous simulation. Retain capture isolation and budgets; do not impose this branch on static pages or hardcode a site's framework, resolution or state variable.

## 1. 分层就绪 / Layered readiness

区分资源可用、场景可见、当前动作进行中、目标状态完成。load、network-idle、Canvas存在或着色器编译完成均不能独自证明一次制作/过场结束。开始取证前为所需状态定义可观察条件和有界等待；不要求永远运动的场景最终静止。
Separate resource availability, visible rendering, action-in-progress and target completion. Page load, an existing canvas or completed shader compilation alone does not prove a recipe/transition has finished. Define observable readiness with bounded waits; continuously animated scenes need not become motionless.

可结合加载层消失、目标名称/控件变化、有效绘制结果、只读busy/progress等已有诊断值。截图标明正在播放或已完成；日志中的等待毫秒是观察时刻，不是效果时长。不得设置完成状态来跳过真实流程。超时保留最后可见状态及缺失证据，不能提升预算来制造完成。
Combine visible loading/state cues, rendered output and available read-only diagnostics. Label in-progress versus completed captures; wait durations are observations, not animation durations. Never set completion state to skip the path; preserve timeout evidence without increasing budgets to force success.

## 2. 多条件响应式 / Multiple responsive conditions

分别列出CSS media/container条件、JS宽高判断、pointer/hover能力、DPR与运行时质量调节，记录原运算符、单位和受影响对象。相同数值的`<=`与`<`不合并；设备名称或单一宽度不能替代这些条件。
List CSS media/container queries, JS dimensions, pointer/hover capabilities, DPR and runtime quality adjustments separately, retaining operators, units and affected regions. Do not merge `<=` with `<` or replace capabilities with a device label.

针对实际影响布局或渲染的边界，记录下方、等于、上方的实测；冷加载决策和resize后的决策可能不同，按源码/实际行为选择必要路径。报告外层展示尺寸、内部视口、Canvas CSS尺寸、drawing-buffer尺寸及实际渲染像素比，避免把清晰度调节当成布局变化。
Probe below, at and above relevant boundaries. Cold-load and resize decisions may differ; choose paths supported by evidence. Distinguish presentation size, internal viewport, canvas CSS size, drawing-buffer size and actual pixel ratio.

## 3. 程序素材与环境 / Procedural assets and environment

保留实际几何、纹理、shader、图标绘制、音效生成代码及所需模块；清单记录生成入口、参数来源、依赖版本、路径、哈希与许可，不能用截图或占位图替代。未知参数继续列为omitted。音频初始化或静音状态通过不等于听感一致。
Carry generator code for geometry, textures, shaders, icons and audio plus required modules. Inventory entrypoints, evidenced parameters, versions, paths, hashes and licenses; screenshots/placeholders are not replacements. Keep unknowns omitted; audio initialization/mute checks do not prove output equivalence.

核对浏览器/图形后端、WebGL上下文是否有效、相机、色彩空间、色调映射、曝光、灯光及实际DPR等影响结果的已知条件；只能读取当前环境可获得的信息，未知项注明。无须为了记录信息改变系统GPU设置。
Record available rendering conditions that matter: browser/backend, valid WebGL context, camera, color space, tone mapping, exposure, lighting and actual DPR. Mark unavailable information; do not change system GPU settings merely to collect metadata.

同一 Chromium 版本的 headless-shell 与完整浏览器可能采用不同图形后端。若资源齐全但持续场景极慢，先记录浏览器可执行文件、可读 renderer/vendor、load 与完成状态耗时；检查软件渲染与 dt 钳制造成的墙钟差异。可用已有完整浏览器重验，保留原失败，不通过调低原站 DPR、跳过过场或延长失败预算制造通过。截图仍需实际查看，不能只看 WebGL 上下文有效或 draw-call 数。

## 4. 随机与时间 / Randomness and time

分开比较DOM布局/文案、确定性场景状态、粒子或程序噪声、运动过程。记录随机源、墙钟与模拟时钟、dt钳制、暂停和帧率调节中能够确认的部分。帧率较低时，源码中的模拟秒数不一定等于墙钟耗时。
Compare DOM/text, deterministic scene state, particles/procedural noise and motion separately. Record evidenced randomness, wall/simulation clocks, dt caps, pause and frame governors. Simulation durations may differ from wall-clock durations under low frame rates.

先观察正常运行。需要逐帧比较且已有可配置种子/时钟或获准的隔离测试副本时，可在双方使用同一明确测试配置；保留正常运行证据、配置与原件，不能把测试改造称为原站默认行为。不能控制随机性或对齐相位时，保留完整截图和差分，将逐帧等价列为未验证；几何、状态及真实输入结果仍可独立验收。
Observe normal operation first. For frame comparison, use the same explicit deterministic configuration only when supported or in authorized isolated test copies, retaining normal evidence and originals. Do not call test instrumentation default behavior. If randomness/phase cannot be aligned, retain full captures and diffs and mark frame equivalence unverified while assessing geometry, states and actual inputs separately.

差异集中在粒子区域只是位置证据；没有来源或受控重复实验时，不把全部差异归因于随机数。不能通过裁切、遮罩或宽容差隐藏缺失模型、材质或交互，也不把像素差异换算成还原百分比。动效至少采起点、适用的中间状态和终点，外加本次范围内的中断/恢复；抑制行为的有效起始条件按acceptance.md核验。
Localized particle differences identify a region, not their cause without source or controlled-repeat evidence. Do not conceal missing models/materials/behavior with cropping, masks or broad tolerance, or turn pixel metrics into a fidelity percentage. Capture start/intermediate/end and scoped interruption/resumption; use acceptance.md's active-baseline checks for suppression.
