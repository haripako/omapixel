# The status contract

The stable interface between the tools underneath and everything we draw. Block
B2 in the [plan](07-plan.md), and the hinge the rest of it turns on.

```bash
scripts/omapixel-status          # human-readable
scripts/omapixel-status --json   # the contract
```

Nothing we build ever reads `pbpctrl`, `rquickshare` or `kdeconnect-cli` output
directly. It reads this.

## Why this exists at all

Three problems that look separate and are not.

**Upstream is mortal.** `pbpctrl` had gone 482 days without an update when this
project started, and it targets first-generation Buds Pro. When it dies, or when
it turns out not to speak to Buds Pro 2, replacing it must cost one file and not
a rewrite of everything that displays a battery.

**Design cannot wait for measurement.** Design cannot build against output that
may never exist. It can build against a contract today, which is why the shape
below is defined before the data behind it is real.

**Degradation has to be designed, not discovered.** Over standard AVRCP there is
one combined battery figure and nothing for the case. Three figures need the
proprietary protocol. If the contract cannot *say* "one figure, combined", every
consumer invents its own way of showing a hole, and they all disagree.

## The rules the contract guarantees

These are promises to consumers, and the reason they can be written simply.

0. **Why something is missing is structural, not prose.** "No battery showing"
   has three completely different fixes — install a package, start a daemon,
   pair a device — and a consumer must not parse English to tell them apart.
   `status` is for code, `reason` is for humans. Both are always present.
1. **Every capability key is always present.** Never omitted, whatever the state
   of the machine. A consumer never writes `if "buds" in data`.
2. **Valid JSON even when nothing works.** A machine with no tools installed, no
   devices paired and no network still gets a complete, parseable answer saying
   so. **This is the case that matters, and the one nobody tests.**
3. **The body is always parseable; the exit code says whether the command
   itself broke.** `0` means it ran, including when every capability is
   unavailable — that is a successful answer, not a failure. Non-zero means the
   command broke, and even then the body is valid JSON carrying an `error` key,
   so a consumer parses first and checks status second. `2` means bad
   arguments; an unknown flag is refused rather than ignored.

   ```json
   {"schema": 1, "generated": "...", "host": {}, "capabilities": {},
    "error": "OSError: ..."}
   ```
4. **`available: false` always comes with a human `reason`.** Never a bare
   false. Every silent failure found during bring-up became a support question;
   the reason string is where that stops.
5. **`provider` names who answered.** So swapping `pbpctrl` for `budslink` is
   visible in the data, and a report can say which tool produced a number.
6. **No host-identifying data.** Subnets, never host addresses. No MAC
   addresses. Same rule as device reports, for the same reason: this output ends
   up pasted into issues.
7. **`as_of` is on every capability, not on the document.** A consumer caches
   one answer at a time, so the stamp has to be at the granularity it caches at.
   It is the moment that capability was probed, never the moment the JSON was
   rendered. Implemented 2026-08-16; the third primitive below is now real
   rather than agreed.
8. **The whole call answers fast enough to poll — measured, not enforced.**
   Stated as a measurement with a date, because that is what it is: nothing in
   the code fails if a future probe reintroduces a fixed wait. Tests owns the
   ceiling that would make it enforceable, and until that exists this is a fact
   about 2026-08-16 rather than a promise about tomorrow. A bar widget refreshing once
   a second cannot hold a process open for two of them, so latency is part of
   the contract and not an implementation detail. Measured on the reference
   machine on 2026-08-16: **84 ms**, down from 2090 ms. The 2008 ms were one
   command — `kdeconnect-cli --list-devices` runs a fixed two-second discovery
   cycle before answering. The same question over D-Bus answers in 2 ms, so
   KDE Connect is asked over `busctl`, not through its CLI. Caching was the
   alternative and it was rejected: it hides the wait instead of removing it,
   and then needs the stamp above to stay honest about what it hid.

## Three primitives, not a pile of fields

Arrived at independently by research, QA and the desktop layer within the same
evening, which is the sign it is real. Every field this contract will ever grow
is one of three shapes. Decide it now, while it is cheap: retrofitting
provenance onto six consumers later is not.

**1. Ausente-con-motivo — absent with a reason.** Never `[]`, never `null`,
never a bare `false`. `{"kind": "unavailable", "reason": "..."}`. Unreachable is
not 0 %, "no peer" is not "failed", "not connected" is not "connected but the
phone has them", and a low-confidence guess must produce nothing rather than a
guess. Already used by `peers` and by battery; it is a type, not a habit.

**2. Value with provenance.** `source` on the battery figure was the first
instance and it was reasoned, not lucky. The simulated-peer mark and the *side*
a transfer failed on are **the same requirement seen again**, not three separate
cases. Each time, two situations look identical from outside and only the data
can separate them:

| Looks the same | Actually is |
|---|---|
| One battery figure | AVRCP giving its complete answer, or two of three readings failing |
| A peer in the list | A real Pixel, or our emulator |
| A failed transfer | Our end gave up, or theirs refused |

**The first one landed on 2026-08-16: `origin` on a device report**, top-level,
required, one of `device` | `emulator` | `unknown`. Not a boolean — `simulated
= true` cannot say "I do not know", because its absence collapses to false,
which reads as "real". Required rather than defaulted for the same reason: if
absent meant `device`, the guarantee would be that every contributor remembers
to declare a simulated run, and that is not a guarantee. In the matrix,
`measured` only counts as a measurement on hardware when the report says it ran
on hardware; anything else is rendered `(emulator)` or `(origin unknown)`. The
emulator will be the cheapest thing in this project to run and the only one
always available while the hardware is missing, so the erosion will not come
from bad faith — it will come from it being easy, and an unqualified cell is
the whole way it erodes.

**A value without provenance is not drawn as fact.** A missing provenance field
means unknown, and unknown never renders as real — that direction matters,
because an old emulator build or a truncated payload must degrade into "unsure",
not into "a measured Pixel". That is the screenshot that ends up in an issue.

**3. Value with an expiry.** `as_of` on the reading itself. A figure with no
timestamp is indistinguishable from the same figure an hour later, and a bar
will draw them identically. Phone battery needs the age of the reading, focus
sync needs to know which side changed last, and who owns the earbuds stops
being true the moment the phone takes them.

**4. An available action.** Added 2026-08-17, requested by the desktop layer
before either side wrote it, and for the reason the other three exist: at least
three are coming — retry the link, cycle ANC, send a file — and if each arrives
as its own field we get `can_retry`, `anc_settable`, `send_available`, and the
fourth case gets argued from scratch. That is the same mistake provenance
already taught us three times.

```json
"actions": [
  {"id": "retry-link", "label": "Reconnect", "available": true},
  {"id": "cycle-anc",  "label": "Cycle ANC", "available": false,
   "reason": "pbpctrl is not installed"}
]
```

- `id` is a closed vocabulary, so a consumer can special-case an icon without
  parsing English.
- `label` is what to show. The consumer never composes this itself.
- `available` says whether it can be done *now*; when false, `reason` says why,
  same rule as everywhere else.
- **An absent `actions` means there is nothing to do**, never "there is
  something and we are not telling you".

The point is that a widget draws a button when there is something to do and
draws nothing when there is not, **without ever knowing which tool is
underneath** — and ANC arrives the day the hardware does, with no change to any
QML.

**Consumers do not perform actions themselves.** Doing so means touching the
device, and that lives on this side of the contract. An action is requested
through the mechanism this contract exposes; a consumer that reaches for D-Bus
directly has reintroduced exactly the coupling the whole file exists to remove.

The first one is real rather than hypothetical. `phone-link` can drop to
`isReachable=false` while still paired, with the phone answering pings — the IP
path fine and KDE Connect simply not reconnecting, which a user sees as
"disconnected" over a working network with no explanation. `forceOnNetworkChange`
restores it in under twelve seconds, measured 2026-08-17. Nobody finds that on
their own, and it is exactly the glue this project says it exists to write.

Get these four right and every future "this must look unknown" is satisfied by
construction, rather than by seven people remembering.

### Rejected is not failed

A related distinction the failure states have to carry, and the reason it is
here rather than in the design rules: **rejected is a decision, not a fault.**
The other end said no. It must not be painted as an error. `failed` must name
the side it failed on, `timeout` must say how long was waited — that is what
replaces an indefinite spinner — and "no peer" means discovery found nothing,
not that nothing exists.

Failure states are **states of `file-send` and `file-receive`**, not
capabilities. They never become rows in `data/capabilities.toml`; doing so would
invent ids that no hardware report can ever join against.

## Shape

```json
{
  "schema": 1,
  "generated": "2026-08-15T21:30:00Z",
  "host": {
    "distro": "Omarchy 4.0.0.alpha",
    "desktop": "Hyprland 0.56.2",
    "subnet": "192.168.10.0/24"
  },
  "capabilities": {
    "file-transfer": {
      "available": false,
      "status": "no_answer",
      "reason": "rquickshare is installed but not running",
      "provider": "r-quick-share 0.11.5-5",
      "as_of": "2026-08-16T00:06:25Z",
      "state": {
        "running": false,
        "peers": {"kind": "unavailable", "reason": "rquickshare is not running"}
      }
    },
    "phone-link": {
      "available": false,
      "status": "nothing_present",
      "reason": "no device is paired with KDE Connect",
      "provider": "kdeconnect 26.04.3-1",
      "as_of": "2026-08-16T00:06:25Z",
      "state": {"devices": [], "reachable": []}
    },
    "buds": {
      "available": false,
      "status": "not_installed",
      "reason": "pbpctrl is not installed",
      "provider": null,
      "as_of": "2026-08-16T00:06:25Z",
      "state": {
        "battery": {"kind": "unavailable", "reason": "pbpctrl is not installed", "source": null},
        "anc": {"kind": "unavailable", "reason": "pbpctrl is not installed"}
      }
    }
  }
}
```

That example is not invented: it is the literal state of the reference machine
on 2026-08-15, and the three capabilities land on three *different* statuses,
which is the point.

### `status`

| Value | Means | The user's fix |
|---|---|---|
| `ready` | Working. `available` is true | — |
| `not_installed` | The tool is not on this machine | Install a package |
| `no_answer` | Installed, but it did not respond | Start a daemon |
| `nothing_present` | It answered, and there is no device | Pair something |
| `not_probed` | Deliberately not asked. `reason` says why | Depends |
| `blocked` | Installed and startable, and starting it damages this machine | **Wait.** `state.unblocked_by` says for what |
| `unreachable` | A device is paired and known, and is not answering now | Wake the phone, or use the `retry-link` action |

`unreachable` was added on 2026-08-17 because the contract was contradicting
itself, and the field that was wrong was the authoritative one. A paired phone
that had dropped reported `nothing_present` — documented as "it answered and
there is no device" — while `reason`, `state.devices` and `actions` all
correctly said there was one. Three of four fields agreed and `status`
disagreed.

That is worse than a mislabel. This document's own rule is **switch on `status`,
never on the prose**, so a consumer doing exactly as instructed would tell the
user to pair a phone that is already paired, while the correct `reason` went by
unread. The field nobody is allowed to trust was right and the field everybody
must trust was wrong.

It is also the same distinction separated two days earlier arriving through
another door: paired-but-out-of-range collapsing into nothing-paired. That was
fixed in `state` by adding `reachable`, and it came back in `status`. Reusing an
existing value would have hidden it a third time — `no_answer` is about the
daemon, and here the daemon answered.

**The general rule it earns:** if `state` is needed to work out what `status`
means, `status` means nothing. Any future disagreement between them is a defect
in `status`, not a hint that consumers should read `state`.

`available` is exactly `status == "ready"` and exists only so simple consumers
can ignore the rest.

`blocked` was added on 2026-08-16 because the vocabulary made the bar give
actively harmful advice, and it did so correctly. `file-transfer` was reporting
`no_answer`, a consumer switching on `status` — as this contract instructs —
read that as "start it", and on BlueZ 5.87 starting `rquickshare` crashes
`bluetoothd` and takes the user's Bluetooth mouse with it. "Installed and
stopped" and "installed, startable, and starting it breaks this machine" are
two situations with opposite advice, and they were collapsing into one state.
Raised by the desktop layer, which had the harmful string on screen in its own
code and correctly refused to special-case `rquickshare` in the widget: a
consumer must not know which tools are underneath, which is what this contract
is for.

It carries two extra fields in `state`, because "wait" is useless without
saying for what:

| Field | Meaning |
|---|---|
| `blocked_by` | What is known, phrased as knowledge — not a cause that was not checked |
| `unblocked_by` | What would clear it. `"bluez 5.88, and a bluetoothd restarted into it"` |

Two rules learned putting it in, both instances of *a name is not the thing*:

- **Gate on the version, never on the tool.** "rquickshare is dangerous" is
  false on 5.88 and this file would have repeated it forever.
- **The package is not the daemon.** The version on disk says what will run
  next time, not what is running now. When 5.88 ships and nobody restarts
  `bluetoothd`, the live process is still the one that crashes while a naive
  check reports safe — so the check also compares the daemon's start time
  against the binary's mtime, and an upgraded-but-not-restarted machine stays
  `blocked`. Raised by QA.

And when the version cannot be read at all, it blocks — unknown is not grounds
to advise an action that breaks a machine — but `blocked_by` then says exactly
that and does not assert a defect in a version nobody read.

`not_probed` earns its place from a measured hazard: on the reference machine a
tool bringing up a BLE listener segfaults `bluetoothd` and takes the user's
Bluetooth mouse with it. **A status command must never be the thing that crashes
somebody's desktop**, so it does not talk to the earbuds unless asked with
`--probe-bluetooth`, and it says so rather than pretending nothing is there.

### Battery, the part that carries the whole argument

`battery.kind` is the discriminator, and **`combined` is a first-class answer,
not a degraded one**:

| `kind` | Fields | When |
|---|---|---|
| `per_bud` | `left`, `right`, `case` (any may be `null`) | The proprietary protocol answered |
| `combined` | `combined` | Standard AVRCP. One figure for both buds, nothing for the case |
| `unavailable` | `reason` | Nothing paired, or no tool can talk to it |

Every one of them also carries **`source`**: `avrcp`, `proprietary`, or `null`.

That field is not decoration. Without it, "there is only one figure because
AVRCP only gives one" and "there were meant to be three and two failed" look
identical from outside, so a consumer shown a single number cannot tell whether
to draw one battery confidently or three with two holes. `source: "avrcp"` means
one figure is the *correct and complete* answer; `source: "proprietary"` with a
missing `right` means something went wrong. Same for a `case` of `null`, which
means unknown rather than empty — the case has no radio and only reports whether
an earbud is inside.

A consumer switches on `kind`. It never infers "no data" from a missing field,
and it never has to render three empty slots because only one number exists.

The case reports only whether an earbud is inside it, because it has no radio of
its own. `case: null` therefore means "unknown", not "empty".

### ANC

| `kind` | Fields |
|---|---|
| `known` | `mode` — one of `off`, `anc`, `transparency` |
| `unavailable` | `reason` |

### `peers`, and the port that is not there

`peers` is never a bare `[]`. An empty list reads as "we looked and nobody is
around", and next to `status: ready` that is exactly the wrong thing for a UI to
believe. Until peer discovery exists it carries the same `unavailable` shape as
everything else, with a reason. Same argument as the battery: empty and unknown
must not look alike.

**When it does exist, every entry carries its own `origin`** — `device`,
`emulator` or `unknown`, the same closed vocabulary and the same rule as on a
device report, with absent reading as `unknown` and never as `device`.

Per entry, not per capability, and that distinction is the whole point. An
`origin` on `file-transfer` as a whole would say the capability came from the
emulator; it could not say *which of the three peers* is the emulator, and the
list is going to mix a real Pixel with our virtual one in the same view. The
consequence is not hypothetical: somebody will paste a screenshot of a working
transfer into an issue, and if the simulated peer draws the same as a Pixel,
that image becomes evidence of something nobody measured.

```json
"peers": [
  {"name": "Pixel 7 Pro",              "origin": "device"},
  {"name": "Virtual Pixel (simulated)", "origin": "emulator"}
]
```

Requested by the desktop layer on 2026-08-16, agreed before either side is
written, which is the rule this contract exists to enforce. Nothing implements
it yet — `peers` is still `unavailable` — so it costs nothing now and would
cost a retrofit across every consumer later.

### An active transfer, and how one ends

Also agreed in advance, also unimplemented. A transfer in flight is a value
with provenance, and a finished one is a value that has to name **which side**
decided:

| Field | Meaning |
|---|---|
| `direction` | `send` or `receive` |
| `peer` | the display name, plus its `origin` as above |
| `bytes`, `total` | `total` may be `unavailable` with a reason — a sender that never declared a size is not a zero-byte file |
| `outcome` | `completed`, `rejected`, `failed`, `timeout` — absent while in flight |
| `side` | on `rejected`, `failed` and `timeout`: `local` or `remote` |

**`rejected` is not `failed`.** The other end said no, which is a decision and
must not be painted as an error. `timeout` says how long was waited, because
that is what replaces an indefinite spinner. And `side` exists because "the
transfer failed" is the sentence a user cannot act on: their end giving up and
the phone refusing have different fixes.

### The earbuds fields, and why they are specified before the hardware exists

`anc.modes` — the modes this particular model supports, so a UI offers what
exists rather than a fixed three — and `charging`, are specified now and will
read `unavailable` with a reason until Pixel Buds Pro 2 arrive and `pbpctrl`
is measured against them. Writing them down early is not optimism: it is so
that a design drawn against this contract degrades to "unknown" instead of
inventing a control that may never have anything behind it. Same reason
`battery.source` exists.

**The transfer port is deliberately absent**, and will stay absent.
`rquickshare` picks a different TCP port on every launch — measured as 35475,
then 34261 after a restart. It is not a stable fact about the machine, a
consumer must never cache it, and a firewall rule cannot be written against it.
That last consequence is a B0 problem, not something the contract can paper
over.

### `provider`

A string naming what answered, or `null`. It usually carries a version, but
**it may be a bare tool name**: the version comes from the host's package
manager, and a report from a distro without `pacman` will have the name only.
Consumers must not parse it for a version.

## Adding a capability

A new key here is a promise to keep it forever, so it enters when it enters a
block in the plan — the same rule that governs
[`data/capabilities.toml`](../data/capabilities.toml). A capability appearing in
[features](features.md) does not qualify.

Never rename a key or a `kind` value. Consumers switch on them.

## Status

**The contract is defined. The implementation reports honestly and measures
almost nothing yet**, which is the accurate state of the project: as of
2026-08-15 no capability has been measured working. As B1 produces real
measurements, the providers get filled in behind this shape without any
consumer changing.
