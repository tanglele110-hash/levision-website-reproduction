# 取证与安全定位 / Capture and target identity

## Public input

Run scripts only in a fresh disposable context without saved profiles, cookies, credentials or granted permissions. Confirm public HTTP/HTTPS targets and every redirect/subresource; reject private, loopback, link-local, reserved or unresolved destinations, including IPv6 and alternate address forms. Use a host-provided guard or a verified capture runner. Do not improvise a weaker fetch fallback.

仅 GET/HEAD；阻断写请求、Service Worker、WebSocket、EventSource/事件流、下载和弹窗；保持 TLS 校验。明确页面数、请求数、每资源/总字节和时间上限，记录截断与拦截，超限不提升上限或关闭保护来制造成功。即使 GET 也可能有副作用，退出登录、删除、下单等不作为研究点击。

The tool must actually enforce these boundaries. If the available browser cannot provide them, leave public live capture pending and continue with supplied files/screenshots or an approved guarded runner. Do not claim that an ordinary logged-in tab is isolated. A local owned fixture is a separate mode: allow only its explicit loopback origin and reject remote requests; never add loopback to the public-URL allowlist.

公网域名解析为保留地址时，先查 DNS 与实际失败阶段，不误判为网站内容不可访问。可选受限采集器提供显式公共 DNS 查询，见 [tooling.md](tooling.md)；默认系统解析与地址校验保持不变，禁止通过允许保留地址、忽略证书或普通浏览器请求回退来绕过拦截。DNS 修复、资源取得、场景就绪、交互验证是不同结论。

Capture only research-authorized content. Record license/access uncertainty. Downloading public assets does not grant redistribution rights. Saved external HTML remains inert for preview; do not move untrusted scripts into a trusted workbench origin.

## Evidence sequence

1. Record final URL, page title, load outcome, browser/version, viewport, DPR, device input capabilities, zoom, font status, locale, theme, reduced motion, scroll and time origin. Cold-load each viewport separately.
2. Read DOM hierarchy, actual text, CSS declarations (including media/container conditions and variables), computed values, element/pseudo-element bounds, assets and font faces. Preserve the units and coordinate basis.
3. For long pages capture top/middle/bottom, lazy content, sticky states and first/middle/last repeated elements. Distinguish measured positions from a proven layout algorithm. Probe neighboring widths to establish breakpoints rather than infer one from three screenshots.
4. Before interaction identify the visible container, role/name, route and controlled region. Check uniqueness, visibility, nonzero geometry and enabled state using the actual UI. Duplicate names require container scope, not `.first()` or nth-guessing. A hidden 1×1 search input is not the visible search field.
5. Execute a bounded list of safe inputs: click/tap, hover/focus, Tab/Enter/Space/Escape, scroll, drag or media controls as applicable. Record before/after, focus, URL, panel state, input value and return/reset result. Do not force-click through overlays or change DOM to fake success.
6. If navigation fails or the route/title/container does not match, keep the failure and stop that branch. A browser network/challenge/error document is not an empty state of the source. Continue independent successful branches.

## Motion evidence

For CSS/WAAPI keep timing declarations and measured frames separately. For spring/scroll effects record solver or progress mapping only if supported by source; otherwise sampled frames and unknown parameters. Capture delay, duration, easing, iteration, direction, transform origin and competing transforms. Sample phase-aligned start/intermediate/end plus interruption/reversal and reduced motion. Test touch scrolling/dragging where scoped; mouse emulation alone is not native-device coverage.

观察等待只表示观察窗口；超过预算还没有控件，不等于该控件永远不存在。已有有效分支不重复采集，失败记录不删除。若两次同一路径失败，检查真实容器、路由、iframe 和就绪条件，再选择新证据；不无界等待。

## Known evidence traps

- Many same-named links can belong to navigation, a live demo, or a nested example. Record route plus controlled region before interpreting behavior.
- Count directory cards separately from nested demos and copy buttons. Occurrences are not necessarily unique components.
- A combined runner can exit unsuccessfully while some branch evidence remains valid. Preserve both the valid branch and global failure; do not label the entire capture passed.
- Input echo/expansion does not establish submitted search correctness. Source font-family declarations do not establish actual font files or glyph coverage.
