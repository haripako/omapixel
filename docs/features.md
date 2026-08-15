# Feature targets: what Apple does, and what the equivalent would be here

**Derived from web research on 15 August 2026.** It is a target list, not a
status report — the status lives in the [capability
matrix](02-capability-matrix.md) and the [roadmap](03-roadmap.md).

Measured claims are tagged **measured** inline, with their date and the command
that produced them. Everything else here is derived. See
[conventions](conventions.md).

## Why Apple is the yardstick

Not because the goal is to clone macOS. Because Apple is the only vendor that has
shipped the whole surface — files, clipboard, notifications, calls, screen,
camera, audio, earbuds, pairing, presence — as one coherent thing, so their
feature list is the most complete inventory available of *what "the devices work
together" actually means* once you break it down.

Two honest caveats before the tables:

1. **Apple's version works because both ends are Apple.** Half of Continuity is
   not clever protocol design, it is the same company controlling the phone, the
   laptop and the account. Here one end is a Pixel we do not control and the
   other is a Linux box Google has never heard of. Some rows are therefore not
   "unimplemented", they are **structurally unavailable**, and this document says
   so instead of pretending they are a matter of effort.
2. **Google's own ecosystem does not have parity either.** Where Apple has
   Handoff, Google has some Chrome tab sync and a Cross-device SDK limited to
   Android and ChromeOS. So for several rows the ceiling is not "what Apple does"
   but "what Android can be made to do at all", which is lower.

## How to read the tables

Every target gets a tier. The tier is the honest answer to "what kind of work is
this", not a priority.

| Tier | Means |
|---|---|
| **T1 — assemble** | Something already exists that does this. The work is installing it, measuring it, and wiring it into Omarchy |
| **T2 — build** | The pieces exist but the feature does not. This repository writes the glue. This is where the original work is |
| **T3 — reverse** | Needs protocol work nobody has done for Linux. Research, with no promise |
| **T4 — closed** | No path today. Documented so nobody rediscovers the wall |

`id` is the proposed capability id if the row is ever promoted into
`data/capabilities.toml`. Ids in **bold** already exist there.

---

## A. Moving content between devices

| Apple | What it actually does | Path on Linux today | Target here | Tier | id | Phase |
|---|---|---|---|---|---|---|
| AirDrop (receive) | Anyone nearby can push a file to you with no setup | rquickshare speaks the real Quick Share protocol | Receive from the Pixel without a cable | T1 | **file-receive** | F1 |
| AirDrop (send) | Push a file to a nearby device from the share sheet | rquickshare | Send to the Pixel | T1 | **file-send** | F1 |
| AirDrop from anywhere in the OS | It is in *every* share sheet, not in an app you open | rquickshare is a standalone app with a tray icon | "Send to phone" in the file manager context menu and on a Hyprland keybinding, acting on the current selection | T2 | `share-to-phone` | F4 |
| AirDrop to self | Your own devices are always visible to each other | Quick Share has the same concept, tied to the Google account, which Linux cannot join | Measure whether rquickshare gets treated as "everyone" only, and what that costs in taps | T1 | `share-to-self` | F1 |
| Universal Clipboard (text) | Copy on one device, paste on the other, no action in between | KDE Connect clipboard plugin; Chrome's shared clipboard as an independent fallback if you are signed into Chrome Sync on both ends | Copy on the phone, paste in a Wayland app | T1 | **clipboard** | F2 |
| Universal Clipboard (images, files) | The same for images and video, not just text | KDE Connect's clipboard has historically been text-only; `wl-clipboard` handles arbitrary MIME types on this end | Image on the clipboard, both directions. Likely needs falling back to Quick Share for anything large | T2 | `clipboard-image` | F2 |
| Handoff | Start a mail draft on the phone, finish it on the laptop, for any Handoff-aware app | Nothing general exists. Chrome "send to your devices" moves a tab and that is the whole of it | Move the current URL between phone and desktop on a keybinding. Do not promise more than URLs | T2 | `url-handoff` | F4 |
| Handoff (arbitrary apps) | Any app can publish a resumable activity | Requires an OS-level activity API on both ends. Android's Cross-device SDK is Android↔ChromeOS | None. Documented as closed | T4 | **app-handoff** | F5 |
| NameDrop | Hold two phones together to swap contact cards | No Linux-side concept, and the desktop has no contact card to offer | None | T4 | — | — |
| Continuity Sketch / Markup | Draw on the phone, it appears live in a Mac document | Nothing, and no obvious Wayland integration point | None. Noted only for completeness | T4 | — | — |

**Note on protocol churn.** Google shipped Quick Share↔AirDrop interoperability
on the Pixel 10 in late 2025 and has been widening it across flagships through
2026. That is not a feature this project can use, but it means the Quick Share
protocol is being actively changed on the Android side, which is a standing risk
to rquickshare. Worth watching, not worth acting on.

---

## B. Messages, calls and notifications

| Apple | What it actually does | Path on Linux today | Target here | Tier | id | Phase |
|---|---|---|---|---|---|---|
| Text Message Forwarding | SMS and MMS from the phone appear in Messages on the Mac and can be answered there | KDE Connect SMS plugin. Google Messages for Web is the account-based fallback, in a browser tab | Read and send SMS from the desktop | T1 | **sms** | F2 |
| Notification Centre relay | Phone notifications appear on the Mac, and actions work from there | KDE Connect notifications plugin, including reply actions | Phone notifications through the Omarchy daemon, without duplicating or fighting it | T1 | **notifications** | F2 |
| iPhone Cellular Calls | Take and make phone calls on the Mac, with the Mac's mic and speakers | KDE Connect's telephony plugin only notifies and mutes. Real call audio needs the PC to act as a Bluetooth **handsfree unit** (HFP HF role), which PipeWire's BlueZ backend claims to support | Two separate targets: the notification (cheap) and the audio path (unmeasured, and the interesting one) | T1 / T2 | `call-notify`, `call-audio` | F2 / F3 |
| SMS code autofill | A one-time code arriving by SMS is offered directly in the Mac's password field | Nothing. But the notification is already crossing the wire via KDE Connect | Pull the code out of the incoming notification, put it on the clipboard, say so. Small, self-contained, high daily value | T2 | `otp-autofill` | F4 |
| Focus / Do Not Disturb sync | Silencing one device silences the others | KDE Connect can trigger commands on either end; no Focus concept exists on Linux to sync *to* | Bidirectional DND: Omarchy's quiet mode silences the phone and the reverse | T2 | `focus-sync` | F4 |
| Phone battery in Control Centre | The phone's battery is just visible on the Mac | KDE Connect battery plugin exposes it over D-Bus | The figure on the Quickshell bar, next to the buds | T2 | `phone-battery` | F4 |
| Find My iPhone → play sound | Ring the phone from the laptop | KDE Connect findmyphone plugin, on the LAN | Ring the phone from the Omarchy menu | T1 | `ring-phone` | F2 |
| Call handoff between devices | Move an in-progress call from phone to Mac and back | Google's Cross-device services do this, Android↔ChromeOS only, tied to one Google account | None | T4 | **call-casting** | F5 |

---

## C. Screen, display and input

| Apple | What it actually does | Path on Linux today | Target here | Tier | id | Phase |
|---|---|---|---|---|---|---|
| iPhone Mirroring | The phone's screen in a window on the Mac, fully interactive, phone stays locked | scrcpy, over USB or ADB-over-WiFi. On several axes it is *better* than Apple's: audio forwarding, two-way clipboard, UHID input, OTG mode without USB debugging | A window on demand, plus deciding whether ADB-over-WiFi is acceptable to leave enabled | T1 | **screen-mirror** | F2 |
| Sidecar | The iPad becomes a second display for the Mac | Reverse direction on Android is weak. Deskreen serves the desktop to a browser on the phone; scrcpy can drive a virtual display | The phone as a genuine extra Hyprland output is the honest ambition, and it is not close | T2 | `second-display` | F5 |
| Universal Control | One keyboard and mouse drive the Mac and the iPad, cursor crosses the screen edge | KDE Connect remote input drives the phone from the desktop; scrcpy UHID does it properly when mirroring | Drive the phone from the desktop keyboard. Edge-crossing without a mirror window is the hard part | T2 | **remote-input** | F2 |
| AirPlay screen mirroring, phone → Mac | Phone throws its screen at the Mac with no cable and no debugging | Android dropped Miracast; Pixels cast. There is no credible open Cast **receiver** for Linux | None. scrcpy covers the need by a different road, at the cost of ADB | T4 | `screen-cast` | F5 |
| iPhone widgets on Mac | Phone widgets sit on the Mac desktop and are clickable | Nothing exists | The Omarchy bar widget: buds battery, phone battery, phone connectivity, transfer status. **This is the original work in this project** | T2 | **bar-widget** | F4 |
| Auto Unlock with Apple Watch | The Mac unlocks because a trusted device is nearby | KDE Connect has a lock/unlock plugin; PAM proximity modules exist and are a genuinely bad idea done carelessly | Lock the session when the phone leaves. **Unlocking** on proximity should be treated as a security decision, not a feature | T2 | `proximity-lock` | F5 |
| Mac Virtual Display / Mirror My View | Vision Pro features | No hardware, no relevance | Out of scope | — | — | — |

---

## D. The phone as a peripheral

| Apple | What it actually does | Path on Linux today | Target here | Tier | id | Phase |
|---|---|---|---|---|---|---|
| Continuity Camera (webcam) | The iPhone becomes the Mac's webcam automatically, with no app on either side | Two roads. Android 14+ has a native USB webcam mode that presents the phone as a standard **UVC** device — but it is not enabled on every device, since it needs kernel config, USB HAL and a preloaded app. Otherwise scrcpy `--v4l2-sink` into `v4l2loopback` | Measure whether the Pixel exposes UVC at all. If it does, this is nearly free; if not, it is a v4l2loopback wrapper | T1 / T2 | `webcam` | F4 |
| Continuity Camera (scan / photo into a document) | Take a photo or scan on the phone, it lands in the Mac document you were editing | Nothing joined-up. Quick Share plus a watched directory gets most of the way | Scan on the phone, file appears in a known place and is announced | T2 | `doc-scan` | F4 |
| Desk View | Overhead view of the desk from the ultra-wide camera | No equivalent hardware behaviour to target | Out of scope | T4 | — | — |
| Live Listen | The phone becomes a remote microphone feeding your earbuds | The reverse is what is useful here: the phone as a microphone for the PC, over Bluetooth HFP or through scrcpy's audio path | Low priority, but it falls out of `call-audio` for free | T2 | `phone-mic` | F4 |
| AirPlay audio, phone → Mac | Phone plays through the Mac's speakers | PipeWire's BlueZ backend can take the **A2DP sink** role, making the PC a Bluetooth speaker | Phone audio out of the desktop speakers, on demand, without breaking the buds' own routing | T2 | `phone-audio-in` | F3 |
| Now Playing / media control | Control what is playing on either device from the other | KDE Connect MPRIS plugin, both directions | Media keys control the phone when it is the thing playing | T1 | `media-control` | F2 |

---

## E. Earbuds

This is the section with the most Apple features and the least Linux tooling, and
it is [F3](03-roadmap.md#f3--pixel-buds) — the phase already flagged as the
riskiest. `pbpctrl` targets the first-generation Pixel Buds Pro and had not been
updated in 482 days as of the landscape query; the Buds Pro 2 use a different
SoC. Every row below is conditional on something responding at all.

As of the night of 15 August 2026 it is conditional on something further down,
too. **Measured by another contributor on the reference machine:** `bluetoothd`
segfaults when rquickshare's BLE listener starts, reproduced 3 times out of 3.
The crash is logged by the kernel, not by `journalctl -u bluetooth`, which is why
this machine's long history of Bluetooth drops never left a trace anywhere anyone
was looking. The write-up is in
[`04-reference-setup.md`](04-reference-setup.md).

Whether it reaches this section is a three-link chain, and only the first link is
measured. Labelled, because the temptation to collapse it is the whole reason
this repository has a conventions file:

- **Measured** — launching rquickshare crashes `bluetoothd`, 3 out of 3, on this
  adapter with BlueZ 5.87.
- **Derived** — `pbpctrl` reaches the earbuds over BLE. That comes from its
  README. It is not installed here and nothing has been run against it.
- **Hypothesis, untested** — that the fault lives in the BLE path rather than in
  something Quick Share does. If it holds, the crash sits *underneath* this whole
  section instead of beside it. One isolation test settles it, and it needs
  hardware that has not arrived.

The precaution is worth taking before the hypothesis is settled rather than
after: **do not read a failure in any row below as evidence about the earbuds
until that isolation test has been run.** The cost of the precaution is nothing;
the cost of skipping it is blaming the Buds for an adapter fault on the first
measurement of F3, and believing it.

| Apple | What it actually does | Path on Linux today | Target here | Tier | id | Phase |
|---|---|---|---|---|---|---|
| AirPods battery in Control Centre | Three separate figures: left, right, case | Standard AVRCP gives **one combined number** and nothing for the case. Three readings need the proprietary protocol, which is what `pbpctrl` implements. The case has no radio and only reports whether a bud is inside | Three figures on the bar, or an honest one figure if that is all that comes back | T1 | **buds-battery** | F3 |
| Noise control (ANC / Transparency) | Switch modes from the device, the phone or the Mac | `pbpctrl` reads and sets ANC state | Read and set from a keybinding | T1 | **buds-anc** | F3 |
| Headphone accommodations / EQ | Per-user audio tuning stored on the buds | `pbpctrl` reads and sets the equaliser | Read and set | T1 | **buds-eq** | F3 |
| Proximity pairing | Open the case near the Mac and a card appears offering to pair | Fast Pair. Note the role naming: the **earbuds** are the Fast Pair *Provider*, the phone is the *Seeker* — so Linux would have to implement the **Seeker** side, and the account-linked half of that leans on Play Services | Research only | T3 | **fast-pair** | F5 |
| Automatic device switching | The AirPods follow whichever device starts playing | Pixel Buds Pro 2 have Bluetooth multipoint, so *the buds* can hold both links. Linux has no automatic handover logic at all | Grab and release the buds from a keybinding or the bar. Not automatic, but one gesture instead of two menus. **Realistically the highest daily value in F4** | T2 | `buds-multipoint` | F4 |
| In-ear detection | Take a bud out, the audio pauses; put it back, it resumes | The buds detect it; whether the event is exposed over the proprietary protocol is unknown, and `pbpctrl` is not documented as surfacing it | Find out if the event is readable. If it is, pause MPRIS on it | T3 | `buds-inear` | F3 |
| Audio Sharing | Two sets of AirPods on one device's audio | The open equivalent is **Auracast** over LE Audio. BlueZ 5.85 has full BAP support and PipeWire 2.0 added Auracast broadcasting; controls for browsing broadcasts and switching between LE Audio and classic Bluetooth were still listed as work in progress, with SIG qualification aimed at 2026. Both ends need a controller that does isochronous channels | Genuinely new ground, and the controller on this end is not the obstacle. **Measured on the reference machine, 15 Aug 2026, `btmgmt info`:** `hci0` lists `iso-broadcaster`, `sync-receiver`, `cis-central` and `cis-peripheral` as supported *and* currently enabled — the isochronous prerequisites for LE Audio and Auracast are live at the controller. (It also reports `version 12`; turning that into a Core Spec number needs the SIG's Assigned Numbers table and has not been checked, so the flags are the evidence here, not the number.) The canonical home for this measurement is [`04-reference-setup.md`](04-reference-setup.md) and it has **not been carried over there yet**. Three things above the controller stay unmeasured, and the load-bearing one is now the far end: **that the Buds Pro 2 do Auracast at all is derived from product copy, about hardware that has not arrived**. Then BlueZ and PipeWire actually completing a broadcast, and the buds pairing over LE Audio. See the crash note under [Earbuds](#e-earbuds) before assuming the stack is healthy | T2 / T3 | `buds-auracast` | F5 |
| Announce Notifications | Siri reads incoming notifications into the buds and you reply hands-free | Nothing. But notifications already arrive via KDE Connect and Linux has decent local TTS | Read selected notifications into the buds. Reply is out of reach; announcement is not | T2 | `buds-announce` | F4 |
| Find My AirPods | Ring the buds, and precision-find them | Unknown whether the ring command is in the proprietary protocol `pbpctrl` speaks | Check. If it exists it is a one-line wrapper | T3 | `buds-find` | F3 |
| Gesture customisation | Remap taps, press-and-hold, swipes | Set in the Google app on the phone. Whether the settings are writable over the same channel as ANC and EQ is unknown | Check while inventorying what `pbpctrl` returns | T3 | `buds-gestures` | F3 |
| Spatial Audio with head tracking | Head-tracked spatial rendering | Proprietary, and on the Pixel side it requires a compatible Pixel phone doing the rendering | None | T4 | — | — |
| Adaptive Audio / Conversation Awareness | ANC and Transparency blended automatically; media ducks when you speak | Runs on the buds' own SoC, driven by the phone. Nothing to drive from Linux | None. If it is a mode the buds can be *put into*, it collapses into `buds-anc` | T4 | — | — |
| Firmware updates | Delivered silently by the paired device | Google app only | None | T4 | — | — |
| Ear tip fit test / hearing test | On-device audiometry | Phone-only, and medical-adjacent | Out of scope | T4 | — | — |

---

## F. Network, identity and finding things

| Apple | What it actually does | Path on Linux today | Target here | Tier | id | Phase |
|---|---|---|---|---|---|---|
| Instant Hotspot | The phone's hotspot appears in the Mac's Wi-Fi menu and connects with no password, and turns itself off after | Google's equivalent is Cross-device services: same Google account, Android and ChromeOS only. No Linux implementation, official or otherwise | Research. A KDE Connect run-command triggering a phone-side automation is the crude workaround, and it is crude | T3 | **instant-hotspot** | F5 |
| Wi-Fi password sharing | Hold a device near another and it offers the network password | Android shares a network as a **QR code**, which is an open, documented format Linux can both generate and read | Read the QR from the phone screen and join the network; and offer this machine's network as a QR. Small, offline, no account, actually achievable | T2 | `wifi-qr` | F4 |
| Find My / device location | Find any device on a crowdsourced network, precision-find nearby ones | Find Hub is web and Android only; no Linux client and no open protocol. `ring-phone` above covers the LAN case only | None beyond the LAN | T4 | — | F5 |
| iCloud Keychain | Passwords and passkeys sync everywhere, autofill everywhere | Google Password Manager has no Linux client outside Chrome. The honest substitute is Bitwarden or KeePassXC, which is a different product, not parity | Out of scope. Named here so the gap is on the record | T4 | — | — |
| Apple Pay confirmation on the phone | Authorise a desktop payment with the phone | Nothing comparable, and nothing worth building | Out of scope | T4 | — | — |
| iCloud Drive / Desktop & Documents / Photos | Files and photos are simply the same on both devices | rclone against Google Drive and Photos, or Syncthing device-to-device | Out of scope. It is a sync problem, not a continuity problem, and it is already solved by tools that owe this project nothing | — | — | — |
| Quick Start (device setup) | Set up a new device by holding it next to the old one | Not applicable between a phone and a desktop | Out of scope | — | — | — |

---

## What Linux already does better

Worth writing down, because the framing of this project is otherwise entirely
"catching up", and that framing is not accurate.

- **scrcpy beats iPhone Mirroring** on capability: audio forwarding, two-way
  clipboard, virtual displays, gamepad passthrough, and an OTG mode that needs no
  debugging bridge at all. What it lacks is Apple's zero-setup path.
- **No account is required** for any of the LAN-local features. KDE Connect and
  rquickshare pair devices directly; nothing in F1 to F4 needs a Google login.
- **Everything is scriptable.** ANC state, battery, clipboard and transfers all
  end up as command-line calls, which is exactly what a bar widget and a
  keybinding want. Apple's equivalents are locked inside the UI.

## Where this leaves the plan

Reading the tiers rather than the sections:

- **T1 is mostly F1 to F3 and mostly already in the roadmap.** This document adds
  few new T1 rows, which is the expected result — the roadmap was built from the
  tools, and the tools are where T1 lives.
- **T2 is the actual project.** `share-to-phone`, `otp-autofill`, `focus-sync`,
  `buds-multipoint`, `wifi-qr`, `buds-announce`, `phone-battery` and the bar
  widget are all glue nobody has written, all achievable with existing parts, and
  all small enough to finish. F4 is bigger than the roadmap currently makes it
  look.
- **T3 and T4 are honest dead ends until proven otherwise**, and belong in F5 or
  in no phase at all. The value of listing them is that nobody has to rediscover
  the wall.

**Nothing here is promoted into `data/capabilities.toml` yet.** Adding a
capability creates a matrix row that reads `untested` on every device, which is
useful for things somebody intends to test and noise for things that are
aspirational. Promote a row when it enters a phase, not when it enters this
document.

## What a T2 target would have to expose

The tiers above say what kind of work each target is. This says what each **T2**
target would have to put on the wire, so that the layer producing the data and
the layer drawing it can be agreed on before either is written rather than after.

It is not a contract — the contract is `08-status-contract.md`, and it is not
mine. This is the list of what would have to be contracted, derived from what
each tool can actually produce.

The last column is the one that matters. Every row here can fail in a way that
looks like a number, and a widget that draws an invented number is worse than a
widget that draws nothing. The precedent already exists in the status contract:
`buds-battery` carries a `source` field (`avrcp` / `proprietary` / `null`)
precisely so that "one figure because only one exists" cannot be mistaken for
"three were due and two failed".

| Target | Produced by | Would have to expose | Desktop consumes | What "unknown" has to look like |
|---|---|---|---|---|
| `phone-battery` | KDE Connect battery plugin, over D-Bus | Level, charging state, and the age of the reading | A figure on the bar | Phone unreachable is **not** 0 %. Needs an explicit unavailable state with a reason, and a timestamp so a stale figure cannot pass as current |
| `buds-multipoint` | `pbpctrl`, plus the local BlueZ connection state | Which host currently holds the buds, and whether a grab succeeded | A toggle, and the current owner on the bar | "Not connected" and "connected but owned by the phone" are different states and must not collapse into one icon |
| `otp-autofill` | KDE Connect notification stream | The extracted code, the sender, and the confidence that it *is* a code | A notification, and the code on the clipboard | A wrong extraction is worse than none. If the pattern does not match cleanly, expose nothing rather than a guess |
| `focus-sync` | Both ends: Omarchy quiet mode and the phone's DND | Current state each side, and which side changed last | A toggle | The two can disagree. There is no single truth to show, so expose both and say which won |
| `buds-announce` | KDE Connect notifications plus local TTS | Nothing visible; it is an action | A toggle, and a queue depth | Announcing into buds that are not in an ear is the failure. Needs in-ear state, which is `buds-inear` — a T3 that is not solved |
| `wifi-qr` | Local: a QR decoder and NetworkManager | The parsed SSID and security type before joining | A dialog | A QR that parses but whose network does not exist should say so, not spin |
| `share-to-phone` | rquickshare | Transfer state, progress, and a terminal result with a reason | Progress, and success or failure | "No peer" is not "failed". The status contract already separates these — keep them separate all the way up |

Three T2 targets need no contract because they produce no state the desktop shows
— `second-display`, `phone-mic` and `phone-audio-in` are audio and display
routing, and their state already lives in PipeWire and Hyprland.

### The seven rows want three fields, not seven

Read the last column down instead of across and the same three shapes keep
appearing. They are worth adding once, generally, rather than seven times in
seven bespoke forms:

- **`as_of`, a staleness stamp on the value itself.** `phone-battery` needs the
  age of the reading, `focus-sync` needs to know which side changed last, and
  `buds-multipoint`'s idea of who owns the buds goes stale the instant the phone
  takes them. A figure with no timestamp cannot be told apart from the same
  figure an hour later, and the bar will draw both identically.
- **Absent-with-a-reason, as a first-class value.** Four rows need it and each
  needs it for a different reason: unreachable is not 0 %, "no peer" is not
  "failed", "not connected" is not "connected but owned elsewhere", and a
  low-confidence code match must produce nothing rather than a guess. The status
  contract already has exactly this shape — `peers` is never an empty list, it is
  unavailable with a reason. That primitive wants generalising, not copying.
- **Provenance.** `buds-battery` already carries `source`
  (`avrcp` / `proprietary` / `null`). `phone-battery` has the same problem in a
  different coat: which channel produced this number changes what it means. And
  the virtual peer needs to declare itself simulated. That is the same field at
  three sites, and it should be one field.

If those three exist generally, every "what unknown has to look like" cell above
is satisfied by construction rather than by seven people remembering.

## Sources

- [Continuity features and requirements for Apple devices — Apple Support](https://support.apple.com/en-us/108046)
- [macOS Continuity — Apple](https://www.apple.com/macos/continuity/)
- [Use Handoff to continue tasks on your other Apple devices — Apple Support](https://support.apple.com/en-us/102426)
- [Use Adaptive Audio with your AirPods — Apple Support](https://support.apple.com/en-us/104979)
- [Announce Notifications with Siri on AirPods or Beats — Apple Support](https://support.apple.com/en-us/102536)
- [Use Live Listen with AirPods or Beats — Apple Support](https://support.apple.com/en-us/102479)
- [AirPods: How to Automatically Switch Between Devices — MacRumors](https://www.macrumors.com/how-to/airpods-switching-devices/)
- [Meet Pixel Buds Pro 2 — Google blog](https://blog.google/products/pixel/google-pixel-buds-pro-2/)
- [Pixel Buds Pro 2 could finally get Auracast — Android Police](https://www.androidpolice.com/pixel-buds-pro-2-support-bluetooth-auracast/)
- [Implementing Bluetooth LE Audio & Auracast on Linux systems — Collabora](https://www.collabora.com/news-and-blog/blog/2025/11/24/implementing-bluetooth-le-audio-and-auracast-on-linux-systems/)
- [LE Audio support in PipeWire — BlueZ](https://www.bluez.org/le-audio-support-in-pipewire/)
- [scrcpy — README](https://github.com/Genymobile/scrcpy/blob/master/README.md)
- [Use a device as a webcam — Android Open Source Project](https://source.android.com/docs/core/camera/webcam)
- [Android 14 adds support for using smartphones as webcams — Esper](https://www.esper.io/blog/android-14-adds-support-for-using-your-smartphone-as-a-webcam)
- [KDE Connect — KDE Community Wiki](https://community.kde.org/KDEConnect)
- [The Google Fast Pair Service — Google for Developers](https://developers.google.com/nearby/fast-pair/landing-page)
- [Google Fast Pair integration — Nordic nRF Connect SDK docs](https://docs.nordicsemi.com/bundle/ncs-3.0.1/page/nrf/external_comp/bt_fast_pair.html)
- [AirDrop–Quick Share interoperability expanding to more Android phones — MacRumors](https://www.macrumors.com/2026/02/11/airdrop-quick-share-interoperability-more-phones/)
- [Chrome shared clipboard across synced devices — Chrome Unboxed](https://chromeunboxed.com/chromes-new-feature-will-let-you-share-your-clipboard-with-synced-devices/)
- [Find Hub — Wikipedia](https://en.wikipedia.org/wiki/Find_Hub)
- [Bluetooth headset — ArchWiki](https://wiki.archlinux.org/title/Bluetooth_headset)
