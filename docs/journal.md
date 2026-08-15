# Journal

What was established, on what day, and by what kind of evidence. Newest first.

The rest of the documentation says what is currently true. This file says **when
it became true and how it was found out**, which is the thing that decays first
and the thing nobody writes down.

It exists because of a specific failure mode. A claim written into a dated,
attributed record starts to *look* verified after a few months, whether or not
anybody ever ran it. So every entry carries a kind, and the kinds are the ones
from [conventions](conventions.md):

| Kind | Means |
|---|---|
| **measured** | Run on the reference machine, on that date. Names the tool version where it matters |
| **derived** | From a README, an AUR page, a specification, a news article or a web search on that date. **Not evidence** |
| **decision** | A choice made, with its reason. Reversible, and the reason is what makes it reviewable |
| **open** | A question named and deliberately left unanswered, with what would settle it |

An entry never changes kind by being repeated. If a `derived` line later gets
run on hardware, that is a **new entry** on a new date, not an edit to the old
one — otherwise the record loses the very thing it exists to preserve.

Two qualifications on `measured`, both of which have already caught something
here:

- **Measured means measured on the reference machine**, on that date, not
  measured in general. Somebody else's adapter, distro or phone is a different
  measurement.
- **A passing test is not a measurement about a device.** The test suite runs
  against stubs, with the `PATH` replaced wholesale. That `omapixel-status`
  emits valid JSON with nothing installed is a fact about the code — not about a
  Pixel and not about a pair of earbuds. Entries below say which they are.
- **Measured against the emulator is its own kind, and it is written out in
  full.** A virtual Quick Share peer is not a Pixel. Anything exercised against
  it is recorded as *measured against the emulator*, never as *measured*. This
  is the qualification most likely to erode, because it will be the easiest and
  most available thing to run — so it is stated here rather than left to
  memory.

Entries are not deleted when they turn out to be wrong. A correction is a new
entry that says what was wrong and what replaced it.

---

## 2026-08-15

The whole project so far. Founded, opened up, and taken through F0 and half of
F1 in one day, which is why the dates below are all the same and why the order
within the day matters more than usual.

### The Bluetooth adapter, and the oldest mystery on this machine

**measured** — `bluetoothd` segfaults when `rquickshare` starts. Reproduced
three times out of three (23:00:34, 23:08:50, and a controlled test at
23:15:49). Killing `rquickshare` without restarting it produces no crash, so the
trigger is the startup path, where the BLE listener comes up.

**measured** — This is the explanation for the machine's long-standing history
of Bluetooth devices "dropping with nothing in the log". The crash is recorded
by the kernel, not by the `bluetooth` unit, so anybody looking in
`journalctl -u bluetooth` was guaranteed to find nothing, indefinitely. It is in
`journalctl -k`.

**measured** — The crash has two outcomes, not one. Usually systemd restarts
`bluetoothd` and the mouse re-enumerates about fifteen seconds later. Once it
did not come back at all: BlueZ reported `Connected: yes` with the HID UUID
present, while `/proc/bus/input/devices` had no mouse and the kernel logged no
re-enumeration. A phantom connection — ACL up, HID profile never re-bound.

**measured** — Recovery order matters, and retrying faster makes it worse.
Immediate reconnect gives `le-connection-abort-by-local`; power-cycling the
adapter gives `br-connection-canceled`; further attempts stack up as
`InProgress` and block each other. Disconnect, wait, one connect, succeeds.

**measured, and it sharpens the entry above** — On the phantom-connection
occasion, `connect` returned `le-connection-abort-by-local` **and the HID
attached anyway**. So that error code is not a reliable signal of failure, and
the recovery sequence above should not be read as "these error codes mean it
did not work". Check the result, not the return.

**measured, and this is the one that becomes a `doctor` check** — BlueZ
reported the mouse `Connected: yes` while `/proc/bus/input/devices` contained
zero MX Master entries. **BlueZ's own state is not proof that the device works.
The kernel input node is.** The check is two commands against each other:

```bash
bluetoothctl info <mac> | grep Connected
grep -c 'MX Master' /proc/bus/input/devices
```

**derived, not reproduced** — The crash signature has the instruction pointer
equal to the faulting address, which is the shape of a call through a corrupted
or freed function pointer. Confirming it needs a backtrace.

**correction of a claim that was circulated as fact** — It was said that the
core dumps were not being saved and that dump storage had to be enabled before
the next crash. **False.** All three exist in `/var/lib/systemd/coredump/`,
`root:root 0640`. `Storage` is at its default of `external` and is working.
`coredumpctl` marks them `inaccessible` because it cannot open them as uid 1000,
not because they are absent. What is needed to symbolise a backtrace is a
password, not another crash.

The failure mode is worth more than the fact: **a tool said "inaccessible" and a
reader heard "does not exist".** It is the same shape as the shell logging
`reloading` while reloading nothing, and it is the third time in one day that a
tool's own words have been the misleading part.

**open** — Is the bug specific to `rquickshare`, or does it live in BlueZ's
advertising path? If plain BLE advertising crashes `bluetoothd` too, this is a
BlueZ 5.87 bug to report upstream. **Settled by one isolation test.**

**open** — Does it threaten the earbuds work? `pbpctrl` talks to the buds over
BLE on the same adapter and the same BlueZ. If the crash is in the BLE path
rather than in anything Quick Share does, it sits underneath the entire
Bluetooth half of this project and outranks everything else. **This is the
highest-value open question in the repository.**

### The desktop layer

**measured** — Plugin QML does not hot-reload on this build (omarchy
`4.0.0-1`), contrary to Omarchy's own documentation. Method: a throwaway bar
widget rendering a literal, edited with the shell left running; evidence is
`grim` captures plus the journal, not impressions. `shell.json` *does* reload
live — the widget appears and disappears without a restart. QML code only
changes after `omarchy restart shell`, with a new PID confirmed. Falsification
test passed: after the restart it did render the new value.

**measured** — The shell logs `Local plugin changed, reloading` while reloading
nothing. **That log line is not evidence of anything.** Verify against pixels.

**measured** — A tray icon is not a delivery mechanism on this desktop.
`rquickshare` registers a StatusNotifierItem correctly and Quickshell picks it
up — the watcher goes from one item to two and the new one resolves to the
process, `Status: Active`, with a menu object exposed. So "does the SNI tray
work under Wayland", which no upstream documentation covered, is **yes**. It is
still invisible, because Omarchy's tray splits items into pinned and a collapsed
drawer that starts shut. Registered, live, and hidden. Nothing is broken, so
there is nothing to report upstream.

**measured** — `rquickshare` publishes its `IconName` as an absolute path rather
than a themed icon name. Quickshell copes; a bar that reads the specification
strictly may not.

**measured** — Inventory of the Omarchy 4.0.0-1 token system: the five `Color`
roles, the multiplicative type scale from 12 px, the spacing tokens, the state
alphas (0.04 / 0.08 / 0.18 / 0.22), `cornerRadius` 8, `gapsOut` 5, and the 33
`qs.Ui` pieces. Three consequences: no stock theme ships a `shell.toml`, so the
default scale is what everybody actually sees; there is not one
`SpringAnimation` in the whole shell (38 `NumberAnimation`, `OutCubic`
dominant, 140 ms the most repeated value); and the active theme resolves `blue`
to `#b59790`, a pink — which is where the rule against encoding state in colour
alone comes from.

**derived** (web, this date) — Material 3 Expressive state-layer alphas, shape
scale, spatial and effect springs, and the type scale by role. Roboto Flex and
Google Sans Flex are OFL; `ttf-material-symbols-variable` is in Arch `extra`
and is not installed here.

### The network, and what "same subnet" is worth

**measured** — The phone shares 192.168.10.0/24 with the wired host and is
genuinely reachable: 30 of 30 ICMP replies, TTL 64, `ip route get` resolving
straight out of `eno1` with no gateway hop. Same layer 2 segment, not merely the
same subnet. This mattered more than it looks: an access point isolating clients
produces the same subnet and a dead transfer.

**measured** — Latency to the phone is bimodal. Zero loss over 30 packets, but a
minimum of 4.8 ms against a median of 338 ms, a p90 of 694 ms and a maximum of
1141 ms, with 18 of 30 above 100 ms. Zero loss with that spread is the shape of
a WiFi client parking its radio between beacons.

**open** — Whether that is what causes the documented Quick Share discovery
flakiness. The two are **consistent, and that is all**. Settled by repeating the
measurement with the phone's screen on, which is an F1 task.

**measured** — A sweep of the /24 found 24 live hosts, seven with
locally-administered MAC addresses: phones with MAC randomisation on. The Pixel
could not be identified by vendor OUI, because a randomised MAC has no vendor.
Any "find your phone on the network" idea cannot lean on OUI lookup. This is a
busy home network, not a quiet lab.

**measured** — `rquickshare`'s TCP listener takes a different port on every
launch (35475, then 34261 after a restart), so a static firewall rule for the
transfer port is impossible.

**measured** — `ufw` is active with `DEFAULT_INPUT_POLICY="DROP"` and has no
rules for mDNS, for KDE Connect's 1714-1764, or for Quick Share. Neither
discovery nor an inbound transfer can arrive.

### Failures that look like nothing happening

All hit in one evening, and all silent. They are the reason a `doctor` command
is the highest-value thing in the plan.

**measured** — `kdeconnectd` ships no systemd unit. It relies on
`/etc/xdg/autostart` plus D-Bus activation, and was not running after install
because the session predated the package. It started only when something spoke
to it over D-Bus.

**measured** — Autostart works here because `xdg-desktop-autostart.target` is
active in this session. That is a property of this setup, not of Linux.

**measured** — The phone appeared first as `18d1:4ee7` (charging and adb, no
MTP), later as `18d1:4ee2` (MTP and adb), because the USB mode was changed on
the phone mid-session. Tools expecting MTP see nothing in the first state.

**measured** — `adb devices` reported `unauthorized`. It needs the phone
unlocked and a dialog accepted; nothing on the desktop side fixes it.

**measured** — A latency percentile calculation produced nonsense (`min 146.0,
p90 6.8, max 9.0`) because `sort -n` was interpreting decimals under a
comma-decimal locale, and `ping`'s output field is localised (`tiempo=` here,
`time=` on an English system). It was caught only because the numbers were
absurd on sight. **A subtler version of this bug would have shipped into the
published matrix**, which is the worst outcome this project has.

### Tools and hardware

**measured** — `r-quick-share 0.11.5-5` installed from the AUR, built from
source. It is a Tauri application: a Rust release build plus a pnpm frontend
build, still compiling after 582 crates. `r-quick-share-bin` is the same
version, prebuilt.

**derived** — `pbpctrl` had gone 482 days without an AUR update as of this date.
It targets first-generation Pixel Buds Pro; the Pro 2 use a different SoC, so
the proprietary protocol may not match. **The largest single unknown in the
project**, and only hardware can settle it. Fallback is `budslink-git`, which
does not list Pixel Buds as supported.

**measured** — No Google device is paired on this machine. What is paired is an
MX Master 3S, an RK-S98RGB keyboard, an Xbox headset and an Xbox controller.

**not measurable today, and worth stating as such** — Earbud battery over
AVRCP. Nothing Google is paired and the Buds Pro 2 have not arrived. **If a
battery figure appears anywhere dated today, it was invented.**

**open, closed the same day — kept because the closing is the point** — The
Bluetooth version the MT7922 in this machine actually reports. "It is 5.2" was a
datasheet claim, not a reading off the adapter.

**measured** — `btmgmt info`, read-only, no privileges. `iso-broadcaster`,
`sync-receiver`, `cis-central` and `cis-peripheral` are all listed as supported
**and currently active**. Those are the isochronous-channel prerequisites for LE
Audio and Auracast, so **the controller is not the obstacle**. It also reports
`version 12` and `manufacturer 70`.

Three things this measurement deliberately does **not** say:

- `version 12` has **not** been translated into a Bluetooth version number here.
  That translation comes from the SIG's Assigned Numbers table and nobody has
  consulted it on this machine. The evidence is the flags, not the number. If a
  version number ever appears in this file, it is derived from a table that was
  not read here, and it has to be labelled that way.
- What was measured is **the controller, and nothing else**. Whether BlueZ and
  PipeWire complete a real Auracast broadcast, and whether the earbuds pair over
  LE Audio at all, are both unmeasured. The jump from "the hardware can" to
  "this works" has not been made.
- Its proper home is [reference setup](04-reference-setup.md), which is where it
  should end up.

**derived, refuted by measurement** — The earlier claim that the MT7922 "is
Bluetooth 5.2" came off a datasheet. The adapter reports `version 12`, which is
not 11. The derived figure does not match what the device reports. Recorded
because it is a clean specimen of the failure mode this whole project is
arranged against: **a specification number smuggled in as a fact about this
machine.**

**derived** (web, this date) — Auracast over LE Audio is viable on Linux in
principle: BlueZ 5.85 has full BAP support and PipeWire 2.0 added broadcasting,
with browsing and switching controls still work in progress. Needs a Bluetooth
5.2+ adapter at both ends. Also noted: the BlueZ backend's **HFP HF** role as a
path to real call audio through the PC, and Android 14+'s native **UVC** webcam
mode, which is not enabled on every device because it depends on kernel config,
the USB HAL and a preloaded app.

**derived, correction** — Fast Pair role naming was backwards in earlier notes.
In Google's specification the **Provider** is the accessory advertising that it
is ready to pair (the earbuds, GAP Peripheral) and the **Seeker** is the phone
looking for it (GAP Central). The consequence is real: the buds already are the
Provider, so there is nothing to port there. What Linux lacks is a **Seeker**,
and the account-linked half of that role leans on Play Services — which is why
this stays in F5 rather than F3.

### The test suite

**measured, on this machine, against stubs** — First suite green: 126 tests, 8
expected failures, 0.9 s. Reproduce with `./scripts/run-tests.sh` from the root.
Standard library only, no network, no pytest. Python 3.14.7 here; CI runs 3.12,
so the two are not the same measurement.

**measured** — A real hole in CI's privacy grep: `subnet = "[ip redacted]/24"`
passed it, because the check only looked for the `/NN` suffix and never checked
that the host part was zero. That is precisely the address the rule exists to
keep out of public reports.

**measured, and it corrects the entry above** — The replacement detector was
then attacked rather than trusted, and **it failed open in seven further ways**:
MAC addresses with dashes — the IEEE's canonical form and the one Windows shows,
so the leak that would actually have happened — IPv6 both global and link-local,
an entire class of addresses that went unchecked, `/32` and `/31` accepted for
ending in `.0`, and a host ending in `.0` inside a wider network. Now the
`ipaddress` module decides, not the shape of the string. Reproduce with:

```bash
LC_ALL=C python3 -m unittest tests.test_repo_invariants.PrivacyOfPublishedReports
```

Worth stating plainly, because the first version of this entry read as solved
when it was not: **a fix that has not been attacked is a hypothesis.**

**decision** — What the detector deliberately does **not** catch is written in
its docstring and **pinned by a test**: bare and Cisco-style MACs stay out,
because twelve hex digits match half the logs in the world, and a false positive
is a red build that a stranger cannot work out how to fix. If somebody adds that
detection, the test fails and forces the docstring to be corrected in the same
commit. The general criterion, which applies well beyond this check: **a privacy
invariant people trust more than it deserves is worse than a grep nobody
trusts.**

**decision** — The privacy rule for device reports is never softened to a
warning, and never "fixed" by normalising `[ip redacted]/24` into
`192.168.10.0/24`. **The address has already travelled in the contributor's pull
request**; masking it hides the leak without undoing it. It is rejected loudly
and the sender is told. Written into the docstring and the test so it survives
the reader who finds it pedantic.

**measured, against fixtures** — The link checker had a defect of its own: it
re-read the file from disk instead of using the text it had been handed, so it
only worked by coincidence against real files. It surfaced while writing
positive controls. **A validator that is only ever tried against real input is
right by accident**, which is the same family as the four cases above.

**measured, against stubs** — Suite now at **147 tests**, including 24 covering
`scripts/omapixel-status`. Supersedes the 126 recorded earlier the same day;
both figures are true of their moment. Later the same evening, **150 green**,
with 18 adversarial entries against the privacy detector.

**reviewed, nothing found** — `SECURITY.md` and `.github/workflows/validate.yml`
read in full on this date, from a security angle: actions pinned to SHAs with the
reason written beside them, `contents: read`, no credentials persisted, and the
MAC/IP invariant moved out of the workflow into the test suite with positive
controls. **No finding.**

This is recorded deliberately, and the distinction matters: it is a record that
these files were reviewed on this date, **not a clean bill of health**. A review
with no findings ages — six months from now the useful fact is when somebody
last looked, not that they found nothing. Silence in a journal is
indistinguishable from nobody having checked, which is the same failure this
project keeps meeting elsewhere.

**decision** — Two `omapixel-status` defects found by review — the Pixel phone
counted as earbuds, and a dead `bluetoothd` reported as "nothing is paired" —
were fixed the same day and kept as **regression tests rather than expected
failures**, because the obvious "improvement" in six months is to widen that
match again.

**measured, and it is the rule biting** — The observable-effect rule was applied
to `probe_file_transfer`: a live process is not a serving process, so it now
requires a listening socket. That **broke the test suite**, which had encoded
the old contract, and the break was repaired in minutes. The breakage is the
evidence that the rule has teeth: a rule that changes no existing behaviour was
not worth writing down.

**decision** — The negative cases for the `[network]` schema were written in the
suite **before** the validation exists in `build-matrix.py`, marked
`expectedFailure`. When the validation lands, the run fails on unexpected
success, and that is the signal to remove the decorators.

**decision** — The invariant "every promoted id appears in the feature
catalogue" was withdrawn. The mapping is injective, not surjective: `hotkeys`
and `menu-entry` are Omarchy-layer capabilities with no Apple analogue. A
comment records it so nobody reinvents the rule.

**open** — `shellcheck` **cannot be verified on this machine**; it is not
installed, and `run-tests.sh` degrades it to a warning. That CI step only ever
runs for real on GitHub. Recorded as *not verified here*, which is a valid and
useful state.

**open** — Proposed: add the suite to `.github/workflows/validate.yml` and drop
the MAC/IP grep from the YAML now that the invariant lives in the suite with
positive controls.

### Decisions

**decision** — A capability enters `data/capabilities.toml` when it enters a
phase, not when it enters the feature catalogue. Reason: adding a row creates an
`untested` cell for every device, which is useful for something somebody is
about to try and noise for something aspirational. A matrix full of aspirations
stops meaning anything.

**decision** — Design builds against the capability matrix, not against the
feature catalogue, and every surface degrades. The concrete case: a battery
widget with three figures (left, right, case) is exactly what the catalogue
asks for, but standard AVRCP gives **one combined figure**, and the three depend
on a tool that may not speak to these earbuds at all. The interface must be able
to say "one figure, combined" as a first-class answer.

**decision** — Corrections to derived documents are made in place with a dated
correction note, not by deleting the original. Reason: a derived document is
dated evidence, and silently rewriting it makes the claim impossible to age.

**decision** — Never draw the state a subsystem reports about itself. Draw the
observable effect. A widget that says "connected" because BlueZ says
`Connected: yes` is a plausible zero wearing a different hat, and the design
rules already forbade those in another context. The operational form of the
question: what would the user look at to know it worked — an input node, a file,
a pixel — and show that instead.

The rule came out of four separate cases in a single day where a tool's own
words were the misleading part, and it is recorded with that evidence attached
rather than as a moral. **All four would have produced a widget that was
confident and wrong.**

**decision** — Build a **virtual Pixel**: a simulated Quick Share peer, local,
that exercises the transfer path without the physical phone, and that reports
errors, successes and state explicitly rather than failing in silence.

It takes priority because F1 is blocked twice over — by hardware that has not
arrived, and by a measured risk, since launching `rquickshare` crashes
`bluetoothd` three times out of three and leaves the machine without a pointer.
The status contract already has the hole it fits: `peers` is never `[]` but
`unavailable` with a reason, *until discovery exists*. This is what makes it
exist.

**correction, same day, and it refutes a premise this very entry carried** — It
was written here, and repeated elsewhere, that a virtual peer unblocks *both*
those things. It does not. **The emulator does not remove the segfault**,
because `bluetoothd` dies during `rquickshare`'s own startup, before any peer
exists to be discovered. Whether the peer on the other end is real, virtual or
absent changes nothing about it. The emulator removes the *hardware* blocker
and leaves the crash exactly where it was — which means the isolation test is
still the thing that matters most, and no amount of emulator work substitutes
for it.

Three rules come with it, and they are not negotiable per session:

1. **No Bluetooth.** The emulator does not bring up BLE, does not talk to
   `bluetoothd`, does not touch the adapter. LAN only — mDNS and TCP. If it
   turns out Quick Share discovery is impossible without the BLE advertisement,
   **that is a finding to report, not a licence to switch it on.**
2. **A virtual Pixel is not a Pixel.** It promotes no capability and closes no
   F1 box. It closes test-infrastructure boxes. A tick against "test receiving
   PC ← phone" requires the phone, and this is not the phone.
3. **The emulator has one owner**, in its own directory, under the same rules as
   the rest of the tooling.

Rule 2 is the one that will erode, because the emulator will be the easiest
thing in the project to run and the only one always available. **Everything
exercised against it is written "measured against the emulator", in full.**

**decision, reached independently by two people** — Rule 2 has to be structural,
not editorial: **the simulated mark lives in the data, not in the styling.** If
the JSON does not say a peer is simulated, no consumer *can* tell — the widget,
the test, the person reading a log, none of them. The argument that settles it
is the screenshot: **a picture of a transfer working, pasted into an issue,
becomes evidence of something nobody measured, and it travels further than any
document we write.** Requested of the status contract, and written into the
design rules as *Simulated data must look simulated*.

**open, and the gate has a blind half** — The "no Bluetooth" gate is supposed to
be a measurement that starting the emulator brings up nothing Bluetooth. But the
test harness records **binary invocations**, and that misses an in-process
socket entirely: `AF_BLUETOOTH`, or D-Bus to BlueZ, without executing anything.
The gate has to cover both halves or it certifies only the half it can see.

**open** — Does Quick Share discovery work over pure LAN, with no BLE
advertisement at all? The whole emulator rests on the answer being yes, and that
is currently a hypothesis, held by somebody who said plainly it should not be
believed on their say-so.

**correction, same day** — It was said that the virtual peer lifts the ceiling
on what a clean VM can validate. It lifts it **halfway**: the LAN path,
feedback, and whether an error can be understood — not real discovery, and
nothing that depends on BLE or on a Pixel sharing the subnet.

**decision** — The interface between the layer that measures the device and the
layer that draws it is agreed **in writing, before it is written**, and whoever
changes it says so beforehand rather than afterwards. **A widget that invents a
number is worse than an empty widget.** Same principle as the rule above: the
drawing layer never fabricates, and never simulates hardware it cannot reach.
That interface already exists — the [status contract](08-status-contract.md)
and `scripts/omapixel-status`, commit `652d128` — so nothing new had to be
agreed, only kept.

**decision, proposed** — The same criterion applies to `doctor`, and more
sharply. [Packaging](05-packaging.md) already says `doctor` is the
highest-value item on its list because every bring-up failure was silent; this
gives it the criterion it was missing. **A check that asks a subsystem how it is
feeling is not a check, it is a survey.**

**decision** — Under the `design-assumptions` anchor in the design rules, every
surface names the capability id it assumes and whether it is an `enhancement` or
`required`. `required` is only legal once the matrix shows that capability
measured. Today every row is `enhancement`, because today nothing is measured.

**decision, technical note that has had to be given twice** —
`data/capabilities.toml` has no `status` field. It defines rows only; statuses
come from `data/devices/`, where there is a single report that deliberately
claims nothing. All 17 capabilities are `untested`, so any check demanding
`measured` starts out entirely red, by design.

**decision** — The repository's first commits carried a work email. Removing it
needed a history rewrite, and the orphaned objects stayed reachable by direct
SHA afterwards, so the repository was deleted and recreated. Deleting it needed
a token scope that could not be scripted.

**decision** — No packaging before something has been shown to work. An elegant
installer for a broken thing is the classic failure of projects like this.

### Honest state at the end of the day

Nothing has been transferred in either direction. No capability has moved off
`untested`. F0 is closed for the phone; its one remaining box is pairing the
earbuds, which needs hardware that has not arrived. Of F1, only the install and
the tray question are closed. The firewall and the `bluetoothd` crash block
everything downstream of them, and neither is fixed.

That is the accurate picture, and it is written here so that a later reader does
not mistake the volume of documentation for progress.
