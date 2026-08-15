# Design rules

How anything this project draws on screen is allowed to look.

> **Ownership.** This file and `docs/design/` belong to design. Development
> seeded it on 15 August 2026 with the token facts measured on the reference
> machine, so that design proposes against real numbers instead of against a
> screenshot. Add to it; do not silently rewrite the measured sections.

Everything in "What Omarchy actually gives us" was **measured** on the reference
machine on 15 August 2026 against omarchy `4.0.0-1`. Everything about Material
Design is **derived** from Google's published specification, gathered the same
day; none of it has been rendered here yet. Everything else is judgement, and
says so. See [conventions](conventions.md).

---

## The one design rule

**Omarchy owns the frame. The Pixel owns what is inside it.**

Geometry, palette, type and spacing come from the active Omarchy theme at
runtime, without exception. Pixel identity is expressed in the *content* layer —
which device this is, what it is doing, how that state reads at a glance — and
nowhere else.

The failure this rule exists to prevent is the obvious one: a widget that looks
like an Android app was pasted into the bar. That widget is wrong even when it is
beautiful, because the user picked their theme and we overrode it. The opposite
failure is just as real and less discussed: a Pixel that shows up as an anonymous
grey glyph indistinguishable from a USB stick. Neither is the goal.

The test to apply to any surface: **switch the theme to something violent and
look again.** If the surface still belongs, the frame is right. If you can still
tell at a glance that the thing on the other end is a Pixel, the identity is
right. Both have to hold at once.

---

## What Omarchy actually gives us

Measured, 15 August 2026, omarchy `4.0.0-1`, Hyprland 0.56.2.

The shell is a single Quickshell process. Two singletons in `qs.Commons` hold
every token: `Color` for palette, `Style` for everything else. Read them. Never
restate their values as literals.

### Palette roles

`Color` exposes five foundational roles — `foreground`, `background`, `accent`,
`urgent`, `muted` — plus per-surface groups that themes can override
independently: `Color.bar.*`, `Color.popups.*`, `Color.tooltip.*`,
`Color.notifications.*`, `Color.menu.*`, `Color.lock.*`, `Color.polkit.*`.

A theme's `colors.toml` also carries terminal colours (`red`, `green`, `cyan`,
`blue`, `magenta`, `yellow`, and `bright_*`). Those are the only named hues
available, and a theme is free to make them all approximately the same colour.
Measured example — the theme in use here, Last Horizon, resolves `blue` to
`#b59790`, a warm rose. **A rule that depends on blue being blue is broken.**

Five of the 39 stock themes are `mode = "light"`: `catppuccin-latte`,
`flexoki-light`, `white`, `rose-pine`, `lupine`.

### Geometry

| Token | Where it comes from | Measured here |
|---|---|---|
| `Style.cornerRadius` | Hyprland `decoration:rounding`, re-read on theme change | 8 |
| `Style.gapsOut` | Hyprland `general:gaps_out` halved by the shell | 10 → 5 |
| Window border | Hyprland `general:border_size` | 2 |
| `Style.bar.sizeHorizontal` | `[bar]` in theme `shell.toml`, scaled by font | 26 |
| `Style.bar.iconSlot` / `iconCanvas` / `iconFont` | same | 27 / 16 / 13 |

Corner radius is a **single value for the whole desktop**, set by the user's
compositor config. There is no shape scale to opt into.

### Spacing

`Style.space(px)` is the shell's rem. Tokens: `hairline` 1, `xxs` 2, `xs` 3,
`sm` 4, `md` 6, `lg` 8, `xl` 10, `xxl` 12, `xxxl` 14, `huge` 18, plus control
tokens (`controlHeight` 28, `controlPaddingX` 10, `controlPaddingY` 6,
`rowPaddingX` 12, `panelPadding` 18, `popupPadding` 14). All multiply by
`[spacing] scale` and, by default, track the font size.

### Typography

Base size 12. The scale is multiplicative from it: `caption` 0.833, `bodySmall`
0.917, `body` 1.0, `subtitle` 1.083, `title` 1.167, `heading` 1.333, `display`
2.0, `displayLarge` 2.333, with `iconSmall` / `icon` / `iconLarge` aliased on
top.

The family is the fontconfig alias `monospace`, which `omarchy font set`
rewrites system-wide. Measured here: `JetBrainsMono Nerd Font`.

**No stock theme ships a `shell.toml`.** Every theme on this machine therefore
runs the default type scale, the default spacing scale and the default bar
dimensions; only `tokyo-night` ships a `shell.lock.toml`, and only for lock
screen colours. Consequence for design: the scale above is not a suggestion that
themes routinely override, it is what everybody is looking at.

### State layers

`Style` already implements state layers as alpha over a role colour — the same
idea Material calls a state layer, with different numbers.

| State | Fill alpha | Border alpha | Border width |
|---|---|---|---|
| normal | 0.04 | 0.40 | 1 |
| hover / keyboard cursor | 0.08 | 0.25 | inherits normal |
| selected | 0.18 | 1.00 | 0 |
| pressed | 0.22 | — | — |
| focus | inherits hover | inherits hover | inherits hover |
| text selection | 0.35 | — | — |

Priority chain, already written for you: `Style.controlFill(focused, hot, fg,
accent)`, `controlBorder(...)`, `controlBorderWidth(...)`.

### Motion

Measured by inventorying every animation in the shell source:

- 38 `NumberAnimation`, 14 `ColorAnimation`, 0 `SpringAnimation`. **There is not
  one spring in the Omarchy shell.**
- Easing is overwhelmingly `Easing.OutCubic` (26 uses), then `OutQuad` (7),
  `InOutCubic` (5).
- Durations cluster at 140 ms (10 uses), 160, 120, 180 and 260 for interaction
  feedback; the few values above 600 ms are ambient, not response.

### The component kit

`qs.Ui` ships 33 components: `Button`, `ButtonGroup`, `Toggle`, `ToggleSwitch`,
`TextField`, `NumberField`, `Dropdown`, `SearchableDropdown`, `MultiSelect`,
`Panel`, `PanelHero`, `PanelSlider`, `PanelSectionHeader`, `PanelSeparator`,
`PanelActionButton`, `PanelToolTip`, `PopupCard`, `ConfirmDialog`,
`BarWidget`, `BarIconButton`, `BarIndicator`, `WidgetButton`, `OpticalGlyph`,
and the border/cursor plumbing.

`WidgetButton` alone handles bar slot sizing, vertical bars, tooltips, press
registration, dimming, concealment and the reveal animation. `OpticalGlyph`
exists because glyph bounding boxes lie: it corrects horizontal painted bounds
while preserving the shared baseline.

**Rule: if a `qs.Ui` component exists for it, use it.** A hand-rolled
`Rectangle` is how a widget stops matching the desktop three theme updates from
now, and it is how you lose vertical-bar support without noticing.

---

## What Material Design 3 gives us

Derived from Google's specification, 15 August 2026. Not rendered here yet.

- **Colour** is tonal: roles (`primary`, `on-primary`, `primary-container`,
  `surface`, `surface-container-*`, `outline`, `error`) generated from tonal
  palettes, optionally sourced from the wallpaper (dynamic colour / Material
  You).
- **State layers** are alpha overlays in the content colour: hover 8 %, focus
  10 %, pressed 10 %, dragged 16 %.
- **Shape** in M3 Expressive is a 10-step corner scale from square to full, plus
  a library of around 35 shapes with animated morphing between them.
- **Motion** in M3 Expressive is physics-based: spatial springs for position,
  size and rotation, effect springs for colour and opacity, each in fast /
  default / slow, under either a standard scheme or an expressive scheme with
  deliberate overshoot.
- **Type** is a role scale — display, headline, title, body, label, each in
  large/medium/small — set in Google Sans on Pixel, Roboto elsewhere.
- **Targets** are physical: 48 dp minimum for touch.

Fonts, licensing checked the same day: Roboto and Roboto Flex are under the SIL
Open Font License; Google Sans Flex has been released under the OFL as well.
Material Symbols is packaged for Arch as `extra/ttf-material-symbols-variable`
(a four-axis variable font, in the official repositories, measured available —
not installed here). `ttf-roboto` is also in `extra`. Google Sans is AUR-only
(`ttf-google-sans`, `ttf-google-sans-code-vf`).

---

## Where the two systems agree

More than the visual gap suggests. Both are token systems of the same shape:
role-based colour rather than named colour, a multiplicative type scale off one
base, and interaction states expressed as alpha over the content colour rather
than as separate palettes.

So the hybrid is a **mapping, not a merge**. Design in Material's vocabulary if
that is how you think, then resolve every token through this table before it
reaches QML.

| Material concept | Resolves to |
|---|---|
| `surface`, `surface-container-*` | `Color.background`, or the surface group (`Color.popups.background`, `Color.bar.background`) |
| `on-surface` | `Color.foreground` |
| `primary` / `secondary` | `Color.accent`. There is one accent; there is no secondary |
| `error` | `Color.urgent` |
| `outline`, `outline-variant` | `Style.normalBorderColor` / `Style.hoverBorderColor` |
| Disabled / de-emphasised | `Color.muted`, or `dimmed` on `WidgetButton` (opacity 0.45) |
| State layer, hover 8 % | `Style.hoverFill` (0.08 — the same number) |
| State layer, pressed 10 % | `Style.pressedFill` (0.22 — deliberately stronger) |
| Elevation level 1–5 | Nothing. See below |
| Corner `xs`…`full` | `Style.cornerRadius`, the one value |
| Type role `body-medium` etc. | `Style.font.body` and neighbours |
| Spacing 4 dp grid | `Style.space(px)` |
| 48 dp touch target | The bar slot. This is a pointer desktop |

---

## Where they conflict, and who wins

| Axis | Ruling |
|---|---|
| **Colour** | Omarchy, absolutely. No Google Blue, no `#4285F4`, no dynamic colour extracted from the wallpaper, no tonal ramp. The theme's accent is the only chromatic colour a surface gets |
| **Elevation** | Omarchy. This shell has no shadows and no tonal surfaces; depth is a 1 px border at 40 % and a 4 % fill. Do not introduce shadow |
| **Shape** | Omarchy for every container. Material's shape scale is unavailable — there is one radius, and the user set it in their compositor config |
| **Typography** | Omarchy, family included. Do not ship Google Sans or Roboto into a widget. See the argument below |
| **Icons** | Split. See below |
| **Motion** | Omarchy for everything reactive: `OutCubic`, 120–180 ms. No overshoot, no bounce, no spring in the bar. See the exception below |
| **Density** | Omarchy. A 26 px bar is not a phone |

### On typography, specifically

This is the rule most likely to be argued with, so: **the family stays
monospace, everywhere, no exceptions.**

The family is a system-wide fontconfig alias that the user chose with `omarchy
font set`. A widget that hardcodes a proportional face is not "on brand", it is
the one element on the desktop that ignored the user. And it will look it —
`Style.font.*` sizes are tuned to a 12 px monospace metric, and the bar aligns
glyphs on a shared baseline through `OpticalGlyph`.

Pixel typographic identity, to the extent it survives this, is carried by the
**scale and rhythm**, not the family: generous size contrast between a value and
its label, one weight per surface, numerals given room. That is available inside
`Style.font`.

### On icons, specifically

Material Symbols is the one piece of Google's visual language worth importing,
because it is the actual iconographic vocabulary of the device on the other end
— and because a Pixel drawn as a Nerd Font phone glyph reads as "a phone", not
as "your phone".

Rules:

1. Material Symbols is used **only for Google-device and Google-feature
   concepts** (the phone, the buds, a share, a cast). Everything else — network,
   volume, battery chrome, status — uses whatever the rest of the bar uses.
2. Draw it through `OpticalGlyph` at `Style.bar.iconFont`, in a palette role
   colour, so it sits on the shared baseline and inherits the theme.
3. Outlined weight only, to match the line weight of the surrounding bar. Never
   filled, never multi-colour.
4. **It is an optional dependency.** `ttf-material-symbols-variable` is not
   installed on the reference machine and cannot be assumed anywhere. Every
   icon needs a declared Nerd Font fallback glyph, and the widget must be
   verified with the font absent. A tofu box in the bar is a shipped bug.
5. No bitmaps. Ever. They cannot be recoloured by the theme.

### On motion, specifically

The measured baseline is 140 ms `OutCubic` and no springs. Match it for every
state change, hover, reveal and value update.

One exception is available and it is a budget, not a licence: **a single
completion moment** — a transfer finishing, a pairing succeeding — may use a
slightly expressive curve, still under 260 ms, still without overshoot past the
resting value in the bar. If two surfaces both claim the exception, neither gets
it.

---

## Where the Pixel is allowed to be a Pixel

The identity budget, in full. Anything not on this list gets the Omarchy
treatment.

1. **The device glyph.** A Material Symbol, per the icon rules above.
2. **The device's own name** as the phone reports it, not a generic label.
3. **Progress and state shapes** for Google-specific operations — the shape of a
   transfer indicator, the arrangement of per-bud battery — may follow
   Material's arrangement, drawn in theme colours.
4. **Brand marks** (a Quick Share mark, the four-colour Google mark) are allowed
   in `preview.png`, the plugin README and the About surface. **Never in the
   bar, never in a panel, never in a notification.**

The rule of one accent holds throughout: `Color.accent` is the only chromatic
colour on a surface. Success and failure use `Color.urgent` and the theme's own
`green`/`red` roles if they must, never Material's error/success ramp — and
never hue alone, because the theme may resolve them to the same colour. **State
is always encoded by glyph or text as well as by colour.** This is the
accessibility rule here, and it exists because we do not own the palette and
therefore cannot promise contrast.

---

## Designing against the matrix, not against the catalogue

`docs/features.md` is a catalogue of targets, derived. `docs/02-capability-matrix.md`
is what has been measured. **Design against the matrix.**

The concrete case, already visible: a battery widget showing left bud, right bud
and case is exactly what Apple does and exactly what the catalogue asks for. But
standard AVRCP yields **one combined figure**, and three figures depend on
`pbpctrl` — 482 days without an update, targeting first-generation Buds Pro —
talking to Buds Pro 2 that are not its target. Design a three-figure layout as
the base case and the widget has been designed for data that may never exist.

So: **one combined figure is the base layout. The split is an enhancement that
the layout absorbs without reflowing.** Generalise that into the standing rules:

- Every surface declares its appearance for: capability untested, tool absent,
  daemon not running, data partial, device unreachable.
- **Never render a plausible zero.** No data means unknown, drawn as unknown.
  A widget showing `0 %` for a battery it could not read is the worst output
  this project can produce, because it is a measurement bug wearing a UI.
- Prefer disappearing to lying. A widget with nothing true to say should
  conceal itself (`WidgetButton` has `concealed` and `keepSpace` for exactly
  this) rather than sit there grey.
- No indeterminate spinner without a timeout and a resulting message. Every
  failure found during bring-up was silent; silence is this project's
  characteristic failure and the UI must not add to it.
- **Never draw a subsystem's self-reported status. Draw the observable
  effect.** A widget saying "connected" because BlueZ says `Connected: yes` is
  a plausible-looking zero wearing a different hat. Ask what the user would
  check to know it worked — an input node, a file, a pixel — and show that.
- When design needs a datum that has not been measured, mark it as an
  assumption and say so out loud. Do not promote anything to
  `data/capabilities.toml` — that is development's, and only when a capability
  enters a phase.

---

## Surfaces and the capabilities they assume

Machine-checked. Every id below is a join key into `data/capabilities.toml`; the
matrix cells themselves come from device reports in `data/devices/`.

**Reliance** is a claim this document makes and the test enforces:

- `enhancement` — the surface must be fully usable without this capability. The
  fallback column says what it looks like when the capability is absent, its
  tool is missing, or nothing has measured it yet. **This is the only legal
  value while a capability is unmeasured.**
- `required` — the surface has no meaning without it. Only legal once the matrix
  shows the capability measured `works` or `partial` on real hardware.

Today every row is `enhancement`, because today nothing is measured. A row that
turns `required` before its capability does is the failure mode this table
exists to catch.

<!-- design-assumptions: one capability id per row; ids must exist in data/capabilities.toml -->

| Surface | Capability id | Reliance | When absent or unmeasured |
|---|---|---|---|
| Earbud battery readout | `buds-battery` | enhancement | Widget conceals itself. Never a zero, never a grey placeholder |
| Per-earbud and case split | `buds-battery` | enhancement | One combined figure in the same layout. No reflow when the split appears |
| ANC control | `buds-anc` | enhancement | Control is not drawn at all. Not drawn disabled |
| Equaliser control | `buds-eq` | enhancement | Not drawn |
| Send-to-phone action | `file-send` | enhancement | Action absent from menu and keybinding. No dead entry |
| Incoming transfer surface | `file-receive` | enhancement | No surface. A transfer that cannot be observed is not announced |
| Phone notification surface | `notifications` | enhancement | Not drawn |
| The bar widget itself | `bar-widget` | enhancement | Nothing on the bar; the CLI stays the interface |
| Keybindings | `hotkeys` | enhancement | Unbound. A bound key that does nothing is worse than no binding |
| Omarchy menu entry | `menu-entry` | enhancement | No entry |

Surfaces for `clipboard`, `sms`, `screen-mirror`, `remote-input` and everything
in F5 are deliberately absent: no design has been proposed for them, and absent
means untested here too.

### Failure states are not capabilities

A transfer can stall, be rejected, time out, or find no peer. Those are **states
of `file-send` and `file-receive`**, not capabilities of their own, and they get
no rows above. Inventing `transfer-rejected` as an id would break the join key
the whole matrix hangs on, and the test that checks this table would be right to
fail. The vocabulary lives here instead:

| State | The user must be able to tell | Must not be drawn as |
|---|---|---|
| Transferring | That it started, and that it is still moving | A bar that could be stuck. Show movement or show elapsed time |
| Rejected | That the other end said no — a decision, not a fault | An error. Nothing is broken |
| Failed | That it stopped, and at whose end | A generic failure with no side named |
| Timed out | That nothing answered, and for how long we waited | An indefinite spinner. That is the state this replaces |
| No peer | That discovery found nothing, not that nothing exists | An empty list. Empty reads as "none available", which is a claim |

Each of these has to be producible on demand before it can be designed, which is
what the emulator's deliberate failure modes are for. And the corollary to the
provenance rule holds in both directions: **a failure produced by the emulator
is not a measured failure either.** It is measured against the emulator, and it
will be the first thing forgotten, because a convincing error persuades harder
than a convincing success.

### Simulated data must look simulated

A virtual Quick Share peer is planned so the transfer path can be exercised
without the phone. The design constraint that comes with it is not optional:
**a simulated peer must be visibly simulated on every surface that draws it**,
and the marking must survive a screenshot.

The reason is not purity. Someone will paste a screenshot of a working transfer
into an issue, a README or a hardware report, and if the virtual peer renders
identically to a real Pixel, that image becomes evidence for something nobody
measured. This project's one rule dies at exactly that moment, in the one
artefact that travels furthest.

So: a distinct label in the peer's name, not a subtle tint. Never the device
glyph a real Pixel gets. And any status line derived from the emulator says so
in words. The same applies to fixtures and mock data used while iterating on a
widget: if it can be screenshotted, it can be mistaken for a measurement.

A surface cannot mark what the data does not tell it, so provenance has to
arrive in the status contract — a `simulated` flag, a `provider` field, whatever
backend settles on. Which raises the case nobody has ruled on yet, and it is the
one that decides whether the rule holds: **when the provenance field is absent,
the surface must not assume real.** Absent is unknown, and unknown is drawn as
unknown — the same way an untested capability is. Failing the other way means an
old emulator build, a replayed fixture or a truncated payload renders as a
measured Pixel, which is the exact image that ends up in an issue.

### Why that rule is not paranoia

Four instances turned up on this machine in a single day, 15 August 2026. Two
were measured here in the course of this document; the other two came out of the
Bluetooth work the same night.

| The tool said | What was actually true |
|---|---|
| `Local plugin changed, reloading` | Nothing reloaded. The old component kept rendering |
| `coredumpctl`: core `inaccessible` | Three cores on disk, `root:root 0640`. Unreadable by this user, not missing |
| `bluetoothctl`: `le-connection-abort-by-local` | The HID was already attached |
| BlueZ: `Connected: yes` | No input node existed |

Four in a day is not anecdote. **What a tool reports is not evidence of what it
did.** Every one of these would have produced a confident, wrong widget if a
surface had rendered the status string it was handed.

## The design has to survive leaving Omarchy

[Packaging](05-packaging.md) is explicit that the final product cannot assume
Omarchy, Hyprland or systemd. The first implementation is an Omarchy plugin
anyway, and that is fine — but it means:

- **The interaction model, not the QML, is the deliverable.** What the user
  does, what they see, what happens when it fails. That has to be expressible as
  a CLI plus a generic tray icon and a freedesktop notification, on a desktop
  with no Quickshell in it.
- **The token mapping lives in this file**, not only in component code, so a GTK
  or generic-tray implementation resolves the same decisions against a different
  system.
- **The tray is not a delivery surface here.** Measured in F1: `rquickshare`
  registers a StatusNotifierItem correctly and Quickshell picks it up, but
  Omarchy's tray module keeps unpinned items in a collapsed drawer behind a
  chevron — the icon is live and invisible. Anything that has to be seen is a
  bar widget. The tray is a fallback for desktops that have nothing better,
  never the surface here. See [roadmap F1](03-roadmap.md).
- Where Omarchy gives us a token and a foreign desktop does not, this file names
  the fallback. Current fallbacks, judgement: radius 8, spacing base 4, one
  accent from the desktop's own accent setting where one exists, monospace UI
  font, 140 ms ease-out.

---

## Process rules

- **Validate before proposing:** `omarchy plugin validate <folder>`. A plugin
  needs `manifest.json` with `schemaVersion: 1`, `kinds` and `entryPoints`.
- **Ship a `preview.png`.** Every plugin in `~/.config/omarchy/plugins/` has one;
  it is how a widget is chosen.
- **Test on at least three themes** before calling a surface done: one dark
  (Last Horizon is the reference), one light (`catppuccin-latte`, `white`,
  `flexoki-light`, `rose-pine` or `lupine`), and one hostile — a theme whose
  accent has almost no contrast against its background.
- **Test with `bar.transparent: true`**, which is the reference machine's
  setting. A surface designed against an opaque bar can vanish.
- **Test on an ultrawide.** The reference monitor is ultrawide; the bar's centre
  section is a long way from its right section. Do not design a relationship
  between two widgets that only reads when they are adjacent.
- **Test the vertical bar.** `WidgetButton` supports it; a widget that assumes
  horizontal breaks silently for anyone who moved their bar.
- **Test with the icon font absent**, per the icon rules.

### Iteration cost — measured

Measured 15 August 2026, omarchy `4.0.0-1`. Omarchy's documentation states that
saving any file under `~/.config/omarchy/plugins/` reloads plugin code
automatically. **On this build it does not.**

Method: a throwaway bar widget rendering the literal `PROBE-A`, enabled on the
bar, then its QML edited to `PROBE-B` with the shell left running. Evidence is
`grim` captures of the bar plus the shell's journal — not impressions.

| Step | Result |
|---|---|
| Add the plugin to `shell.json` | Widget appears live. No restart |
| Edit the QML and save | Shell logs `Local plugin changed, reloading: local.hotreload-probe`. Bar still renders `PROBE-A` |
| Wait 23 s | Still `PROBE-A`, on both monitors |
| `omarchy-shell shell rescanPlugins` | Still `PROBE-A` |
| Disable, then re-enable the widget | Still `PROBE-A` |
| `omarchy restart shell` (confirmed new PID) | `PROBE-B` |
| Remove the plugin from `shell.json` | Widget disappears live. No restart |

**Layout hot-reloads. Code does not.** The last two rows are the falsification
test and the control: the probe was capable of rendering `PROBE-B` all along,
and `shell.json` really is live.

`~/.cache/quickshell/qmlcache` is written at the moment of the logged reload,
which is consistent with the engine reusing a compiled component. That
explanation is **not reproduced** and is not needed for the conclusion.

Three consequences, and the third is a design rule rather than a workflow note:

- **Every QML change costs a shell restart.** Batch visual work; do not tune one
  value at a time.
- **The log lies about it.** The shell says `reloading` and nothing reloads.
  Verify against pixels, never against the journal.
- **Anything a user might tune belongs in the manifest `schema`, not in a QML
  constant.** Settings in `shell.json` apply live; code does not. A widget whose
  knobs are hardcoded is a widget nobody can adjust without restarting their
  desktop.

---

## Acceptance checklist

A surface is not done until every line is true.

1. Every colour resolves through `Color.*`. No hex literal outside a declared
   fallback.
2. Every dimension resolves through `Style.space()`, `Style.font.*`,
   `Style.bar.*` or `Style.cornerRadius`. No magic number.
3. Interaction states use `Style.controlFill` / `controlBorder` /
   `controlBorderWidth`, not hand-written alphas.
4. It is built from `qs.Ui` components wherever one exists.
5. Motion is `OutCubic`, 120–180 ms, no spring — or it is the one budgeted
   completion moment and says so in review.
6. Identity is confined to the four items in the identity budget.
7. State is legible without colour.
8. Untested, absent, down, partial and unreachable each have a defined
   appearance, and none of them is a plausible-looking zero.
9. It has been seen on a dark theme, a light theme and a hostile theme, on the
   ultrawide, with a transparent bar, and with the icon font uninstalled.
10. It degrades to something describable outside Omarchy.
11. Every user-tunable value is in the manifest `schema`, not a QML constant.

---

## Open questions, for measurement

Nobody should design around these until they have an answer.

- Does Material Symbols render correctly through `OpticalGlyph`, given
  `Text.NativeRendering` and a four-axis variable font behind a fontconfig
  lookup? Does the optical axis survive at 13 px?
- Is `Color.accent` legible against a transparent bar over an arbitrary
  wallpaper, or does the bar need its own contrast floor?
- What does the buds widget actually have to render — one figure or three? This
  is F3 and it is the riskiest phase in the project.

## Sources

Derived material gathered 15 August 2026:

- [Material Design 3 — States](https://m3.material.io/foundations/interaction/states/applying-states)
- [Material Design 3 — Motion](https://m3.material.io/styles/motion/overview/how-it-works)
- [Material 3 Expressive: components, motion, shapes](https://supercharge.design/blog/material-3-expressive)
- [googlefonts/roboto-flex](https://github.com/googlefonts/roboto-flex) — OFL 1.1
- [Google Sans Flex released for free download](https://www.androidauthority.com/google-sans-flex-free-3617034/)

Measured material read from omarchy `4.0.0-1` on the reference machine:
`/usr/share/omarchy/shell/Commons/{Color,Style}.qml`,
`/usr/share/omarchy/shell/Ui/`, `/usr/share/omarchy/themes/*/colors.toml`,
`hyprctl getoption`, `fc-match`, `pacman -Ss`.
