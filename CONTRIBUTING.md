# Contributing

The most valuable thing you can contribute to this project is **a measurement on
hardware nobody here owns**.

The maintainer has one Pixel and, soon, one pair of Pixel Buds Pro 2. Everything
this project claims about a Pixel 9, about first generation Buds Pro, about
Buds A-Series, about a different Bluetooth adapter or a different compositor is
guesswork until somebody with that hardware runs it and says what happened.

Code is welcome too. But a five-line report from a device we cannot buy is worth
more than a refactor.

## Before anything else

Read [docs/conventions.md](docs/conventions.md). It is short, and it is the one
thing this project is strict about: **measured and derived claims never get
blurred together**, and a capability you did not test is left out rather than
guessed at.

## Reporting hardware

1. Get the repository and run the report generator. It installs nothing:

   ```bash
   git clone https://github.com/haripako/omapixel.git
   cd omapixel
   scripts/hw-report.sh --markdown
   ```

   The generator is a `bash` script and calls no interpreter of its own.

   It redacts MAC addresses written in the usual forms — `aa:bb:cc:dd:ee:ff` and
   `aa-bb-cc-dd-ee-ff` — along with host IPv4 and IPv6 addresses, and prints
   bare subnets instead. It does **not** catch a MAC written without separators
   or in Cisco form (`aabb.ccdd.eeff`): twelve hex digits match too much
   ordinary text to key on. Read the block before you paste it — that is the
   check that catches what a filter cannot.

2. Open a **Hardware report** issue and paste the block in.

That is enough. A maintainer will turn it into a device file. If you would rather
do that yourself, open a pull request instead:

1. Copy `data/report-template.toml` to
   `data/devices/<vendor>-<model>-<your-handle>.toml`, lowercase and hyphenated.
2. Fill it in. `scripts/hw-report.sh --toml` prints the `[host]` section ready to
   paste.
3. Regenerate the matrix and commit both files:

   ```bash
   scripts/build-matrix.py
   ```

## Report format

`schema = 1` at the top. Then:

| Table | Field | Required | Meaning |
|---|---|---|---|
| `[reporter]` | `handle` | yes | Your GitHub handle, so a claim has a name on it |
| `[reporter]` | `date` | yes | ISO 8601 date you took the measurements |
| `[device]` | `kind` | yes | `phone` or `earbuds` |
| `[device]` | `vendor` | yes | e.g. `Google` |
| `[device]` | `model` | yes | e.g. `Pixel 9 Pro` |
| `[device]` | `os` | no | Android version, or buds firmware if known |
| `[host]` | any | no | Free-form key/value. Use `hw-report.sh --toml` |
| `[network]` | any | no | Phones only: subnet, reachability, RTT. Subnets only, never host addresses |
| `[[result]]` | `id` | yes | Must exist in `data/capabilities.toml` |
| `[[result]]` | `status` | yes | `works`, `partial`, `broken` or `blocked` |
| `[[result]]` | `method` | yes | `measured` or `derived` |
| `[[result]]` | `tool` | no | Exact version you ran, e.g. `pbpctrl 0.1.8` |
| `[[result]]` | `notes` | no | The caveat. Often the most useful field |

Omit `[[result]]` entirely for anything you did not test.

`scripts/build-matrix.py --check` validates all of this and runs in CI, so a
malformed report fails the pull request with a message naming the file and the
field rather than being silently ignored.

## Adding a capability

New rows in the matrix go in `data/capabilities.toml`. Adding one that nobody has
tested is fine — it shows up as untested everywhere, which is useful.

Never rename an existing `id`. Ids are the join key between the registry and
every report that references them; renaming one silently orphans results.

## Code

- Shell scripts must not install anything. They print the exact command and stop.
  Package installation is the user's decision, on their machine, with their
  package manager.
- `scripts/build-matrix.py` depends on the standard library only. Keep it that
  way: a contributor should be able to validate a report on a bare Python.
- `docs/02-capability-matrix.md` is generated. Edit the data and rerun the
  generator; do not hand-edit the file.

## Language

Documentation, issues and commit messages are in English, so that people with
hardware we do not have can take part. The README carries a Spanish section, and
issues in Spanish are welcome — nobody should be locked out of reporting a
device over language.

## Licence

By contributing you agree that your contribution is licensed under GPL-3.0, the
same as the rest of the project.
