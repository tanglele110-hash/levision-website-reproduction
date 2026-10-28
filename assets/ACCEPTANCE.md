# 复刻验收 / Reproduction acceptance

- Scope/version and input hashes:
- Implementation mode (source localization / evidence reimplementation), license evidence and pinned-source/deployment comparison when applicable:
- Implementation directory/version and startup command:
- Actual browser URL and owning process:
- Browser/OS, viewport/DPR/input, font readiness, state/scroll/time:
- Readiness conditions (resources / visible scene / action in progress / target complete), observations and timeout outcome:
- Predetermined tolerances and excluded requirements:

| ID | Requirement / state | Source evidence | Implementation evidence | Conditions | Result | Measured difference / recovery |
| --- | --- | --- | --- | --- | --- | --- |

## Visual and motion review

Link original captures, actual captures, difference images and measurements. Record real visual review separately from metrics. Describe phase alignment, intermediate frames, interruption, reversal and reduced motion. For dynamic scenes record randomness, wall/simulation time, actual rendering ratio and any explicit test instrumentation; separate ordinary runs from deterministic experiments and frame equivalence from state/layout agreement.

List relevant CSS and JS responsive conditions separately, including operators, device capabilities and cold-load/resize differences; link boundary probes. If using presentation frames, record the internal viewport and direct page URL separately from the scaled display size.

## Behavior and resources

Record real inputs, assertions, back/reset/focus results, console/network errors, asset decode/glyph checks. Mark emulated versus real touch devices and untested backend states.

| Suppression check | Source expectation evidence | Proven active baseline | Actual input | Observed change | Restoration if applicable | Result / missing evidence |
| --- | --- | --- | --- | --- | --- | --- |

An already absent animation is not proof that reduced motion works. Retain wrong-expectation failures and evidence for their correction. Include procedural generator modules, exact dependencies and license notices in the asset inventory when used.

## Decision

Document / asset integrity / visuals / behavior / motion / runnable delivery: report each separately. Summarize compared, failed, unverified and not-applicable checks. State complete-within-scope only when all required layers pass; otherwise list remaining omissions, impact and recovery conditions. Do not rewrite frozen inputs with later findings.
