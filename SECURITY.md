# Security

## What the risk actually is here

This repository ships no service and no daemon. It ships **shell scripts that
people run on their own machines**, and it collects **reports describing those
machines**. Those are the two things worth protecting.

**Scripts you are told to run.** `scripts/hw-report.sh` is meant to be run by
anyone considering a hardware report, with their own user privileges. A pull
request that quietly adds a line to it reaches every one of those people. So:

- Scripts must never install packages, write outside the repository, or contact
  the network. They read local state and print. CI enforces the package-manager
  half of that; the rest is enforced by review.
- `scripts/build-matrix.py` uses the standard library only. A pull request that
  adds a dependency is a pull request that adds a supply chain, and will be
  treated as one.
- GitHub Actions are pinned to commit SHAs rather than tags, because a tag can
  be repointed by whoever controls the action. The workflow runs with
  `contents: read` and does not persist credentials.

**Reports that describe your machine.** A device report is written by a
contributor and rendered into a published document. `hw-report.sh --markdown`
and `--toml` therefore redact MAC addresses and host IP addresses, and print
bare subnets instead — the subnet is the fact that matters for Quick Share, and
the rest identifies you. CI rejects a report under `data/devices/` containing a
MAC address in colon or dash form, or a host IPv4 or IPv6 address. It does not
catch a MAC written without separators or in Cisco form (`aabb.ccdd.eeff`):
twelve hex digits match too much ordinary text to reject on sight, so that
limit is deliberate rather than an oversight. The check is a floor, not a
guarantee — read your own report before you send it.

**A device name cannot reach a report through the tool, and you can check that
rather than believe it.** A Bluetooth device is often named after whoever owns
it, which makes it the obvious thing to worry about. But `hw-report.sh` never
reads one: its only look at paired devices is `bluetoothctl devices Paired |
grep -icE 'pixel|google'`, and `-c` counts matches instead of printing them.
The report schema has nowhere to put one either — `vendor` and `model` are
catalogue values like "Google" and "Pixel 9 Pro", not the name a device
announces. That is a property of one line you can read, not a promise you have
to take on trust.

The exception is `notes`, which is prose you write yourself. Nothing filters
it, deliberately: catching people's names would need per-language lists and
possessive patterns, and a check that rejects honest reports costs more than
the case it catches. So it is asked for at the point of writing instead — no
device names, no people's names.

If you write a report by hand, do the same. If you spot published data that
identifies somebody, say so and it will be removed.

## Reporting something

For anything sensitive, use **private vulnerability reporting** on this
repository: the Security tab, "Report a vulnerability". It stays private until
it is resolved.

For anything not sensitive — a script that misbehaves, a check that does not
catch what it claims to — open a normal issue.

Please do not use the issue tracker to report a vulnerability in **rquickshare,
pbpctrl or KDE Connect**. Those are separate projects with their own security
contacts; this repository integrates them and cannot fix them. Links are in
`.github/ISSUE_TEMPLATE/config.yml`.

## What this project will not do

It will not ask you to pipe a script from the internet into a shell, and it will
not install anything on your behalf. Every tool that needs installing is named
with the exact command, for you to run yourself, having read it. If you ever see
this repository do otherwise, that is the bug.
