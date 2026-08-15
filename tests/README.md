# Tests

```bash
scripts/run-tests.sh                          # everything
scripts/run-tests.sh --watch                  # re-run on every save
scripts/run-tests.sh tests.test_build_matrix  # one module
```

Standard library only. No pytest, nothing to install, no network. Python 3.11+
for `tomllib`; CI pins 3.12 and the reference machine runs 3.14.

## The rules this suite holds itself to

**Nothing here starts a binary that talks to hardware.** Not `rquickshare`, not
`pbpctrl`, not `bluetoothctl` with a verb that changes anything. Measured on the
reference machine on 2026-08-15, 3 attempts out of 3: launching `rquickshare`
takes `bluetoothd` down by SIGSEGV, which drops the Bluetooth mouse for fifteen
seconds — or, when the HID profile fails to reattach, until somebody
disconnects and reconnects it by hand. A suite meant to run continuously must
not be able to do that to the person running it.

`test_hw_report.py` therefore replaces `PATH` entirely with a directory of
stubs. Not shadowing — replacement. A command with no stub is not found rather
than falling through to the real one, and the `bluetoothctl` stub exits 90 on
any verb but `show` and `devices`. Two tests guard the harness itself.

**Nothing here writes to `data/`.** Malformed fixtures go to a temporary
directory with the generator's paths repointed at it. `data/capabilities.toml`
is read, never written: capabilities are promoted by development, and a test
that could add a row would make the matrix meaningless.

**A failing test is a measured finding**, reported to whoever owns the file
with the exact command to reproduce it. The suite does not fix other people's
code.

**`LC_ALL=C` everywhere.** A decimal comma has already cost this project a
wrong percentile calculation.

## What is covered

| File | What it holds |
|---|---|
| `test_build_matrix.py` | Validation of capabilities and reports, `summarise()`, rendering, `--check`, exit codes |
| `test_network_schema.py` | The `[network]` table, written before its validation exists |
| `test_hw_report.py` | The script's interface, the privacy contract, and static rules over every `scripts/*.sh` |
| `test_repo_invariants.py` | Matrix freshness, id hygiene, MAC and host IP in reports, markdown links and anchors, dated provenance |
| `test_docs_features.py` | `docs/features.md`: the bold/backtick contract, closed vocabularies, id collisions |
| `test_docs_design.py` | `docs/06-design.md`: every surface's assumed capability exists, `required` is only claimed once measured |

## `expectedFailure` is deliberate here

Some tests describe an invariant the repository does not satisfy yet. They are
marked `expectedFailure`, which keeps the suite green while recording the gap
in code rather than in a comment nobody reads.

**When the gap is closed, unittest reports an unexpected success and the run
fails.** That is the point: the failure says "this works now, delete the
decorator". Do not silence it by deleting the test.

Currently marked:

- `test_network_schema.py` — the whole `[network]` schema. Agreed with
  development on 2026-08-15: the negative cases are written here first, the
  validation lands in `build-matrix.py` against them.
- `test_docs_features.py::test_every_promoted_id_is_reachable_from_the_catalogue`
  — `hotkeys` and `menu-entry` are promoted capabilities with no row in
  `docs/features.md`. Reported; whether the rule holds at all is research's
  call, since it is their document.

## Ownership

`tests/` and `scripts/run-tests.sh` belong to QA. Everything they read belongs
to somebody else: `data/` and `scripts/` to development, `docs/features.md` and
`docs/01-landscape.md` to research, `docs/06-design.md` to design. A test that
needs one of those to change is a message to its owner, not an edit.
