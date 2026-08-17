"""Shared helpers for the test suite. No test cases live here.

Three jobs:

  * import scripts/build-matrix.py, whose filename is not a valid module name,
    and point its module-level paths at a throwaway directory
  * parse the markdown tables the docs use as data
  * hold the patterns for the privacy invariant in one place, so the detector
    the tests trust is the same one they prove works
"""

from __future__ import annotations

import contextlib
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DOCS = ROOT / "docs"
DATA = ROOT / "data"

# --- the generator under test ------------------------------------------------


def load_build_matrix():
    """Import scripts/build-matrix.py as a module.

    The hyphen makes it unimportable by name, and it has no package, so it is
    loaded from its path. Cached on the function to keep repeated imports cheap
    and to keep `ReportError` a single class across the suite: two separate
    imports would produce two unrelated exception types and `assertRaises`
    would quietly stop matching.
    """
    cached = getattr(load_build_matrix, "_module", None)
    if cached is not None:
        return cached

    path = SCRIPTS / "build-matrix.py"
    spec = importlib.util.spec_from_file_location("build_matrix", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_matrix"] = module

    # Importing writes scripts/__pycache__ otherwise, which litters a directory
    # that belongs to development and shows up in everyone's `git status`.
    previously = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previously
    load_build_matrix._module = module
    return module


@contextlib.contextmanager
def temp_data(capabilities: str, devices: dict[str, str] | None = None):
    """Run the generator against throwaway data.

    Yields (module, workdir). The module's CAPABILITIES, DEVICES and OUTPUT are
    repointed for the duration and restored afterwards, so a test can feed it
    malformed TOML without writing a single byte into data/, which belongs to
    development and is the join key for every hardware report.
    """
    module = load_build_matrix()
    saved = (module.CAPABILITIES, module.DEVICES, module.OUTPUT, module.ROOT)

    with tempfile.TemporaryDirectory(prefix="omapixel-test-") as tmp:
        work = Path(tmp)
        (work / "data" / "devices").mkdir(parents=True)
        (work / "docs").mkdir()

        caps_path = work / "data" / "capabilities.toml"
        caps_path.write_text(capabilities)
        for name, text in (devices or {}).items():
            (work / "data" / "devices" / name).write_text(text)

        module.ROOT = work
        module.CAPABILITIES = caps_path
        module.DEVICES = work / "data" / "devices"
        module.OUTPUT = work / "docs" / "02-capability-matrix.md"
        try:
            yield module, work
        finally:
            module.CAPABILITIES, module.DEVICES = saved[0], saved[1]
            module.OUTPUT, module.ROOT = saved[2], saved[3]


# The last line of every report. A truncated TOML file is still valid TOML —
# the structure is flat, so cutting it does not break the parse — and it loads
# with fewer [[result]] blocks than its author measured. Those rows then read
# `untested`, which the matrix defines as "nobody has tried it on that
# hardware": a claim fabricated against somebody who did try it and took the
# trouble to send it in. The marker is what makes the truncation visible.
END_MARKER_LINE = "# *— end of report —*"


# A capability file that is valid and boring, for tests about something else.
MINIMAL_CAPABILITIES = """
schema = 1

[[capability]]
id = "file-send"
name = "Send files to the phone"
apple = "AirDrop"
phase = "F1"
tool = "rquickshare"
"""


def device_report(results: str = "", *, kind: str = "phone",
                  origin: str = "device") -> str:
    """A valid device report, plus whatever [[result]] blocks a test needs.

    `origin` is mandatory in the schema since 2026-08-16 — a report must say
    whether it came from hardware, from the emulator, or from something that
    could not be determined. Fixtures declare "device" so that tests about
    something else are not silently testing the origin rule.
    """
    return f"""
schema = 1
origin = "{origin}"

[reporter]
handle = "tester"
date = "2026-08-15"

[device]
kind = "{kind}"
vendor = "Google"
model = "Pixel 7 Pro"
os = "Android 17"
{results}
{END_MARKER_LINE}
"""


# --- privacy invariant -------------------------------------------------------
#
# A device report is written by a stranger and rendered into a published
# document. These two things must never survive into one. The patterns live
# here rather than in the workflow YAML so that they can be run locally and,
# more importantly, so the tests can prove the detector catches a report that
# really does leak.

# Both separators the world writes MACs with. Colons are what BlueZ prints;
# hyphens are the IEEE's canonical form and what Windows shows in its Bluetooth
# panel, which is where a contributor is most likely to copy from.
MAC_RE = re.compile(
    r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b|\b[0-9a-f]{2}(?:-[0-9a-f]{2}){5}\b",
    re.IGNORECASE,
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")
# Candidates only. Anything that looks vaguely like IPv6 is handed to the
# `ipaddress` module to decide, so a timestamp like 23:15:49 is rejected by the
# parser rather than by a regex nobody can read.
IPV6_CANDIDATE_RE = re.compile(r"\b[0-9a-f]{0,4}(?::{1,2}[0-9a-f]{0,4}){2,7}(?:/\d{1,3})?")

# An IPv4 network this small is a machine, whatever the prefix claims.
MIN_IPV4_PREFIX = 30
# An IPv6 prefix longer than a subnet identifies an interface.
MIN_IPV6_PREFIX = 64


def _is_publishable_network(token: str) -> bool:
    """True for a bare subnet, false for anything that identifies a machine.

    Decided by the `ipaddress` module rather than by shape. "Ends in .0 and has
    a prefix" is a syntactic proxy for a semantic property, and it blesses
    192.168.10.0/32 — which is exactly one machine.
    """
    import ipaddress

    if "/" not in token:
        return False
    try:
        network = ipaddress.ip_network(token, strict=False)
        address = ipaddress.ip_address(token.split("/")[0])
    except ValueError:
        return False

    if network.network_address != address:
        return False  # host bits set: an address wearing a subnet's clothes
    limit = MIN_IPV4_PREFIX if network.version == 4 else MIN_IPV6_PREFIX
    return network.prefixlen <= limit


# Ranges the standards reserve for documentation. They cannot identify anyone,
# by design, which is exactly why a document should use them — and why flagging
# them would push authors back towards pasting real addresses.
DOCUMENTATION_NETWORKS = (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",  # RFC 5737
    "2001:db8::/32",                                       # RFC 3849
)


def _is_documentation_address(token: str) -> bool:
    import ipaddress

    try:
        address = ipaddress.ip_address(token.split("/")[0])
    except ValueError:
        return False
    return any(
        address in ipaddress.ip_network(net)
        for net in DOCUMENTATION_NETWORKS
        if ipaddress.ip_network(net).version == address.version
    )


def _is_loopback(token: str) -> bool:
    """127.0.0.1 and ::1 identify nobody.

    A known false positive, exempted rather than suppressed: loopback appears
    in every example of connecting to a local service, and flagging it would
    train people to ignore this check.
    """
    import ipaddress

    try:
        return ipaddress.ip_address(token.split("/")[0]).is_loopback
    except ValueError:
        return False


def privacy_violations(text: str) -> list[str]:
    """Every MAC address and host IP in `text`, as human-readable findings.

    A bare subnet is allowed and is the whole point of the field: 192.168.10.0/24
    says what Quick Share needs to know without identifying the machine. Carrying
    a prefix is not enough — [ip redacted]/24 is a host address wearing a
    subnet's clothes, and the CI grep this replaces let that through.

    Enforcing docs/conventions.md, "Privacy in public reports". A report is
    written by a stranger, merged into a public repository and kept in its git
    history forever, so a leak cannot be unpublished. Two consequences that
    outlive whoever reads this next:

      * **This never softens into a warning.** A rejected report is a fixable
        mistake; a merged one is not.
      * **Never "fix" a leak by normalising it.** Rewriting [ip redacted]/24 to
        192.168.10.0/24 hides the address without unpublishing it — it already
        travelled in the contributor's pull request — and leaves everyone
        believing the system worked. Reject loudly and tell the sender to edit
        it at the source.

    **What this does NOT detect**, listed deliberately, because a privacy check
    that people trust more than it deserves is worse than a grep nobody trusts:

      * MACs written without separators (`106FD9DA5A16`) or Cisco-style
        (`106f.d9da.5a16`). Twelve hex digits in a row match half the log
        output in the world, and a false positive here is a red build a
        stranger cannot fix.
      * Hostnames, serial numbers, Bluetooth device names, account addresses.
      * Anything obfuscated on purpose. This stops accidents, not adversaries.
    """
    found = [f"MAC address {m.group(0)}" for m in MAC_RE.finditer(text)]
    seen_spans: list[tuple[int, int]] = [m.span() for m in MAC_RE.finditer(text)]

    def overlaps_mac(span: tuple[int, int]) -> bool:
        return any(start < span[1] and span[0] < end for start, end in seen_spans)

    for match in IPV4_RE.finditer(text):
        token = match.group(0)
        if _is_loopback(token) or _is_documentation_address(token):
            continue
        if not _is_publishable_network(token):
            found.append(f"host IP {token.split('/')[0]}")

    import ipaddress

    for match in IPV6_CANDIDATE_RE.finditer(text):
        token = match.group(0)
        if overlaps_mac(match.span()):
            continue
        try:
            ipaddress.ip_address(token.split("/")[0])
        except ValueError:
            continue  # a timestamp, a range, a fragment of something else
        if _is_loopback(token) or _is_documentation_address(token):
            continue
        if not _is_publishable_network(token):
            found.append(f"host IPv6 {token.split('/')[0]}")
    return found


# --- markdown as data --------------------------------------------------------


class Table:
    """A markdown table: its header cells, its rows, and where each row is."""

    def __init__(self, header: list[str], rows: list[tuple[int, list[str]]]):
        self.header = header
        self.rows = rows

    @property
    def width(self) -> int:
        return len(self.header)


def _split_row(line: str) -> list[str]:
    """Split a markdown row, ignoring pipes inside backticks."""
    cells, cell, in_code = [], [], False
    for char in line.strip().strip("|"):
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(char)
    cells.append("".join(cell).strip())
    return cells


def parse_tables(text: str) -> list[Table]:
    """Every markdown table in `text`, with 1-based line numbers for the rows."""
    lines = text.splitlines()
    tables: list[Table] = []
    index = 0

    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        header = _split_row(lines[index])
        if index + 1 >= len(lines) or not re.fullmatch(
            r"\|[\s:|-]+\|", lines[index + 1].strip()
        ):
            index += 1
            continue

        rows: list[tuple[int, list[str]]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            rows.append((cursor + 1, _split_row(lines[cursor])))
            cursor += 1
        tables.append(Table(header, rows))
        index = cursor

    return tables


def github_slug(heading: str) -> str:
    """GitHub's anchor slug for a heading, near enough for link checking.

    Lowercase, punctuation dropped, spaces to hyphens. An em dash is
    punctuation, so "F3 — Pixel Buds" becomes "f3--pixel-buds", which is why
    the double hyphen in the anchors in docs/ is correct rather than a typo.
    """
    text = heading.strip().lstrip("#").strip().lower()
    text = re.sub(r"[`*_\[\]()]", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s", "-", text.strip())


def headings(text: str) -> list[str]:
    """Every ATX heading in a markdown document, hashes stripped."""
    out = []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and re.match(r"#{1,6}\s", line):
            out.append(line)
    return out


LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?://|mailto:)([^)\s]+)\)")


def broken_links(text: str, source: Path) -> list[str]:
    """Relative links in `text` that do not resolve, anchors included.

    `source` is the file the text came from: links resolve relative to its
    directory, and a bare `#anchor` resolves against the file itself. That last
    case is the most common one and the one that breaks most often, since
    renaming a heading kills it with no other trace.

    External links are never fetched. A dead URL is not a broken build, and a
    suite that needs the network stops being able to tell the difference.
    """
    findings: list[str] = []
    for match in LINK_RE.finditer(text):
        link = match.group(1)
        target, _, anchor = link.partition("#")

        destination = (source.parent / target).resolve() if target else source
        if target and not destination.exists():
            findings.append(f"{link} -> no such file")
            continue
        if not anchor:
            continue

        # For a bare `#anchor` the headings come from the text in hand, not from
        # disk: the caller may be checking a document that was never written.
        slugs = {
            github_slug(h)
            for h in headings(destination.read_text() if target else text)
        }
        if anchor not in slugs:
            where = destination.name if target else "this file"
            findings.append(f"{link} -> no heading #{anchor} in {where}")
    return findings


def promoted_ids() -> set[str]:
    """The capability ids in data/capabilities.toml.

    Read only. data/capabilities.toml belongs to development; the tests use it
    to know which ids exist and say nothing about what should be in it.
    """
    import tomllib

    with (DATA / "capabilities.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return {cap["id"] for cap in data.get("capability", [])}


def normalise_id(cap_id: str) -> str:
    """Fold the differences that make two ids look distinct but collide."""
    return re.sub(r"[-_]", "", cap_id.strip().lower())


# --- command sandbox ---------------------------------------------------------
#
# Scripts that inspect the machine are run against a directory of stub commands
# that replaces PATH outright. Replacement, not shadowing: a command with no
# stub is not found, rather than quietly falling through to the real binary.
# That distinction is the whole safety argument — on this machine the real
# binary might be the one that segfaults bluetoothd and takes the mouse down.

import os  # noqa: E402  - kept next to the sandbox helpers that use it
import shutil  # noqa: E402
import stat  # noqa: E402

BASH = shutil.which("bash") or "/bin/bash"

# What a script legitimately needs in order to run at all.
COREUTILS = ("sh", "awk", "sed", "cat", "grep", "head", "paste", "uname", "tr")


def write_sandbox(
    directory: Path,
    stubs: dict[str, str],
    *,
    coreutils: tuple[str, ...] = COREUTILS,
    log: Path | None = None,
) -> None:
    """Fill `directory` with stub commands and links to the real coreutils.

    If `log` is given, every stub records its own invocation there first, so a
    test can assert not only what a script printed but what it ran — including
    what it did not run.
    """
    for name, body in stubs.items():
        lines = body.splitlines()
        shebang, rest = lines[0], lines[1:]
        if log is not None:
            # printf, not echo: a stub name or a path with a quote in it would
            # otherwise break the script it is embedded in.
            rest.insert(0, f'printf "%s %s\\n" "{name}" "$*" >> "{log}"')
        path = directory / name
        path.write_text("\n".join([shebang, *rest]) + "\n")
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    for name in coreutils:
        if name in stubs:
            continue
        for prefix in ("/usr/bin", "/bin"):
            source = Path(prefix) / name
            if source.exists():
                (directory / name).symlink_to(source)
                break


def sandbox_env(directory: Path, **extra: str) -> dict[str, str]:
    """The environment a sandboxed run gets: our PATH, C locale, empty HOME.

    HOME matters as much as PATH here. `omapixel-status` reads
    ~/.local/share/omarchy/version by absolute path, which PATH cannot
    intercept, so a run that inherited the real HOME would pick up this
    machine's Omarchy version and behave differently in CI or in a clean VM.
    """
    return {
        **os.environ,
        "PATH": str(directory),
        "HOME": str(directory),
        "LC_ALL": "C",
        "LANG": "C",
        **extra,
    }
