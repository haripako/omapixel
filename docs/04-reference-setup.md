# Reference setup

The machine the maintainer develops on. It is not a requirement — it is the
baseline that everything else gets compared against, so that when a report
differs we know what differed.

**Measured on 15 August 2026** with `scripts/hw-report.sh`. Unlike the
[landscape](01-landscape.md), this is not derived: it comes off the machine.

## Host

| Piece | State |
|---|---|
| Distro | Omarchy 4.0.0.alpha (edge channel), Arch-based |
| Compositor | Hyprland 0.56.2 |
| Kernel | 7.1.8-arch1-3 |
| Bar | Quickshell, with an SNI tray |
| BlueZ | 5.87-2 |
| Bluetooth adapter | MediaTek MT7922 (usb `0e8d:0608`) |
| Wired network | `eno1`, 192.168.10.0/24 |
| Wireless | `wlp11s0` present, not rfkill-blocked, not connected |
| Tailscale | active |
| Installed already | `wl-clipboard`, `gvfs-mtp`, `libmtp`, `waydroid`, `bluetoothctl`, `gio`, `udisksctl` |

## Devices

Declared by the maintainer on 2026-08-15. Only the Pixel 7 Pro is physically
present; nothing has been measured through any of them yet.

| Device | Role |
|---|---|
| Pixel 7 Pro | On hand and connected. **The test rig for F1 and F2**, and being traded in for the 11 Pro |
| Pixel 11 Pro | Not yet delivered. The eventual primary device |
| Pixel Buds Pro 2 | Not yet delivered. The target of F3 |
| Android 17 | The OS version in play |

Two consequences that shape the plan:

**F1 and F2 do not wait for the Pixel 11 Pro.** Quick Share and KDE Connect
depend on the Android version and Google Play Services, not on the Pixel model.
Whatever gets measured on the 7 Pro will need reconfirming on the 11 Pro, not
redoing.

**pbpctrl targets first generation Pixel Buds Pro, not the Pro 2.** Its README
says other models "may or may not work", and the Pro 2 use a different SoC, so
the proprietary protocol may not match. That is the largest single unknown in
the project and only the hardware can settle it.

## What is missing

From the official repositories:

```bash
sudo pacman -S kdeconnect android-tools scrcpy
```

From the AUR:

```bash
yay -S r-quick-share pbpctrl
```

Warning: `pbpctrl` had gone 482 days without an AUR update as of the query date.
It may not build against current Rust. If it fails, the fallback is
`budslink-git`, which does not list Pixel Buds as supported yet.

## Three things that condition the project

**No Google device is paired on this machine.** What is paired is an MX Master
3S, an RK-S98RGB keyboard, an Xbox headset and an Xbox controller. F0 is not a
formality: the buds have to physically arrive before anything in F3 can be
measured.

**The PC is on ethernet, not WiFi, and that turns out to be fine.** Measured on
2026-08-15: the phone sits in the same 192.168.10.0/24 as the wired host and is
reachable directly — 30 of 30 ICMP replies, TTL 64, and `ip route get` resolves
straight out of `eno1` with no gateway hop. Same layer 2 segment, not merely the
same subnet, so the access point is not isolating clients. Quick Share's hard
requirement is met without touching `wlp11s0`, which stays available as an
escape hatch if the network is ever re-segmented.

A sweep of the /24 the same day found 24 live hosts, seven with
locally-administered MAC addresses — the signature of phones with MAC
randomisation on. Worth knowing when debugging discovery later: this is a busy
home network, not a quiet lab.

**Latency to the phone is bimodal, and F1 will have to account for it.** Over 30
packets: zero loss, but a minimum of 4.8 ms against a median of 338 ms, a p90 of
694 ms and a maximum of 1141 ms, with 18 of 30 above 100 ms. Zero loss with that
spread is the shape of a WiFi client parking its radio between beacons.

That is an observation, not a diagnosis. It has **not** been established that
this is what causes the documented Quick Share discovery flakiness — the two are
merely consistent, and it would be exactly the sort of plausible-sounding
shortcut this project refuses to take. F1 tests it directly by repeating the
measurement with the phone's screen on.

**The Bluetooth adapter had form, and the mystery is now solved.** This machine
had a long-standing history of the MX Master dropping for no visible reason,
"without writing a line to the log". Measured on 2026-08-15: **`bluetoothd`
segfaults, and `journalctl -u bluetooth` never shows it because the kernel is
what records the crash.** Anybody looking in the obvious place was guaranteed to
find nothing, indefinitely.

```bash
journalctl -k --since today | grep 'bluetoothd.*segfault'
```

**Trigger, reproduced three times out of three:** launching `rquickshare`.

| Time | What was launched | Result |
|---|---|---|
| 23:00:34 | `rquickshare` (via a `--help` that it ignores and starts anyway) | `hci0: ACL packet for unknown connection handle`, mouse re-enumerates at 23:00:49 |
| 23:08:50 | `rquickshare` restarted | Mouse re-enumerates at 23:09:06 |
| 23:15:49 | `rquickshare` started as a controlled test | Segfault in the same second |

Killing `rquickshare` without restarting it does **not** produce a crash, so it
is the startup path — where the BLE listener comes up — and not shutdown.
systemd restarts `bluetoothd` each time and the mouse re-attaches after roughly
fifteen seconds. That gap is the input stall.

Crash signature: `segfault at 55f8f18e0f40 ip 000055f8f18e0f40`. The instruction
pointer equals the faulting address, meaning execution was transferred there.
**Inference, not yet confirmed:** that is the shape of a call through a corrupted
or freed function pointer. Confirming it needs the backtrace, and the core dumps
are root-owned (`coredumpctl` lists them as inaccessible without privileges).

**The crash has two outcomes, not one.** The first two times, systemd restarted
`bluetoothd` and the mouse re-attached after about fifteen seconds. The third
time it did not come back at all: BlueZ reported `Connected: yes` with the HID
UUID present, while `/proc/bus/input/devices` had no MX Master and the kernel
had logged no re-enumeration. A phantom connection — the ACL is up, the HID
profile never re-bound, so there is no input node and the user has no pointer.
That second form matches the machine's original "drops and does not reconnect"
symptom exactly.

**Recovery, measured, and the ordering matters.** Naive retries make it worse:

| Step | Result |
|---|---|
| `bluetoothctl disconnect` | Works |
| `bluetoothctl connect` immediately after | `org.bluez.Error.Failed le-connection-abort-by-local` |
| `power off` then `power on`, then connect | `br-connection-canceled` |
| Two more connects straight away | `org.bluez.Error.InProgress` — the retries queue behind a pending attempt and block each other |
| Wait for the pending attempt to expire, then connect | **Succeeds.** HID re-binds, `HID++ 4.5 device connected` |

So the recovery is a disconnect, a genuine pause, and one connect. Retrying
faster is actively counterproductive:

```bash
bluetoothctl disconnect [mac redacted]; sleep 15; bluetoothctl connect [mac redacted]
```

This is a `doctor` check and a `doctor` remedy, and it is the kind of thing that
only shows up by breaking a real machine.

Two things this does not yet tell us, and both matter:

- **Whether the bug is rquickshare-specific or lives in BlueZ's advertising
  path.** If plain BLE advertising crashes `bluetoothd` too, this is a BlueZ
  5.87 bug worth reporting upstream rather than an integration quirk.
- **Whether it threatens F3.** `pbpctrl` also talks to the earbuds over BLE on
  this same adapter and BlueZ version. If the crash is in the BLE path rather
  than in anything Quick Share does, the entire Bluetooth half of this project
  sits on top of it.

## A note for anyone reading logs on Omarchy

The journal on this machine is flooded by the `dizziee.system-stats` plugin,
which accounts for the overwhelming majority of lines. Filter it out:

```bash
journalctl -f -u bluetooth | grep -v 'dizziee.system-stats'
```
