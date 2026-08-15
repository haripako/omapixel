# Roadmap

Each phase starts with something concrete and ends with something checkable.
Nothing moves on until the previous phase has actually been measured.

Checkboxes here track the **reference machine** (see
[reference setup](04-reference-setup.md)). Other people's hardware is tracked in
the [capability matrix](02-capability-matrix.md) instead, which is generated
from device reports.

## F0 — Inventory and environment

In: a clean machine and this repository.
Out: knowing exactly what hardware is here and what is missing.

- [x] Run `scripts/hw-report.sh` and record the result
- [x] Record which Google devices actually exist (Pixel 7 Pro on hand, Pixel 11 Pro and Pixel Buds Pro 2 on the way; Android 17)
- [x] Pick a licence, language and contribution model so the repo can be published
- [x] Confirm the phone and the PC are on the same subnet (hard requirement for Quick Share)
- [ ] Pair the buds over Bluetooth and record the MAC — blocked until the hardware arrives

**F0 is closed as far as the phone goes.** The remaining box needs hardware that
has not arrived and blocks neither F1 nor F2.

## F1 — File transfer

In: F0 closed.
Out: sending and receiving from the Pixel without a cable.

- [ ] Install `r-quick-share` from the AUR
- [ ] Test receiving PC ← phone and sending PC → phone
- [ ] Measure the discovery problem: how many attempts until the device appears, and whether having the phone's screen on helps
- [ ] Verify the tray indicator under Hyprland with the Quickshell bar
- [ ] If autostart is needed, set it up as a user service

Testable in full on the Pixel 7 Pro. Does not wait for the Pixel 11 Pro.

## F2 — Clipboard and notifications

In: F1 working.
Out: copy on the phone, paste on the PC.

- [ ] Install `kdeconnect` and the Android app
- [ ] Pair and validate: clipboard both ways, notifications, SMS
- [ ] Verify the clipboard under Wayland (`wl-clipboard`)
- [ ] Decide how the daemon starts in the Hyprland session
- [ ] Check whether the tray icon coexists with the bar

Also testable in full on the Pixel 7 Pro.

## F3 — Pixel Buds

In: the buds paired.
Out: battery and ANC from the desktop.

- [ ] Install `pbpctrl` from the AUR (482 days without an update — it may not build)
- [ ] Find out which buds model responds and which fields come back
- [ ] If `pbpctrl` is dead, evaluate `budslink-git` and whether it has added Pixel Buds
- [ ] Wrap the battery read in a stable script the bar can consume

**Blocked on hardware, and the riskiest phase.** pbpctrl targets the first
generation Pixel Buds Pro; the Pro 2 use a different SoC, so the proprietary
protocol may not match. Nothing here is assumed until it prints on a terminal.

## F4 — Omarchy integration (where the original work starts)

In: F1 to F3 producing data on the command line.
Out: all of it visible and usable from the desktop.

- [ ] Bar plugin: buds battery and phone status
- [ ] Hyprland keybindings: cycle ANC, send the selected file to the phone
- [ ] Entry in the Omarchy menu
- [ ] Package the plugin following `manifest.json` and `omarchy plugin validate`

The plugin scaffolding can be built against fake data before F3 lands, which is
worth doing given the QML restart cycle.

## F5 — Research (no promise anything comes of it)

- [ ] Fast Pair: is there a public specification for the *provider* side? Is it worth anything without Google Play Services?
- [ ] Cross-device services: is the traffic observable? Is it tied to device attestation?
- [ ] Decide honestly whether this is viable, or close the door and document why

## The project's principle

Before writing your own code, check it does not already exist. And before
calling a feature done, measure it against real hardware — not against somebody
else's README.
