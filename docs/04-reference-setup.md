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

**Confirmed on 2026-08-16 by symbolizing all three core dumps.** The inference
above was right, and the backtrace says where. Identical in all three, with only
the ASLR base differing:

```
gdb -batch -q -iex 'set debuginfod enabled on' -iex 'set confirm off' \
    -ex 'set pagination off' -ex 'bt' \
    /usr/lib/bluetooth/bluetoothd core-1088.dump
```

```
#0  0x0000560c724cebf0 in ?? ()
#1  queue_find (queue=…, function=0x560c724cebf0, match_data=…)  src/shared/queue.c:230
#2  is_filter_match (discovery_filter=…, eir_data=…, rssi=-81)   src/adapter.c:7218
#3  btd_adapter_device_found (…, bdaddr_type=1, rssi=-81, …)     src/adapter.c:7437
#4  device_found_callback (index=0, …)                           src/adapter.c:7602
#5  queue_foreach (…, function=notify_handler, …)                src/shared/queue.c:207
#7  process_notify (mgmt=…, event=…, …)                          src/shared/mgmt.c:363
#8  can_read_data (io=…, user_data=…)                            src/shared/mgmt.c:423
#9  watch_callback (…)                                           src/shared/io-glib.c:173
```

Line 230 of `queue.c` is `if (function(entry->data, match_data))`, and
`function` holds `0x560c724cebf0` — an address in the heap, not in the mapped
text of the binary, which starts around `0x560c4c2…`. So `queue_find` is handed
a data pointer where a function pointer belongs and calls it. That is the
corrupted-function-pointer shape, now measured rather than inferred.

The call site is `adapter.c:7218`, `queue_find(eir_data->services, …)`, reached
while matching a received advertisement against the discovery filters
registered by D-Bus clients. Locals at that frame: `item = 0x560c724d1cc0`,
`l = 0x560c72486a50 = {0x560c724d2870, 0x560c7247fe80}`.

**What this establishes, and what it does not.**

*Measured:* the fault is in BlueZ, in the LE discovery path. All three crashes
happen processing an mgmt **Device Found** event with `bdaddr_type=1` — an LE
address — carrying a real advertisement (RSSI -81, -79, -74; the third dump's
payload is legible and belongs to a passing `Oclean X` toothbrush). `rquickshare`
appears nowhere in the stack; it is a separate process. It is the **trigger**,
because it turns on LE discovery with filters, not the thing that crashes.

**The root cause, measured, and it is not a corruption at all — the arguments
are swapped.** Reading the address that gets called settles it:

```
gdb -batch -q -ex 'x/s 0x560c724cebf0' /usr/lib/bluetooth/bluetoothd core-1088.dump
0x560c724cebf0:  "0000fe2c-0000-1000-8000-00805f9b34fb"
```

Identical in all three dumps. The value passed where `queue_find` expects a
match function is **a UUID string**, so nothing is corrupted or freed: the call
site hands `queue_find` its arguments in the wrong order and the string is
invoked as code. That matches the upstream diagnosis exactly — `is_filter_match()`
passing the UUID where the match function belongs, a slip introduced when that
code moved from `GSList` to `struct queue` — and it is confirmed here from the
dumps rather than taken on trust.

And the UUID names the trigger. `0xFE2C` is **Google Fast Pair**, which is the
service `rquickshare` filters on. That is why it looked like launching
`rquickshare` crashed `bluetoothd` — it registers the filter, and the next
stranger's advertisement does the rest.

**The UUID comes from the client's filter, not from the air.** Worth checking
rather than assuming, because it decides whether the crash can be dodged from
our side. The advertisement being processed in the first dump is from a device
called `PR BT 7152` and carries exactly one service:

```
p *(struct queue *)eir_data->services      -> {entries = 1}
x/s …->head->data                          -> "4553867f-f809-49f4-aefc-e190a1f459f3"
```

A custom 128-bit UUID, not Fast Pair. So `0000fe2c…` is the needle the client
asked BlueZ to look for, and `eir_data->services` is the haystack — which is
what the swapped arguments confirm: the needle ends up where the comparison
function belongs.

**Two conditions have to hold at once**, and the second is easy to miss: a
client registering a UUID discovery filter, **and** an advertisement that
carries at least one service. An advertisement with an empty service list
leaves `queue_find` with nothing to iterate, so the bad pointer is never
called. That is measurable here — the crashing dumps all show `entries = 1` —
and it explains why the crash is not instant: it waits for a neighbour that
advertises services.

**Fixed upstream, and not in the version installed here.** Derived from the
GitHub API by the coordination agent on 2026-08-16: the fix is commit
`82af2be`, dated 2026-07-09, while tag `5.87` is dated 2026-07-03 — six days
earlier. A tag cannot contain a later commit, and no `5.88` exists, so `bluez
5.87-2` on this machine cannot have it. **Do not open an upstream issue: it
would be a duplicate.** Two ways out, both product decisions rather than code:
build BlueZ with the patch, or wait for 5.88.

*Derived, and the reason this matters beyond F1:* if any other tool that brings
up LE discovery reaches the same code, it will crash `bluetoothd` the same way,
because nothing here is specific to `rquickshare`. That would put the defect
underneath the whole Bluetooth half rather than inside F1. It stays derived
until a second LE tool is measured against it — `pbpctrl` using BLE comes from
its README, not from a terminal here.

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

**That recovery is for a crash, and it does not cover a blocked radio. Measured
2026-08-16.** After `rfkill block bluetooth`, unblocking and following the
sequence above did not bring the mouse back: `unblock` reported `Soft blocked:
no`, the first connect returned `le-connection-abort-by-local`, and two further
attempts — one after a genuine fifteen-second pause, one after a `power off` /
`power on` cycle — both timed out at thirty seconds. `bluetoothctl info` showed
`Paired: yes, Trusted: yes, Connected: no` and `/dev/input/by-id/` had no mouse
node. `bluetoothd` was healthy throughout and no new segfault was recorded.

Nothing was broken: a Bluetooth mouse that loses its link waits to re-advertise
until it is moved or a button is pressed, and no software on this side can do
that. **So blocking the radio needs somebody physically at the machine**, which
the written recovery above quietly assumed and did not say. It was written from
the crash case, where the device is still awake and re-announces on its own.

Worth knowing before assuming the machine keeps a pointer: the Logitech
Unifying receiver present here has the **MX Keys keyboard** paired to it, not a
mouse — `0003:046D:408A` under the receiver, and the `…Receiver-if02-event-mouse`
node exists whether or not a mouse is paired, because the dongle exposes it
either way. The only mouse on this machine is the MX Master over Bluetooth.

This is a `doctor` check and a `doctor` remedy, and it is the kind of thing that
only shows up by breaking a real machine.

Two things this did not tell us. **The first is now answered by the backtrace
above; the second is not.**

- ~~**Whether the bug is rquickshare-specific or lives in BlueZ.**~~ **Answered
  2026-08-16: it lives in BlueZ**, and `rquickshare` is the trigger rather than
  the culprit — it appears nowhere in the stack. Worth reporting upstream as a
  BlueZ 5.87 defect. One correction to how this question was posed: the crash is
  in the **discovery** path, not the advertising path. It happens while
  processing an advertisement *received* from some other device, matching it
  against registered discovery filters, not while emitting one. That matters for
  reproducing it, because the second device involved is whatever happens to be
  advertising nearby — in the third dump, a passing toothbrush.
- **Whether it threatens F3.** Still open, and now the more valuable of the two.
  `pbpctrl` also talks to the earbuds over BLE on this same adapter and BlueZ
  version. Since the crash is in code that runs for any client that starts LE
  discovery, and nothing in the stack is specific to Quick Share, the whole
  Bluetooth half of this project may sit on top of it. **That remains derived**:
  it needs a second LE tool measured against this adapter, and that `pbpctrl`
  uses BLE comes from its README rather than from a terminal here.

## The adapter can do LE Audio and Auracast, on paper

Measured 2026-08-15 with `btmgmt info`, which needs no privileges. First
reported by the research agent from inside `docs/features.md`; re-run here
independently before being written down, because that file is declared derived
and this is a measurement of this machine.

`hci0` lists `cis-central`, `cis-peripheral`, `iso-broadcaster` and
`sync-receiver` in **both** `supported settings` and `current settings`. Those
are the isochronous-channel prerequisites for LE Audio and Auracast, and they
are not merely supported, they are active.

`btmgmt` also prints `version 12`. **Deliberately not translated into a
Bluetooth Core Specification number**: that mapping needs the SIG's Assigned
Numbers table and has not been checked. The evidence here is the flags, not the
version integer. It is also not the BlueZ userspace version, which is 5.87 and
unrelated.

**Contradiction resolved, 2026-08-15.** It was held open for a few hours on
purpose: a derived claim from a manufacturer spec sheet said this adapter was
Bluetooth 5.2, the controller reported `version 12`, and reconciling the two
needed the SIG's mapping — which was the unverified link. A measured integer
does not automatically beat a spec sheet when the mapping between them is what
nobody has checked.

Research then fetched the table. In the SIG's Assigned Numbers, the HCI Version
parameter maps `0x0B` to Core Specification 5.2 and `0x0C` to 5.3. `version 12`
is `0x0C`, so **the adapter is 5.3 and the spec-sheet claim of 5.2 was wrong**.
Still **derived** — that table came off the web, not out of this terminal — but
from the primary source rather than from a guess.
[Assigned Numbers](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Assigned_Numbers/out/en/index-en.html)

The flags remain the better evidence regardless. They say what this controller
will actually do; the version says only which document it claims to follow, and
an adapter can advertise 5.3 without exposing isochronous channels. The version
is context now, not the proof.

**What this does not say, and the distance is large.** It says the controller
exposes the capability. It says nothing about whether BlueZ and PipeWire can
complete a real broadcast, and nothing about whether Pixel Buds Pro 2 will pair
over LE Audio at all. Both remain unmeasured. Given that `bluetoothd` is
currently segfaulting on this same adapter, treat controller capability as the
floor of what is possible, not as a feature.

The journal on this machine is flooded by the `dizziee.system-stats` plugin,
which accounts for the overwhelming majority of lines. Filter it out:

```bash
journalctl -f -u bluetooth | grep -v 'dizziee.system-stats'
```

## The virtual peer does not touch Bluetooth — measured, not asserted

Recorded here rather than left in a message, because this is the gate that lets
the testing agent drive `tools/virtual-pixel/`, and a fact that lives only in a
message dies with the session.

Measured 2026-08-15. The emulator's own `--self-check` does **not** count as the
evidence: a program's opinion of itself is exactly what the doctor rule rejects.
What supports it is four external observations, taken across a full startup, an
mDNS advertisement and a completed simulated transfer.

```bash
systemctl show bluetooth -p MainPID --value                       # before and after
journalctl -k --since today | grep -c 'bluetoothd.*segfault'      # before and after
bluetoothctl info <mouse-mac> | grep Connected                    # stays yes
ls -l /proc/$(pgrep -f virtual-pixel.py)/fd | grep -ci bluetooth  # 0
```

| Check | Before | After |
|---|---|---|
| `bluetoothd` PID | 431109 | 431109, unchanged |
| Segfaults today | 3 | 3, no increment |
| Bluetooth mouse | connected | connected |
| Bluetooth file descriptors held by the process | — | 0 |

The bluetooth journal stayed quiet throughout. `strace -f -e trace=socket` would
have added the syscall half of this and **could not be run: strace is not
installed on this machine.** Stated plainly rather than quietly skipped, because
a missing half of a measurement is itself worth knowing.

## F2: the phone is linked, and not over the LAN

**Measured 2026-08-16.** The first working link to the phone in this project,
and the transport is not the one every earlier note assumed.

```
$ busctl --user call org.kde.kdeconnect /modules/kdeconnect \
    org.kde.kdeconnect.daemon devices bb true true
as 1 "<device-id>"

$ ss -tnp | grep 1716
ESTAB  [100.64.0.0/10 host]:1716  [100.64.0.0/10 host]:38748  users:(("kdeconnectd",…))

$ ip route get <phone>
… dev tailscale0 …
```

| Fact | Value |
|---|---|
| Device | Google Pixel 7 Pro, `type: phone` |
| Paired | yes |
| Reachable | yes |
| Transport | **Tailscale**, interface `tailscale0` |
| This host's physical subnet | `192.168.10.0/24` |
| Phone on that subnet | **no** — Hari is away from home |
| Plugins negotiated | 20, including clipboard, notifications, share, battery |
| Phone battery | 53 %, not charging |

**Every F2 measurement taken today is over a VPN, and none of them may be
written as "works on the LAN".** The two are different claims with different
failure modes: the LAN path needs broadcast, the same subnet and a permissive
firewall, and none of that was exercised here. `kdeconnect-cli` reports the
link as being over the LAN, which is wrong — one more instance of the rule
this machine keeps teaching, that a subsystem's account of itself is not
evidence. The transport was confirmed from `ss` and `ip route`, not from what
the tool said.

**Why LAN discovery had never happened**, established by the coordination agent
and consistent with what was measured here earlier: KDE Connect discovers over
UDP broadcast, and Tailscale does not carry broadcast. That is why the kernel
logged 10,675 `ufw` drops in three days and **zero** on port 1716 — the traffic
never left, so the firewall was never the obstacle. It needed
`customDevices=<phone>` in `~/.config/kdeconnect/config` and a daemon restart.

**Nothing is promoted in the matrix from this.** Pairing is the precondition
for the five F2 rows — clipboard, notifications, SMS, remote input, screen
mirroring — and is none of them. The plugin list says the two ends negotiated
those features, not that any of them carries data: `activeNotifications`
returned zero, which is equally consistent with "notifications work and the
phone has none" and with "notifications never arrive". Distinguishing those
needs somebody to produce a notification on the phone, and the phone is not
here.

`phone-link` in the status contract reports `ready` with the device in both
`devices` and `reachable`, which closes that loop: the contract was written
against a machine where nothing was paired, and it did not need a change when
something finally was.

## The notification server on Omarchy is Quickshell itself

**Measured 2026-08-17.** First established by the desktop-layer agent and
reproduced here before being written down, since this is a claim about the
machine rather than about a document.

```
$ busctl --user call org.freedesktop.Notifications /org/freedesktop/Notifications \
    org.freedesktop.Notifications GetServerInformation
ssss "quickshell" "quickshell" "" "1.2"
```

No separate notification daemon is running — no mako, dunst, swaync or
xfce4-notifyd — so there is nothing for the bar to collide with. It declares
six capabilities: `persistence`, `body`, `body-markup`, `body-hyperlinks`,
`actions`, `icon-static`.

Worth publishing because no Omarchy documentation says it, and anyone building
a notification-facing feature on this desktop has to guess otherwise. It also
sets the limit on what can be checked from a terminal: Quickshell keeps no
queryable history, so **whether a notification was drawn cannot be established
by asking anything.** That is why the `notifications` row stays `partial`. The
transport half is measured, the drawing half has a written reason rather than a
blank, and closing it needs the screen — which is the user's to authorise, not
ours to assume.

## Headroom on this machine, measured before anything is installed

**Measured 2026-08-17**, in normal working conditions: eleven agent sessions,
the advisor's VM, and the desktop up. Taken because a local LLM was proposed
and "does it fit" is the wrong question — the right one is what it displaces.

| Resource | Total | In use | Free |
|---|---|---|---|
| VRAM, Radeon RX 7900 XT | 20464 MiB | 4688 MiB (22 %) | **15.4 GiB** |
| VRAM, Raphael iGPU | 512 MiB | 15 MiB | — |
| RAM | 30 GiB | 22 GiB | **8.3 GiB available** |
| zram swap | 30.6 GiB | **7.1 GiB** | — |
| GPU utilisation, idle desktop | — | **21 %** | — |

**The headline is not the VRAM. The machine is already swapping.** 6733 MiB of
pages have been pushed out to zram, compressed 2.5:1 into 2743 MiB of physical
RAM. So this is not a question of whether loading a model *would* cause swap:
under a normal working load, with no model anywhere, it is already happening.
The 8.3 GiB `free` reports as available is what remains *after* that eviction.

**The largest single consumer is ours, not the user's:** `qemu-system-x86` at
5.8 GiB — the advisor's clean-install VM. Each agent session costs about
0.5 GiB. So the most effective way to free memory on this machine is to shut
down a VM nobody is using, and that is worth knowing before anything is bought
or installed.

**What is not measured, and matters most for the desktop:** what happens to
Hyprland when the GPU saturates. Hyprland composites on the same card that
would run inference, and idle utilisation is already 21 %. Establishing that
needs a load to be generated, which needs something installed, which needs
Hari's permission. Recorded as an open question rather than reasoned about:
"a 20 GiB card has room" is exactly the plausible-sounding shortcut this
project refuses to take.
