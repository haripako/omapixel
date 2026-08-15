# The plan

The [roadmap](03-roadmap.md) sequences **measurements** on the reference
machine. This document is the other axis: what gets **built**, in what order,
and why that order and not another.

The unit here is a block, not a feature. A block is a body of work that ends in
something falsifiable, and that unblocks specific later work. Blocks are ordered
by dependency, not by appeal.

Written 15 August 2026, after the F0 measurements. Anything called measured
below happened on this machine; everything else is judgement and says so.

---

## What we are actually chasing

Not a feature list. Six sentences a user should be able to say truthfully. Every
block below exists to make one of them true, and anything that makes none of
them true does not belong in the plan.

| | The user should be able to say | Depends on |
|---|---|---|
| **U1** | "I sent that file to my phone without touching a cable or a browser" | B0, B1, B3 |
| **U2** | "I copied it on the phone and pasted it here" | B0, B1 |
| **U3** | "My phone's notifications arrive here, and I can act on them" | B0, B1, B3 |
| **U4** | "I can see the earbuds' battery without opening anything" | B1, B2, B3 |
| **U5** | "One key changes noise cancelling" | B2, B3 |
| **U6** | "It worked after I logged in, and when it did not, it told me why" | B0, B4 |

**U6 is the one that separates a demo from a product**, and it is the one every
project like this skips. Everything found during bring-up failed *silently*.

---

## B0 — Make the machine able to talk at all

**Status: blocking everything. Nothing in B1 can be measured until this is done.**

This block did not exist in the original plan. It exists because F0 measurement
found two hard stops, both silent.

**The firewall drops it all.** Measured: `ufw` is active with
`DEFAULT_INPUT_POLICY="DROP"`, and the existing rules cover LocalSend, ssh,
Jellyfin and eMule. There is nothing for mDNS, nothing for KDE Connect's
1714-1764, nothing for Quick Share. Discovery cannot arrive and neither can an
inbound transfer.

**One wrinkle that shapes the fix.** Measured: rquickshare's TCP listener takes a
**different port on every launch** — 35475, then 34261 after a restart. A static
allow rule for the transfer port is therefore impossible. Options, in order of
preference: find a way to pin the port; scope a range to the LAN subnet only;
open and close a rule around the process lifetime. Not yet decided, because it
should be decided against a measurement, not a preference.

**bluetoothd is crashing.** Measured: two `SIGSEGV` of `bluetoothd`, at 23:00:34
and 23:08:50, both coinciding with an rquickshare start. Each is followed about
15 seconds later by the MX Master re-enumerating — which is the input stall the
maintainer feels. **This also explains the machine's long-standing "Bluetooth
drops with nothing in the log" history: the segfault is recorded by the kernel,
not by the `bluetooth` unit,** so anybody looking at `journalctl -u bluetooth`
would have seen nothing, forever.

Not yet established: the exact trigger. Both crashes coincide with a start, and a
kill without a restart did not produce one, which points at the BLE listener
coming up rather than going down. Reproducing it is a 30-second test and it has
not been run yet.

**Done when:**
- A file moves phone → PC and PC → phone.
- rquickshare runs for an hour with the mouse connected and no `bluetoothd`
  segfault in `journalctl -k`.
- Every rule and workaround needed is written down as a *check*, not as a fix
  applied by hand.

**Why it is not throwaway work:** every diagnosis in this block becomes a check
in B4's `doctor`. This block is where the product's error messages are
discovered. A user hitting the same firewall will hit the same silence.

## B1 — The three transports, measured

The tool-level work. Produces the data that the matrix is made of.

- **Quick Share** — send, receive, and characterise discovery: attempts until
  the device appears, and whether the phone's screen being on changes it. There
  is a specific hypothesis to test, from F0: latency to the phone is bimodal
  (median 338 ms, minimum 4.8 ms, zero loss), which is the shape of a WiFi
  client parking its radio. **Consistent with the documented discovery
  flakiness, not shown to cause it.**
- **KDE Connect** — clipboard both ways against `wl-clipboard`, notifications
  against the Omarchy daemon, SMS.
- **Earbuds** — battery and ANC. **Blocked on hardware.** And the riskiest thing
  in the project: `pbpctrl` targets first-generation Buds Pro, the Pro 2 use a
  different SoC, and the package has gone 482 days without an update.

**Done when:** matrix rows move from `untested` to `works`, `partial` or
`broken`, each with an exact tool version and a date. Not before.

## B2 — One stable interface per capability

**The hinge of the whole plan, and the least obvious block.**

Every capability gets wrapped behind our own command with stable, machine
readable output. Nothing upstream is ever consumed directly by anything we draw.

```
omapixel status --json   ->  { buds: {...}, phone: {...}, transfer: {...} }
```

Three separate problems collapse into this one block:

1. **Upstream is going to die.** `pbpctrl` probably first. When it does, or when
   it turns out not to speak to Buds Pro 2, swapping in `budslink` or a fork
   must cost one file and not a rewrite of the interface.
2. **Design is blocked without it.** Design cannot build against `pbpctrl`
   output that may never exist. It can build against a contract. **So the
   contract gets defined at the start of this block, not at the end** — that is
   what lets design and development run in parallel instead of in sequence.
3. **Degradation has to be designed, not discovered.** Standard AVRCP gives one
   combined battery figure; three figures need the proprietary protocol. The
   interface must be able to say "one figure, combined" as a first-class answer,
   so the UI has something honest to draw rather than a blank.

**Done when:** the command returns valid JSON on a machine where *none* of the
underlying tools work, correctly reporting that nothing is available. That case
is the one that matters, and it is the one nobody tests.

## B3 — The experience

F4 in the roadmap. The original work: nobody has integrated any of this into
Omarchy.

- Bar widget: earbuds battery, phone presence, transfer progress.
- Keybindings: cycle ANC, send the current selection to the phone.
- Omarchy menu entry.
- Notification behaviour that coexists with the Omarchy daemon.

Two constraints already measured, both of which change the design:

- **A tray icon is not a delivery mechanism here.** rquickshare's SNI item
  registers correctly and Quickshell picks it up, but Omarchy's tray splits
  items into pinned and a collapsed drawer that starts shut. An unpinned app is
  live and invisible. Anything that must be seen has to be a real bar widget.
- **QML has no hot-reload.** Every visual change costs a shell restart, so
  iteration is expensive and the widget should be built against fake data from
  the B2 contract before real data exists.

Design owns how it looks, per [design rules](06-design.md). Development owns the
plumbing. Both meet at the B2 contract.

## B4 — It works on a machine that is not this one

Per [packaging](05-packaging.md). The product half.

- **`doctor`** — the highest-value single thing in the plan, because every
  failure found so far was silent. It turns `hw-report.sh` from a reporter into
  a diagnostician: subnet, reachability, firewall ports, daemon alive, autostart
  wired, USB mode, adb authorisation, adapter present. Each check names its fix.
- **Dependencies as data** — a per-distro table, so adding Fedora is a data
  change. The install path is currently Arch-only and that is the single biggest
  portability problem.
- **No assumptions about the desktop** — no systemd user unit where none exists,
  no reliance on XDG autostart being processed.

**Done when:** somebody on a different distro with a different bar installs it,
runs `doctor`, and either gets a clean result or gets told exactly what to fix.

## B5 — Research, with no promise

Fast Pair, Cross-device services, and the rest of the T3/T4 rows in
[features](features.md). Runs in parallel and blocks nothing. Its output is a
decision — viable or closed — and a written reason either way, so the next
person does not rediscover the same wall.

---

## Order, and what runs in parallel

```
B0  firewall + bluetoothd        <- blocks everything, start here
 |
B1  transports measured           <- feeds the matrix
 |                                    (earbuds half waits on hardware)
B2  stable interface              <- contract defined EARLY, at B1's start
 |        \
B3  experience   \                <- design works against the contract,
 |                \                  in parallel with B1
B4  portability   <- draws its checks from B0 and its data from B2

B5  research      <- parallel throughout, blocks nothing
```

The two things worth noticing:

**Define the B2 contract during B1, not after it.** It is the only way design and
development are not serialised, and it costs nothing to write a JSON shape
before the data behind it exists.

**B0 is not overhead.** It is where the product's diagnostics get discovered.
Doing it carelessly by hand means B4 has to rediscover all of it later.

## What this plan deliberately does not do

- **No packaging before something is shown to work.** An elegant installer for a
  broken thing is the classic failure of projects like this.
- **No capability enters `data/capabilities.toml` because it entered
  `features.md`.** It enters when it enters a block. Otherwise the matrix fills
  with aspirations marked `untested` and stops meaning anything.
- **No design against unmeasured data.** If a figure has not been measured, the
  design assumes it may never exist and degrades.

## Honest current state

B0 is unstarted and blocking. Of B1, only the install and the tray question are
closed. Nothing has been transferred in either direction. No capability in the
matrix has moved off `untested`, and that is the accurate picture.
