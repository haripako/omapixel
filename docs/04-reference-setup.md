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

**The PC is on ethernet, not WiFi.** Quick Share needs both devices on the same
network. If the phone joins the same router over WiFi and lands in
192.168.10.0/24, it should work — but that has to be confirmed, and it is the
most likely first point of failure. If the router segregates WiFi from wired,
the escape hatch is `wlp11s0`: the radio exists and is unblocked, just
disconnected, so the PC can join the same WiFi.

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
