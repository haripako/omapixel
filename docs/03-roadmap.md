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

- [x] Install `r-quick-share` from the AUR — `r-quick-share 0.11.5-5`, built from source
- [ ] Test receiving PC ← phone and sending PC → phone
- [ ] Measure the discovery problem: how many attempts until the device appears, and whether having the phone's screen on helps
- [x] Verify the tray indicator under Hyprland with the Quickshell bar
- [ ] If autostart is needed, set it up as a user service

Testable in full on the Pixel 7 Pro. Does not wait for the Pixel 11 Pro.

> **Blocked on an upstream bug, 2026-08-16.** The three unchecked boxes above
> cannot be measured on this machine right now, and the reason is not ours.
> Launching `rquickshare` turns on LE discovery with a UUID filter, and BlueZ
> 5.87 crashes the moment a received advertisement matches one — measured here
> from three core dumps with an identical backtrace, and fixed upstream in
> [`82af2be`](https://github.com/bluez/bluez/commit/82af2be), six days after the
> 5.87 tag. No release carries the fix yet, so **F1 waits for BlueZ 5.88**.
> Details, backtrace and dates in
> [docs/04-reference-setup.md](04-reference-setup.md).
>
> Three ways around it were considered and dropped on 2026-08-16. Recompiling
> BlueZ, or patching the `rquickshare` binary, would put a package outside the
> package manager on the reference machine — and this project's whole claim is
> that what is measured here reproduces on an ordinary Arch. Living with the
> crash would mean measuring on a system restarting underneath the measurement.
> The work that does not need the radio continues meanwhile.

### The tray indicator works, and is invisible anyway

Measured 2026-08-15, and worth reading before designing anything around a tray
icon. On launch, `rquickshare` registers a StatusNotifierItem correctly and
Quickshell picks it up: the watcher goes from one registered item to two, and the
new one resolves to the `rquickshare` process, `Status: Active`, with a menu
object exposed. So the answer to "does the tray work under Wayland", which no
upstream documentation covered, is **yes**.

It is still not visible on the bar. Omarchy's tray module splits items into
**pinned** and a **collapsed drawer**, and the drawer starts shut behind a
chevron. An unpinned application is registered, live, and hidden.

Two consequences:

- Nothing here is broken, so this is not a bug to file upstream.
- **A tray icon is not a delivery mechanism on this desktop.** Anything that
  needs to be seen has to be a real bar widget, which is what F4 is for. Design
  should treat the tray as a fallback, never as the surface.

One spec detail worth recording for portability: `rquickshare` publishes its
`IconName` as an absolute path (`/run/user/1000/tray-icon/...png`) rather than a
themed icon name. Quickshell copes. A bar that reads the specification strictly
may not, so on another desktop the icon may be missing even though the item
registers.

## F2 — KDE Connect: clipboard, notifications and files

In: nothing. **Corrected 2026-08-17: this said "F1 working", and it was wrong.**
F1 is blocked on a BlueZ bug and F2 was measured anyway — the two share no code
path. The dependency was assumed because both involve the phone, and it cost a
day of treating F2 as unreachable.
Out: copy on the phone, paste on the PC — and, since F1 is blocked upstream,
**the file path that does work today**. This is not a substitute for Quick
Share: it is a second route, with its own tool and its own rows, and saying
which one a user is actually using is the whole point.

- [x] Install `kdeconnect` and the Android app — `kdeconnect 26.04.3-1`
- [x] Pair — `Pixel 7 Pro`, paired and reachable, 2026-08-17
- [ ] Validate: clipboard both ways, notifications, SMS — **two halves measured,
      both `partial`.** Notifications arrive over D-Bus with their source app;
      nobody has verified they are *painted*. Clipboard measured one way.
- [ ] Verify the clipboard under Wayland (`wl-clipboard`)
- [ ] Decide how the daemon starts in the Hyprland session
- [ ] Check whether the tray icon coexists with the bar
- [ ] Files over KDE Connect — **measured 2026-08-19, both directions, hash
      verified on the phone's own storage, not on the sender.** Needs its own
      rows: `file-send` and `file-receive` belong to F1 and their tool is
      `rquickshare`, whose note says both devices must share a LAN subnet.
      Marking them from a KDE Connect measurement would claim Quick Share works
      on the strength of something that is not Quick Share.

> **Everything measured so far went over Tailscale, not the LAN**, with 97-737 ms
> RTT and a relay in the path. That is not the route the product will use, so no
> row here says anything about LAN behaviour yet.
>
> **The link drops on its own and does not recover on its own** — twice in a few
> hours, with the phone paired and answering ping. `forceOnNetworkChange` over
> D-Bus restores it in under 12 s, which is why the contract carries an
> `unreachable` status with a `retry-link` action instead of a grey gap.
>
> **Sending a file can be measured; confirming it arrived cannot yet.**
> `kdeconnect-cli --mount` returns a path and mounts nothing: `sshfs` is not
> installed, and the journal says so while the command does not. Installing it
> is a decision for the maintainer.

Also testable in full on the Pixel 7 Pro. The phone's battery reads correctly
over the same channel, but it stays out of the matrix on purpose: the catalogue
places `phone-battery` in F4, and a capability enters when its phase does.

## F3 — Pixel Buds

In: the buds paired.
Out: battery and ANC from the desktop.

- [ ] Install `pbpctrl` from the AUR (still 482 days without an update, but it
      **does** build: measured 2026-08-16 in a clean Omarchy 4.0.0 VM, installed
      from the AUR untouched. It was not run, so this says nothing about whether
      it talks to Buds Pro 2, which use a different SoC)
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

Anything drawn here answers to the [design rules](06-design.md): tokens from the
active Omarchy theme, Pixel identity confined to the identity budget, and a
defined appearance for every capability the matrix does not yet call `works`.

## F5 — Research (no promise anything comes of it)

- [ ] Fast Pair: is there a public specification for the *provider* side? Is it worth anything without Google Play Services?
- [ ] Cross-device services: is the traffic observable? Is it tied to device attestation?
- [ ] Decide honestly whether this is viable, or close the door and document why

## The project's principle

Before writing your own code, check it does not already exist. And before
calling a feature done, measure it against real hardware — not against somebody
else's README.
