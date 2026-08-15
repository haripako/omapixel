#!/usr/bin/env python3
"""Render docs/02-capability-matrix.md from the report data.

The matrix is generated, never hand-edited. Rows come from data/capabilities.toml,
cells come from data/devices/*.toml. Every claim in the output can be traced back
to a named reporter and a date.

  scripts/build-matrix.py           write docs/02-capability-matrix.md
  scripts/build-matrix.py --check   validate and fail if the file is stale (CI)

Requires nothing beyond the standard library (tomllib, Python 3.11+).
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES = ROOT / "data" / "capabilities.toml"
DEVICES = ROOT / "data" / "devices"
OUTPUT = ROOT / "docs" / "02-capability-matrix.md"

STATUSES = ("works", "partial", "broken", "blocked")
METHODS = ("measured", "derived")
KINDS = ("phone", "earbuds")

# The phases in docs/03-roadmap.md. A capability belongs to the matrix once it
# belongs to a phase — that is what separates a row from an aspiration. Anything
# still being researched lives in docs/features.md, which is not this file.
PHASES = ("F0", "F1", "F2", "F3", "F4", "F5")

# Worst-first, so the summary leads with the problems rather than the wins.
STATUS_ORDER = ("broken", "partial", "works", "blocked")


# Device reports are the only input to this repository written by a stranger
# and rendered into a published document. Everything below reaches the matrix
# as markdown, so a newline escapes the table, a pipe forges a column, and a
# backtick escapes a code span — after which the contributor writes whatever
# they like into a file whose own header promises that "every cell traces back
# to a named reporter and a date".
#
# Rejected on load rather than escaped on render. Escaping would let the odd
# value through and paint it nicely; rejecting tells the contributor what to
# fix, and matches how this project handles a leaked MAC address.
# Angle brackets are here because markdown renders raw HTML: an
# "<!-- comment -->" in a value swallows the rest of the line and passes a
# filter that only looks for pipes. Found by the security agent after the first
# version of this check let exactly that through.
# "](" is the two-character sequence that turns text into a link; the brackets
# and parentheses are fine on their own, since model names use them.
# "://" is here because a bare URL needs no markdown at all: GitHub autolinks
# it. Blocking the link syntax and leaving the plain URL closes the front door
# and leaves the window open — worst in [reporter].handle, which renders into
# the very sentence that promises who measured this. A contributor with a link
# to share puts it in the issue, not in a generated document.
# The message below promises "a control character", so the check has to mean
# every character a reader cannot see, not just the ASCII ones. U+2028 and
# U+2029 are line and paragraph separators, U+200B-U+200F and U+FEFF are
# zero-width, and U+202A-U+202E and U+2066-U+2069 reorder text without changing
# it — the Trojan Source trick, where the rendered line and the stored line say
# different things. None of them belong in a device model or a note, and a
# guarantee with silent exceptions is worse than no guarantee.
FORBIDDEN = re.compile(
    "["
    r"|`<>"
    r"\x00-\x1f\x7f"          # ASCII control, newline and tab included
    r"\u200b-\u200f"           # zero-width, and the direction marks
    r"\u2028\u2029"            # line separator, paragraph separator
    r"\u202a-\u202e"           # bidirectional overrides — Trojan Source
    r"\u2066-\u2069"           # bidirectional isolates, same trick
    r"\ufeff"                  # zero-width no-break space, the BOM
    "]"
    r"|\]\("
    # GitHub turns three shapes into links with no markdown syntax at all, and
    # its autolink extension defines exactly those three: a scheme, a bare
    # "www.", and an email address. Blocking markdown's link syntax and leaving
    # these open closes the door and leaves the window. Enumerating them is
    # sound here in a way that enumerating markdown in general is not — the set
    # is closed by specification, not by guesswork.
    r"|://"
    r"|\bwww\."
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"
)
FORBIDDEN_DESCRIPTION = (
    "a pipe, a backtick, an angle bracket, a markdown link, a URL, a newline, "
    "or a control or invisible character"
)

# [host] was previously copied into the document key and value, unvalidated,
# so arbitrary keys became arbitrary markdown.
HOST_KEYS = ("distro", "desktop", "kernel", "bluez", "bt_adapter", "arch", "shell")


class ReportError(Exception):
    """A data file is malformed. Always names the file and the field."""


def clean(value: str, where: str, path: Path) -> str:
    """Reject anything that would escape the cell it is rendered into."""
    if FORBIDDEN.search(value):
        raise ReportError(
            f"{path.name}: {where} contains {FORBIDDEN_DESCRIPTION}. "
            f"These are refused rather than escaped, because this field is "
            f"rendered into a published markdown document"
        )
    return value


def load(path: Path) -> dict:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ReportError(f"{path.name}: not valid TOML: {exc}") from exc


def require(data: dict, table: str, field: str, path: Path) -> str:
    section = data.get(table)
    if not isinstance(section, dict):
        raise ReportError(f"{path.name}: missing [{table}] section")
    value = section.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ReportError(f"{path.name}: [{table}].{field} is missing or empty")
    return clean(value.strip(), f"[{table}].{field}", path)


def load_capabilities() -> list[dict]:
    data = load(CAPABILITIES)
    caps = data.get("capability")
    if not caps:
        raise ReportError("capabilities.toml: no [[capability]] entries")

    seen: set[str] = set()
    for cap in caps:
        cap_id = cap.get("id")
        if not cap_id:
            raise ReportError("capabilities.toml: a [[capability]] has no id")
        if cap_id in seen:
            raise ReportError(f"capabilities.toml: duplicate capability id {cap_id!r}")
        seen.add(cap_id)
        for field in ("name", "phase"):
            if not cap.get(field):
                raise ReportError(f"capabilities.toml: {cap_id!r} has no {field}")
        if cap["phase"] not in PHASES:
            raise ReportError(
                f"capabilities.toml: {cap_id!r} has phase={cap['phase']!r}, "
                f"expected one of {', '.join(PHASES)}. A capability joins the "
                f"matrix when it joins a phase; until then it belongs in "
                f"docs/features.md"
            )
    return caps


def load_reports(known_ids: set[str]) -> list[dict]:
    if not DEVICES.is_dir():
        return []

    reports = []
    for path in sorted(DEVICES.glob("*.toml")):
        data = load(path)

        report = {
            "path": path,
            "handle": require(data, "reporter", "handle", path),
            "date": require(data, "reporter", "date", path),
            "vendor": require(data, "device", "vendor", path),
            "model": require(data, "device", "model", path),
            "os": clean(
                str(data.get("device", {}).get("os", "")).strip(),
                "[device].os", path,
            ),
            "kind": require(data, "device", "kind", path),
            "host": validated_host(data.get("host", {}), path),
            "results": [],
        }

        if report["kind"] not in KINDS:
            raise ReportError(
                f"{path.name}: [device].kind is {report['kind']!r}, "
                f"expected one of {', '.join(KINDS)}"
            )

        for result in data.get("result", []):
            cap_id = result.get("id")
            if cap_id not in known_ids:
                raise ReportError(
                    f"{path.name}: unknown capability id {cap_id!r}. "
                    f"Ids must exist in data/capabilities.toml"
                )
            for field in ("tool", "notes"):
                if field in result:
                    result[field] = clean(
                        str(result[field]).strip(), f"{cap_id!r}.{field}", path
                    )
            for field, allowed in (("status", STATUSES), ("method", METHODS)):
                value = result.get(field)
                if value not in allowed:
                    raise ReportError(
                        f"{path.name}: {cap_id!r} has {field}={value!r}, "
                        f"expected one of {', '.join(allowed)}"
                    )
            report["results"].append(result)

        ids = [r["id"] for r in report["results"]]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ReportError(
                f"{path.name}: repeated result ids: {', '.join(sorted(duplicates))}"
            )

        reports.append(report)
    return reports


def validated_host(host, path: Path) -> dict:
    """[host] is free-form, but not arbitrary: keys are whitelisted and every
    value is cleaned, because both are rendered straight into the document."""
    if not isinstance(host, dict):
        raise ReportError(f"{path.name}: [host] must be a table")
    out = {}
    for key, value in host.items():
        if key not in HOST_KEYS:
            raise ReportError(
                f"{path.name}: [host].{key} is not a recognised key. "
                f"Allowed: {', '.join(HOST_KEYS)}"
            )
        out[key] = clean(str(value).strip(), f"[host].{key}", path)
    return out


def device_label(report: dict) -> str:
    return f"{report['vendor']} {report['model']}"


def summarise(cap_id: str, reports: list[dict]) -> str:
    """One cell: the spread of reported statuses, worst first."""
    counts: dict[str, int] = {}
    derived_only = True
    for report in reports:
        for result in report["results"]:
            if result["id"] == cap_id:
                counts[result["status"]] = counts.get(result["status"], 0) + 1
                if result["method"] == "measured":
                    derived_only = False

    if not counts:
        return "untested"

    parts = [f"{status} {counts[status]}" for status in STATUS_ORDER if status in counts]
    cell = ", ".join(parts)
    return f"{cell} (derived)" if derived_only else cell


def render(caps: list[dict], reports: list[dict]) -> str:
    lines: list[str] = []
    add = lines.append

    add("<!-- GENERATED FILE — DO NOT EDIT BY HAND. -->")
    add("<!-- Edit data/capabilities.toml or data/devices/*.toml, then run:")
    add("     scripts/build-matrix.py -->")
    add("")
    add("# Capability matrix")
    add("")
    add(
        "What the Apple ecosystem does between iPhone and Mac, what can be done "
        "today between a Pixel and Arch Linux, and with which tool."
    )
    add("")
    add(
        f"Built from {len(reports)} device "
        f"{'report' if len(reports) == 1 else 'reports'}. "
        "Every cell traces back to a named reporter and a date; see the "
        "per-device sections below."
    )
    add("")
    add(
        "**Read `untested` as untested, not as broken.** An absent result means "
        "nobody has run it on that hardware, which is the most common state in a "
        "young project. See [conventions](conventions.md) for what the statuses "
        "and the measured/derived distinction mean."
    )
    add("")

    add("## Summary")
    add("")
    add("| Capability | Apple equivalent | Phase | Tool | Reported |")
    add("|---|---|---|---|---|")
    for cap in caps:
        add(
            f"| {cap['name']} | {cap.get('apple', '—')} | {cap['phase']} "
            f"| `{cap.get('tool', '—')}` | {summarise(cap['id'], reports)} |"
        )
    add("")

    notes = [cap for cap in caps if cap.get("notes")]
    if notes:
        add("### Constraints worth knowing")
        add("")
        for cap in notes:
            add(f"- **{cap['name']}** — {cap['notes']}")
        add("")

    add("## Reports")
    add("")
    if not reports:
        add("No device reports yet.")
        add("")
        return "\n".join(lines) + "\n"

    for report in reports:
        add(f"### {device_label(report)}")
        add("")
        os_bit = f", {report['os']}" if report["os"] else ""
        add(
            f"Reported by **{report['handle']}** on {report['date']} "
            f"({report['kind']}{os_bit})."
        )
        host = report["host"]
        if host:
            bits = [f"{key}: {value}" for key, value in host.items()]
            add("")
            add(f"Host — {'; '.join(bits)}.")
        add("")

        if not report["results"]:
            add("No capabilities tested yet on this device.")
            add("")
            continue

        add("| Capability | Status | Method | Tool | Notes |")
        add("|---|---|---|---|---|")
        by_id = {cap["id"]: cap for cap in caps}
        for result in report["results"]:
            cap = by_id[result["id"]]
            tool = result.get("tool", "—")
            add(
                f"| {cap['name']} | {result['status']} | {result['method']} "
                f"| `{tool}` | {result.get('notes', '')} |"
            )
        add("")

    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    check_only = "--check" in argv[1:]

    try:
        caps = load_capabilities()
        reports = load_reports({cap["id"] for cap in caps})
    except ReportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    rendered = render(caps, reports)

    if check_only:
        current = OUTPUT.read_text() if OUTPUT.exists() else ""
        if current != rendered:
            print(
                f"error: {OUTPUT.relative_to(ROOT)} is out of date. "
                "Run scripts/build-matrix.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"ok: {len(caps)} capabilities, {len(reports)} reports, matrix current")
        return 0

    OUTPUT.write_text(rendered)
    print(
        f"wrote {OUTPUT.relative_to(ROOT)} "
        f"({len(caps)} capabilities, {len(reports)} reports)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
