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

**The Bluetooth adapter has form.** This MT7922 has a history of unexplained
disconnections with the MX Master: it drops and does not reconnect, without
writing a line to the log. If anything odd happens while pairing the buds,
suspect the adapter before blaming the new software.

## A note for anyone reading logs on Omarchy

The journal on this machine is flooded by the `dizziee.system-stats` plugin,
which accounts for the overwhelming majority of lines. Filter it out:

```bash
journalctl -f -u bluetooth | grep -v 'dizziee.system-stats'
```
