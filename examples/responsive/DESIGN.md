---
version: alpha
name: "Field notes"
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

Header, full-width SVG, then Space / Type / Rhythm cards. SVG is 640×280, rendered at 100% width × 140px with object-fit: cover and a 24px bottom margin. Grid has three equal columns / 24px gap, switching to one column / 32px gap at max-width 640px. Each card has a 2px #244c3a top border, 20px top padding, a 26px heading and 16px body text.

Initial page copy (DOM order; includes initially hidden native content):

- 01 / Responsive composition
- Field notes
- A small collection for observing space, type and rhythm across screen sizes.
- Space
- A consistent outer margin keeps every block connected to the page.
- Type
- The same words reveal changes in line length and wrapping.
- Rhythm
- Three columns become one when the reading space gets narrow.

## 3. Interactions

This page has no interactive controls or animation. The three cold-load cases verify actual heading text, grid geometry and SVG decode. The required asset check also compares swatches.svg bytes. Do not add invented controls or motion.

## 4. Assets and implementation

Original asset swatches.svg exists on both sides. Its two shapes are a green circle and terracotta square over a pale green field. The HTML and SVG are complete local sources; there are no remote dependencies.

Run output contains actual response files, hashes, screenshots and measurements in a new directory outside the Skill. Preserve the included source as the input; capture-generated DESIGN.md is a separate evidence draft.

## 5. Acceptance

Run examples/run_examples.py; scope.json enumerates required checks, capture-plan.json defines real inputs and observations. Desktop, tablet and phone cold-load separately. Static states use zero pixel difference within the same browser/environment; dynamic running frames have no pixel-equivalence claim. All required runtime and behavior checks must pass; an inactive initial state cannot prove suppression. Physical devices, blind-agent reconstruction and full timing/trajectory validation remain outside this example. Output ready_for_user_review is not user acceptance.
