# Conventions

This project is mostly an exercise in not fooling ourselves. The tooling around
Pixel-on-Linux is young, half-documented and frequently abandoned, and almost
every claim you will read online is somebody repeating a README rather than
somebody reporting what happened on their machine.

So there is one rule that outranks the rest.

## Measured or derived. Never blurred.

Every claim in this repository is tagged as one of two things.

**Measured** — you ran it, on your hardware, and watched what happened. You can
say which version of the tool, on which device, on which day. If somebody asks
"how do you know", the answer is "I did it".

**Derived** — it comes from a README, a release note, an AUR page, a forum
thread, a news article, or a model's guess. It might well be true. It has not
been verified here.

Derived claims are useful: they tell us where to look. They are not evidence.
They never graduate to measured by being repeated, being plausible, or being
believed by everyone. They graduate by somebody running the thing.

Practically:

- `docs/01-landscape.md` is derived in its entirety, and says so at the top with
  the date it was gathered. Treat it as a research lead, not a status report.
- Device reports in `data/devices/` carry a `method` field per result. Use
  `measured` only for things you personally ran.
- The generated matrix marks a capability `(derived)` when no measured report
  backs it, so a row that looks confident but is not gets flagged.

## Absent means untested

If you did not test a capability, leave it out of your report. Do not guess it
works because it works for somebody else, and do not mark it broken because you
did not get round to it.

`untested` is the honest and most common state of a young project. A matrix full
of `untested` is more useful than a matrix full of optimism, because it tells the
next person exactly where the unexplored ground is.

## Statuses

| Status | Means |
|---|---|
| `works` | Did what it should, repeatably. Say how many times you tried |
| `partial` | Works with a caveat that matters. The caveat goes in `notes` |
| `broken` | You ran it and it failed. Say how it failed |
| `blocked` | No known path today, for reasons outside the tooling |

`partial` is the most informative status in this project and the one to reach
for when in doubt. "Works but only with the phone screen on" is `partial`, and
that caveat is worth more than the status.

## Name the version, not the release

`pbpctrl 0.1.8`, not `latest`. Tools here move fast or not at all, and a report
without a version cannot be reproduced or aged out. Same for the Android
version: it is a better predictor of Quick Share behaviour than the phone model.

## Do not announce a cause you have not reproduced

Plausible explanations are cheap and this hardware punishes them. The reference
machine has a MediaTek MT7922 adapter with a history of unexplained Bluetooth
disconnections that leave nothing in the logs. If something misbehaves, say what
you observed and what you have not yet ruled out. "The adapter drops the buds
after ~20 minutes, cause unknown, not reproduced with a second adapter" is a
good report. "It's a BlueZ bug" without a bisect is not.

## Privacy in public reports

`scripts/hw-report.sh --markdown` redacts MAC addresses and host IP addresses
and prints bare subnets instead. That is deliberate: subnet is the fact that
matters for Quick Share, and the rest identifies your machine. If you write a
report by hand, do the same.
