---
version: alpha
name: "Orbital study"
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

Header → #orbit canvas → Pause and Reset to still buttons → status text. Canvas has a 960×360 drawing buffer, 100% CSS width and 360px CSS height, changing to 260px at max-width 640px. Its opaque background is #183e32. Controls use the common 12px flex gap; status is 14px/1.6 Verdana.

Initial page copy (DOM order; includes initially hidden native content):

- 03 / Dynamic canvas
- Orbital study
- A deterministic orbit with live motion, pause, resume and a repeatable reset state.
- Pause
- Reset to still

## 3. Interactions

Normal mode starts Running. requestAnimationFrame advances phase by min(deltaSeconds,0.04)×0.6. Pause stops phase changes and changes the label to Resume/status to Paused; Resume restores phase updates. Reset to still sets phase=0 and paused=true. Reduced motion starts still and never advances phase while the preference is active. Each frame draws twelve dots: angle=phase+i*pi/6, radius=90+(i mod 3)*18, x=480+cos(angle)*radius*2.3, y=180+sin(angle)*radius; dot radius=8+(i mod 3)*3. Colors alternate #e4a26a for i mod 3=0 and #dce7c8 otherwise. Five states × three viewports verify moving baseline, pause, resume, reset and reduce. canvasChanging samples 180ms apart; this does not verify the full trajectory or animation timing.

## 4. Assets and implementation

Procedural asset: the actual generator module is the inline script in each complete HTML source. There are no external assets. Shared code makes a deterministic regression pair, not an independent reimplementation. Only reset/reduce are phase-aligned for raw pixel comparison.

Run output contains actual response files, hashes, screenshots and measurements in a new directory outside the Skill. Preserve the included source as the input; capture-generated DESIGN.md is a separate evidence draft.

## 5. Acceptance

Run examples/run_examples.py; scope.json enumerates required checks, capture-plan.json defines real inputs and observations. Desktop, tablet and phone cold-load separately. Static states use zero pixel difference within the same browser/environment; dynamic running frames have no pixel-equivalence claim. All required runtime and behavior checks must pass; an inactive initial state cannot prove suppression. Physical devices, blind-agent reconstruction and full timing/trajectory validation remain outside this example. Output ready_for_user_review is not user acceptance.
