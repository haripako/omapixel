# Development environment vs. the final product

This project has to end up on machines that are not this one: other distros,
other compositors, other Bluetooth adapters, other phones. That only works if we
are explicit about **which of the two things we are building at any moment**,
because they have opposite priorities.

Everything in the evidence section **happened here and was measured**. The
requirements drawn from it are judgement, and are marked as such. See
[conventions](conventions.md).

## The two environments, side by side

| | Development environment | Final product |
|---|---|---|
| Who | The maintainer, and contributors reporting hardware | Somebody who wants their Pixel to talk to their Linux box |
| Success | A measurement that can be reproduced and trusted | It works, and when it does not, it says why |
| Install | Build from source. Auditable, matches `SECURITY.md` | Prebuilt. A multi-minute Rust build is a lost user |
| Slowness | Acceptable. One-off cost | Not acceptable |
| Manual steps | Acceptable, if documented | Every manual step is a user lost |
| Distro | Arch and Omarchy, because that is what is here | Must not assume `pacman`, Hyprland, or systemd user units |
| Wrong answers | The worst outcome. A bad measurement is published as fact | Bad, but a silent failure is worse |
| Tolerated failure mode | Loud and early | Never silent. Silence generates every support request |

The one rule that spans both: **a check you cannot run locally is a check you
will break**, and **a measurement bug is worse than a crash**, because a crash
tells you.

---

## Development environment

What it is for: producing numbers that go into the capability matrix and can be
trusted by somebody who was not in the room.

**Requirements (judgement, from the evidence below):**

- Build from source where practical. It is auditable and the wait is paid once.
- Force `LC_ALL=C` in anything that parses command output, and prefer
  machine-readable formats (`ip -json`, `--format` flags) over human text.
  Non-negotiable: this project's entire value is measurement.
- Contributor setup must install the same lint tooling CI runs. Right now
  `shellcheck` runs in CI and is absent here, so that job cannot be reproduced
  before pushing.
- Repository identity set deliberately per project, not inherited.
- Device reports carry a `[host]` block, because the adapter and the compositor
  are variables in the result, not background detail.

## Final product

What it is for: somebody who has never read this repository getting their phone
and their desktop talking.

**Requirements (judgement, from the evidence below):**

- **One command to install**, resolving to prebuilt artefacts.
- **Dependencies expressed as data, not as shell.** A table of
  `capability -> tool -> {arch, fedora, debian, flatpak}`, so supporting Fedora
  is a data change rather than a rewrite. Same pattern
  `data/capabilities.toml` already uses for the matrix.
- **A `doctor` command**, which is the single highest-value thing on this list.
  Every failure mode found during bring-up was silent, so the product must
  actively diagnose rather than wait to be debugged. In order: same subnet,
  actual reachability, firewall ports, daemon alive, autostart wired, USB mode,
  adb authorisation, Bluetooth adapter present. Each check names the fix.
- **No assumption that the desktop behaves like this one.** No systemd user unit
  where none exists, no reliance on XDG autostart being processed.
- **A stable internal interface for the earbuds**, so that upstream dying costs
  one file rather than a rewrite of the bar widget.

`scripts/hw-report.sh` is already two thirds of `doctor`: it reports state but
does not judge it or prescribe. Finishing that job serves both audiences at
once — the user runs it when nothing works, the contributor runs it to file a
report.

---

# Evidence

Everything below was measured during bring-up on 15 August 2026. The **Hits**
column says which environment each one damages.

## The install path is the portability problem

| | |
|---|---|
| Hits | Product, badly |

Every dependency came from Arch: `pacman -S kdeconnect android-tools scrcpy`,
`yay -S r-quick-share`. On Fedora, Debian or openSUSE none of that exists. The
AUR is not a package source, it is a build recipe format for one distro.

`r-quick-share` from the AUR is a Tauri application — a Rust release build plus a
pnpm frontend build. It pulled in `pnpm` as a dependency and was still compiling
after 582 crates. `r-quick-share-bin` is the same 0.11.5, prebuilt.

## Upstream is the risk, not our code

| | |
|---|---|
| Hits | Both |

`pbpctrl`, the only tool that reads per-earbud battery and ANC, had gone 482 days
without an AUR update. It targets first-generation Pixel Buds Pro; the Pro 2 use
a different SoC.

## Failures that look like nothing happening

| | |
|---|---|
| Hits | Product, and it is the category that generates every support request |

All of these were hit in one evening.

- **Firewall.** `ufw` is active here. KDE Connect needs 1714-1764 TCP and UDP. If
  the policy blocks them, discovery never happens: no error, no log.
- **Daemon not running.** `kdeconnectd` ships no systemd unit. It relies on
  `/etc/xdg/autostart` plus D-Bus activation, and was not running after install
  because the session predated the package. It started only when something spoke
  to it over D-Bus.
- **Autostart is compositor-dependent.** It works here because
  `xdg-desktop-autostart.target` is active in this session. That is a property of
  this setup, not of Linux.
- **USB mode.** The phone appeared first as `18d1:4ee7` (charging and adb, no
  MTP), later as `18d1:4ee2` (MTP and adb), because the mode was changed on the
  phone mid-session. Tools expecting MTP see nothing in the first state.
- **adb authorisation.** `adb devices` reported `unauthorized`. It needs the
  phone unlocked and a dialog accepted; nothing on the desktop side fixes it.
- **Same subnet is not enough.** The phone shares 192.168.10.0/24 with the host,
  but that only became meaningful once reachability was tested: 30/30 replies,
  TTL 64, no gateway hop. An access point isolating clients produces the same
  subnet and a dead transfer.

## Do not parse human output

| | |
|---|---|
| Hits | Development, hardest |

A latency percentile calculation produced nonsense — `min 146.0, p90 6.8, max
9.0` — because `sort -n` was interpreting decimals under a comma-decimal locale.
It was caught only because the numbers were absurd on sight. A subtler error
would have shipped into the published matrix.

`ping` output is localised: the field was `tiempo=` here and `time=` on an
English system. Grepping for one silently produces nothing on the other.

## Hardware identity is not what it used to be

| | |
|---|---|
| Hits | Both |

A sweep of the LAN found 24 hosts, seven with locally-administered MAC addresses
— phones with MAC randomisation on. The Pixel could not be identified by vendor
OUI, because a randomised MAC has no vendor. Any "find your phone on the network"
feature cannot lean on OUI lookup.

The Bluetooth adapter here, a MediaTek MT7922, has a history of unexplained
disconnections with an unrelated device. A report saying "buds battery works"
without saying on which adapter cannot be reproduced.

## Repository hygiene

| | |
|---|---|
| Hits | Development |

The first commits carried a work email into a public repository. Removing it
required rewriting history, and the orphaned objects stayed reachable by direct
SHA on GitHub afterwards; the repository had to be deleted and recreated to be
sure. Deleting it needed a `gh` token scope that was not granted, which needs a
browser and cannot be scripted.

---

## Order of work

1. **`doctor`** — turns `hw-report.sh` from a reporter into a diagnostician.
2. **Dependencies as data** — per-distro table instead of hardcoded `pacman`.
3. **Stable interface for the earbuds** — upstream dying costs one file.

None of it before F1 to F3 have produced real measurements. Packaging something
that has not been shown to work is how projects end up with an elegant installer
for something broken.
