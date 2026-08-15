<!-- GENERATED FILE — DO NOT EDIT BY HAND. -->
<!-- Edit data/capabilities.toml or data/devices/*.toml, then run:
     scripts/build-matrix.py -->

# Capability matrix

What the Apple ecosystem does between iPhone and Mac, what can be done today between a Pixel and Arch Linux, and with which tool.

Built from 1 device report. Every cell traces back to a named reporter and a date; see the per-device sections below.

**Read `untested` as untested, not as broken.** An absent result means nobody has run it on that hardware, which is the most common state in a young project. See [conventions](conventions.md) for what the statuses and the measured/derived distinction mean.

## Summary

| Capability | Apple equivalent | Phase | Tool | Reported |
|---|---|---|---|---|
| Send files to the phone | AirDrop | F1 | `rquickshare` | untested |
| Receive files from the phone | AirDrop | F1 | `rquickshare` | untested |
| Shared clipboard | Universal Clipboard | F2 | `kdeconnect` | untested |
| Phone notifications on the desktop | Notification Centre | F2 | `kdeconnect` | untested |
| Send and read SMS from the desktop | Messages | F2 | `kdeconnect` | untested |
| Phone as remote control or keyboard | Continuity | F2 | `kdeconnect` | untested |
| Phone screen on the desktop | iPhone Mirroring | F2 | `scrcpy` | untested |
| Per-earbud and case battery | AirPods battery in Control Centre | F3 | `pbpctrl` | untested |
| Read and set ANC mode | Noise control | F3 | `pbpctrl` | untested |
| Read and set the equaliser | Headphone accommodations | F3 | `pbpctrl` | untested |
| Omarchy bar widget for buds and phone | Control Centre | F4 | `omapixel` | untested |
| Hyprland keybindings (cycle ANC, send file to phone) | — | F4 | `omapixel` | untested |
| Entry in the Omarchy menu | — | F4 | `omapixel` | untested |
| Instant pairing when the case opens | AirPods pairing | F5 | `—` | untested |
| Tethering without entering a password | Instant Hotspot | F5 | `—` | untested |
| Move a call between devices | Call handoff | F5 | `—` | untested |
| Continue an app across devices | Handoff | F5 | `—` | untested |

### Constraints worth knowing

- **Send files to the phone** — Requires both devices on the same LAN subnet.
- **Receive files from the phone** — Android advertises its mDNS intermittently; discovery is the weak point.
- **Shared clipboard** — Needs verifying against wl-clipboard under Wayland.
- **Phone notifications on the desktop** — Must coexist with the Omarchy notification daemon.
- **Phone screen on the desktop** — Needs USB debugging or ADB over WiFi.
- **Per-earbud and case battery** — Standard AVRCP gives one combined figure only. Three separate readings require the proprietary protocol. The case has no radio of its own and only reports whether an earbud is inside.
- **Omarchy bar widget for buds and phone** — Nothing exists for this. It is the original work in this project.
- **Instant pairing when the case opens** — In the Fast Pair spec the buds are the Provider and the phone is the Seeker, so Linux would have to implement the Seeker side. No known implementation, and the account-linked half of that role leans on Play Services.
- **Tethering without entering a password** — Google Cross-device services: same Google account, Android and ChromeOS only.
- **Move a call between devices** — Google Cross-device services. Same constraint as instant-hotspot.
- **Continue an app across devices** — No equivalent concept outside Apple-to-Apple or Google-to-Google.

## Reports

### Google Pixel 7 Pro

Reported by **haripako** on 2026-08-15 (phone, Android 17).

Host — distro: Arch Linux; desktop: Omarchy 4 (edge) / Hyprland; kernel: 7.1.8-arch1-3; bluez: 5.87; bt_adapter: MediaTek MT7922 (usb 0e8d:0608).

No capabilities tested yet on this device.

