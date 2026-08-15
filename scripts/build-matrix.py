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


class ReportError(Exception):
    """A data file is malformed. Always names the file and the field."""


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
    return value.strip()


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
            "os": data.get("device", {}).get("os", "").strip(),
            "kind": require(data, "device", "kind", path),
            "host": data.get("host", {}),
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
