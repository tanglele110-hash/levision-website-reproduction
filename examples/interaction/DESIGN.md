---
version: alpha
name: "Reading room"
description: "Original MIT example for repeatable capture and acceptance testing."
omitted:
  - "Real-device and independent blind-agent reconstruction are outside this regression example."
colors: {paper: "oklch(96% .018 90)", ink: "oklch(27% .035 155)"}
typography: {heading: {fontFamily: "Georgia, serif", fontSize: "56px", lineHeight: "1.05"}}
rounded: {control: "0px"}
spacing: {desktopGutter: "32px", phoneGutter: "20px", columns: "24px"}
components: {button: {minHeight: "44px", padding: "10px 18px"}}
---

## 1. Global rules

Source: reference/index.html; paired implementation: replica/index.html. Both are original MIT fixtures by 木渡川（Tanglele）, with intentionally shared tokens and behavior and differing section wrappers. This is a regression pair, not a blind reconstruction benchmark. All numerical specifications below are declarations from these included sources, checked against actual browser evidence during a run.

Viewports: 1440×1000, 768×1024, 390×844; DPR 1. Body has zero margin, paper oklch(96% .018 90), ink oklch(27% .035 155), Georgia/serif. Main width min(1120px, viewport - 64px), vertical margin 64px. At max-width 640px: width viewport - 40px, margin 32px, h1 38px. Otherwise h1 is 56px/1.05, weight 400, letter-spacing -.035em and margin 16px 0. Eyebrow is 600 12px/1.5 Verdana with .14em spacing. Paragraphs are 18px/1.6, max-width 640px. Header has a 1px #bbc6bb bottom border, 24px bottom padding and 40px bottom margin (28px on phone). Buttons are 15px/1.4 Verdana, min-height 44px, padding 10px 18px, 1px #859d8b border, square corners; hover background #d8e5d9.

## 2. Page regions

Header → Menu and controlled nav → Notes/Essays tablist → collection/filter/results panel → About this collection detail → Reading settings trigger → native dialog. Flex controls wrap with 12px gap and 24px vertical margin. Panels have a 1px #bbc6bb top rule, 24px vertical padding and 140px minimum height. Filter is min(100%,360px), with 12px padding and a 1px #859d8b border. Selected tab is #244c3a/white. Dialog has 32px padding, max-width calc(100% - 40px), #f5f4e9 background and #14261a66 backdrop.

Initial page copy (DOM order; includes initially hidden native content):

- 02 / Stateful components
- Reading room
- Open the menu, switch a collection, filter titles and return from the dialog.
- Menu
- Collections · Reading list
- Notes
- Essays
- Notes collection
- Space / Type / Rhythm
- About this collection
- Short observations, kept together for future reference.
- Reading settings
- Reading settings
- This dialog restores focus when it closes.
- Close

## 3. Interactions

Menu starts aria-expanded=false and nav hidden; each activation toggles both. Tabs select Notes (Space / Type / Rhythm) or Essays (Attention / Memory); selection changes aria-selected and heading. The text filter is case-insensitive; zzzz yields No matching titles. Detail toggles its expanded attribute and explanatory paragraph. Reading settings uses showModal(); Close or Escape closes it and restores focus to #open-dialog. Native focus outline is 3px #d17036 with 3px offset. There are no CSS transitions. Twenty-one cases cover seven states × three viewports; a separate negative fixture makes the menu inert to check failure detection.

## 4. Assets and implementation

Self-contained HTML/CSS/JavaScript; no downloaded images, fonts or media. Native dialog behavior comes from the browser. Source event handlers and capture-plan.json identify the exact targets and observed values.

Run output contains actual response files, hashes, screenshots and measurements in a new directory outside the Skill. Preserve the included source as the input; capture-generated DESIGN.md is a separate evidence draft.

## 5. Acceptance

Run examples/run_examples.py; scope.json enumerates required checks, capture-plan.json defines real inputs and observations. Desktop, tablet and phone cold-load separately. Static states use zero pixel difference within the same browser/environment; dynamic running frames have no pixel-equivalence claim. All required runtime and behavior checks must pass; an inactive initial state cannot prove suppression. Physical devices, blind-agent reconstruction and full timing/trajectory validation remain outside this example. Output ready_for_user_review is not user acceptance.
