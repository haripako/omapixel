# Landscape: what already exists

**Derived from web research and AUR queries on 15 August 2026.** None of it has
been verified by running it. Verifying it is the point of phases F1 to F3, and
until then every line here is a lead, not a fact. See [conventions](conventions.md).

Package versions and "last updated" figures were true on the date above and rot
quickly. Check before relying on them.

## File transfer — Quick Share

**rquickshare** ([Martichou/rquickshare](https://github.com/Martichou/rquickshare),
AGPL-3.0, Rust) is the reimplementation of the Nearby Share / Quick Share
protocol for Linux and macOS. It is the centrepiece of this project and the most
mature piece in the stack.

- How it works: it emits a **Bluetooth advertisement** so that Android starts
  publishing its mDNS, and the transfer itself runs over **WiFi on the LAN**.
  The hard consequence: both devices must be on the same network.
- Bidirectional — send to the phone and receive from it.
- Known limitation: the Android device's visibility is intermittent, because
  Android does not advertise its mDNS continuously.
- The README describes itself as a work in progress.
- Packaged in the AUR in three variants, as queried on 2026-08-15:
  `r-quick-share` 0.11.5-5 (updated 4 days earlier, +15 votes),
  `r-quick-share-bin` 0.11.5-2, and `r-quick-share-git`.
- There is a fork, [oop7/rquickshare-x](https://github.com/oop7/rquickshare-x),
  which adds Windows support.
- Nothing is documented about Wayland. **First thing to verify**: the tray
  indicator and the dialogs under Hyprland.

### What the protocol actually requires

**Derived from the reverse-engineering write-ups on 15 August 2026**, gathered to
answer one question: can a peer be spoken to over the LAN alone, with no
Bluetooth? Sources at the foot of this file.

**Yes. BLE is a doorbell, not a transport.** It carries no payload, takes no part
in the handshake and authenticates nothing. Its only job is to nudge a dormant
Android device into publishing its mDNS record — pyquickshare states it plainly:
BLE is used only to trigger advertisement, what it calls *nudging* or *Fast
Init*. NearDrop on macOS has no BLE at all, because its author could find no
macOS API for it, and it receives files fine. rquickshare's own README says
**Wi-Fi LAN only** and documents workarounds for machines with no Bluetooth at
all: open the Quick Share sheet by hand on the phone, from the Files app or an
intent shortcut.

The consequence for anything that emulates a peer: two software endpoints on a
LAN can both publish mDNS continuously, so there is nothing to nudge and nothing
for BLE to do.

The shape of it, for whoever implements against it:

| Layer | What it is |
|---|---|
| Service type | `_FC9F5ED42C8A._tcp.` — from `SHA256("NearbySharing")` |
| Instance name | 10 bytes, URL-safe base64: `0x23` (PCP), 4-byte endpoint id, `0xFC 0x9F 0x5E`, two zero bytes |
| TXT record | One key, `n`: URL-safe base64 endpoint info |
| Endpoint info | Bitfield byte (version, visibility, device type), 2-byte salt, 14-byte encrypted metadata key, length-prefixed UTF-8 device name, optional TLVs |
| Transport | Plain TCP on the port from the SRV record. Every protobuf message is prefixed with a 4-byte big-endian length |
| Handshake | ConnectionRequest → UKEY2 ClientInit → ServerInit → ClientFinish → ConnectionResponse. Encrypted from here on |
| Then | PairedKeyEncryption and PairedKeyResult both ways, Introduction from the sender, Response with ACCEPT, payload chunks |

Two things this does **not** settle, and neither should be assumed:

- Whether the 14-byte encrypted metadata key can be random when visibility is set
  to everyone, or whether it has to derive from real account state.
- Whether rquickshare fires its BLE advertisement on startup regardless of
  whether anything needs nudging. That question is not academic here: the
  measured `bluetoothd` segfault on this machine happens in rquickshare's
  *startup* path, so a peer that needs no nudging does not, by itself, stop the
  crash. See [reference setup](04-reference-setup.md).

Alternatives that do not solve the same problem: LocalSend, Warpinator and
Syncthing all use their own protocols. They move files perfectly well, but they
do not speak to the Quick Share that is already on the Pixel, which is exactly
what this project is after.

## Pixel Buds

Two projects with opposite profiles.

**pbpctrl** ([qzed/pbpctrl](https://github.com/qzed/pbpctrl)) — a CLI, and the
reference implementation. Reads detailed battery levels, hardware and software
information, and both reads and changes settings: ANC state and equaliser. It
targets the Pixel Buds Pro; with other models the README says it "may or may not
work". In the AUR as `pbpctrl` 0.1.8 and `pbpctrl-git`, **both untouched for 482
days** as of the query date.

**Measured against a clean VM on 16 August 2026, by the end-user agent:**
`pbpctrl` 0.1.8-1 builds and installs from the AUR untouched, in 49 seconds
wall-clock, on Omarchy 4.0.0 (ISO of 14 Aug 2026) with kernel 7.1.8-arch1-3.
`pacman -Q pbpctrl` returns `pbpctrl 0.1.8-1`. The 482 days are still true; the
inference drawn from them here — that a stalled package probably would not build
— was wrong. It was not run: the ban on touching anything BLE stands, so this
says the package compiles and nothing about whether it talks to anything.

Two halves, and only one is closed. Whether it still builds: yes, today. Whether
it speaks to Buds Pro 2, which use a different SoC: unanswerable in a VM and
waiting on hardware. And this is a fact with a shorter shelf life than most —
what compiles against today's Arch can break on the next dependency change,
precisely because nobody is maintaining the package. There is also `pbpctrl-plasmoid`, a Plasma widget: not directly
useful here, but a reference for how to consume the data.

**BudsLink** — much newer, with press coverage in June 2026. Graphical
interface, battery, ANC, ambient sound modes and gestures, speaking L2CAP/RFCOMM
directly. Supports AirPods, Galaxy Buds, Sony and Nothing; **Pixel Buds are
listed as possible future work, not as supported**. In the AUR as `budslink-git`
(90 days old at the time of the query).

One technical fact shapes the whole battery widget: over standard AVRCP you get
**a single combined battery figure** for both earbuds and nothing for the case.
Getting three separate readings requires the proprietary protocol, which is what
pbpctrl implements. The case only reports whether an earbud is inside it,
because it has no radio of its own.

## Clipboard, notifications, SMS

**KDE Connect** is the most complete option and lives in Arch's `extra`
repository. Bidirectional clipboard, notifications, file transfer, remote
control and SMS. It is the backbone of the whole "ecosystem" half of this
project.

**GSConnect** is the same idea integrated into GNOME Shell, so it does not apply
here — this is Hyprland.

What needs verifying under Hyprland: the clipboard against `wl-clipboard`,
notifications against the Omarchy daemon, and whether the tray indicator gets
along with the bar (which is Quickshell with SNI).

## What is closed today

**Google Cross-device services** — Instant Hotspot (tethering without a
password) and call casting (moving a call between devices). Announced at I/O
2024 and rolling out since July 2024, but **only between Android and ChromeOS
devices signed into the same Google account**. There is no Linux implementation,
official or third-party, as of the query date.

**Fast Pair** — the instant pairing when you open the case. Get the roles the
right way round before looking for something to port: in Google's specification
the **Provider** is the accessory advertising that it is ready to pair (the buds,
GAP Peripheral) and the **Seeker** is the phone looking for it (GAP Central). The
Pixel Buds already are a Provider, and there is nothing to write on that side.
What is missing is a Linux **Seeker** — and the account-linked half of the Seeker
role is where Play Services sits, which is the part that makes this F5 rather
than F3. No known Linux implementation, as of the query date.

*(Corrected on 15 August 2026: an earlier version of this section had the two
roles the wrong way round and said the provider side was missing.)*

These belong in the research drawer, not the work queue. See F5 in the
[roadmap](03-roadmap.md).

## Sources

- [rquickshare — README](https://github.com/Martichou/rquickshare/blob/master/README.md)
- [rquickshare-x (Windows fork)](https://github.com/oop7/rquickshare-x)
- [Installing RQuickShare on Linux](https://linuxtldr.com/install-rquickshare-on-linux/)
- [pbpctrl — README](https://github.com/qzed/pbpctrl/blob/main/README.md)
- [BudsLink brings advanced earbud controls to Linux desktops — Linux Journal](https://www.linuxjournal.com/content/budslink-brings-advanced-earbud-controls-linux-desktops)
- [BudsLink — OMG! Ubuntu](https://www.omgubuntu.co.uk/2026/06/budslink-airpods-galaxy-buds-linux)
- [Alternatives to KDE Connect](https://en.androidsis.com/Alternatives-to-KDE-Connect-for-connecting-Android-and-Linux/)
- [Cross-device services: call casting and internet sharing — 9to5Google](https://9to5google.com/2024/07/28/android-cross-device-services-rolling-out/)
- [Instant Hotspot, how to use it — Android Authority](https://www.androidauthority.com/android-cross-device-services-how-to-instant-hotspot-3478597/)
- [Google's Nearby Share protocol — grishka/NearDrop PROTOCOL.md](https://github.com/grishka/NearDrop/blob/master/PROTOCOL.md)
- [pyquickshare — Quick Share for Linux](https://github.com/teaishealthy/pyquickshare)
- [packet — Quick Share client for Linux](https://github.com/nozwock/packet)
- [Google Fast Pair Service — specification](https://developers.google.com/nearby/fast-pair/specifications/introduction)
- [Google Fast Pair integration — Nordic nRF Connect SDK docs](https://docs.nordicsemi.com/bundle/ncs-3.0.1/page/nrf/external_comp/bt_fast_pair.html)
