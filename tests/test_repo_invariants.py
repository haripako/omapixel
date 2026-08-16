"""Invariants over the repository itself: the data, the matrix, the links.

These are the checks a stranger's pull request has to survive. Two of them were
CI-only until now, which meant nobody could run them before pushing:

  * the matrix is regenerated after a data change
  * no device report carries a MAC address or a host IP

The privacy one gets a positive control. A detector nobody has seen fail is not
evidence, so the same function that clears data/devices/ is fed a report that
really does leak, in a temporary directory, and has to catch it.
"""

from __future__ import annotations

import io
import re
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tests.support import (
    DATA,
    DOCS,
    ROOT,
    broken_links,
    device_report,
    load_build_matrix,
    normalise_id,
    privacy_violations,
    promoted_ids,
    temp_data,
)

DEVICES = DATA / "devices"


class GeneratedMatrix(unittest.TestCase):
    def test_matrix_is_current(self):
        """Same check CI runs, runnable before pushing."""
        module = load_build_matrix()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = module.main(["build-matrix.py", "--check"])
        self.assertEqual(
            code, 0,
            f"{err.getvalue().strip()}\nReproduce with: scripts/build-matrix.py --check",
        )

    def test_matrix_says_it_is_generated(self):
        first = (DOCS / "02-capability-matrix.md").read_text().splitlines()[0]
        self.assertIn("DO NOT EDIT BY HAND", first)


class RealData(unittest.TestCase):
    """The live data/ directory has to satisfy the generator it feeds."""

    def test_capabilities_and_reports_load(self):
        module = load_build_matrix()
        caps = module.load_capabilities()
        self.assertTrue(caps)
        module.load_reports({cap["id"] for cap in caps})

    def test_capability_ids_are_kebab_case(self):
        for cap_id in sorted(promoted_ids()):
            with self.subTest(id=cap_id):
                self.assertRegex(cap_id, r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_no_two_capability_ids_nearly_collide(self):
        """`buds_anc` and `buds-anc` are one typo and two orphaned reports.

        The id is the join key with every hardware report, and a collision
        corrupts data that cannot be regenerated: the reporter is gone and the
        hardware is not here.
        """
        seen: dict[str, str] = {}
        for cap_id in sorted(promoted_ids()):
            key = normalise_id(cap_id)
            self.assertNotIn(
                key, seen,
                f"{cap_id!r} and {seen.get(key)!r} differ only in case or separators",
            )
            seen[key] = cap_id

    def test_every_capability_phase_has_a_section_in_the_roadmap(self):
        """A capability belongs to a phase, and a phase has to be somewhere."""
        roadmap = (DOCS / "03-roadmap.md").read_text()
        # The phase headings, not the whole document: a failure here should name
        # the missing phase, not print the roadmap back at you.
        sections = {
            match.group(1)
            for match in re.finditer(r"^##\s+(F\d)\b", roadmap, re.MULTILINE)
        }
        with (DATA / "capabilities.toml").open("rb") as fh:
            caps = tomllib.load(fh)["capability"]
        for cap in caps:
            with self.subTest(id=cap["id"]):
                self.assertIn(
                    cap["phase"], sections,
                    f"{cap['id']} is in phase {cap['phase']}, which has no section "
                    f"in docs/03-roadmap.md (found: {', '.join(sorted(sections))})",
                )

    def test_report_template_would_pass_validation(self):
        """The template is the first thing a contributor copies.

        If it drifts from the schema, every new report starts invalid and the
        project's own example is the one teaching the mistake.
        """
        text = (DATA / "report-template.toml").read_text()
        module = load_build_matrix()
        with temp_data((DATA / "capabilities.toml").read_text(),
                       {"template.toml": text}) as (mod, _):
            caps = mod.load_capabilities()
            reports = mod.load_reports({cap["id"] for cap in caps})
        self.assertEqual(len(reports), 1)
        self.assertTrue(reports[0]["results"], "the template has no example result")
        self.assertIsNot(module, None)

    def test_device_reports_are_named_after_their_device(self):
        for path in sorted(DEVICES.glob("*.toml")):
            with self.subTest(file=path.name):
                self.assertRegex(path.name, r"^[a-z0-9]+(-[a-z0-9]+)*\.toml$")


class PrivacyOfPublishedReports(unittest.TestCase):
    """A stranger writes the report; it is rendered into a published document."""

    def test_no_device_report_contains_a_mac_or_a_host_ip(self):
        for path in sorted(DEVICES.glob("*.toml")):
            with self.subTest(file=path.name):
                found = privacy_violations(path.read_text())
                if found:
                    self.fail(
                        f"{path.name} leaks {', '.join(found)}.\n"
                        f"Use the adapter model and the bare subnet instead; see "
                        f"docs/conventions.md, 'Privacy in public reports'.\n"
                        f"If that is a four-part version number and not an "
                        f"address, it is a known false positive: quote it as "
                        f"prose or drop the fourth component.\n"
                        f"Do NOT normalise the address away — it already travelled "
                        f"in the contributor's pull request. Reject the report and "
                        f"ask them to edit it at the source."
                    )

    def test_the_generated_matrix_contains_no_mac_or_host_ip(self):
        """Reports are clean and the renderer must not reassemble anything."""
        text = (DOCS / "02-capability-matrix.md").read_text()
        self.assertEqual(privacy_violations(text), [])

    # --- positive controls: prove the detector actually detects --------------

    def test_detector_catches_a_mac_address(self):
        leaky = device_report() + '\nbt_mac = "[mac redacted]"\n'
        self.assertIn("MAC address [mac redacted]", privacy_violations(leaky))

    def test_detector_catches_a_bare_host_ip(self):
        leaky = device_report() + '\naddress = "[ip redacted]"\n'
        self.assertIn("host IP [ip redacted]", privacy_violations(leaky))

    def test_detector_catches_a_host_ip_wearing_a_prefix(self):
        """The gap in the CI grep: it accepts anything ending in /NN."""
        leaky = device_report() + '\nsubnet = "[ip redacted]/24"\n'
        self.assertIn("host IP [ip redacted]", privacy_violations(leaky))

    def test_detector_allows_a_real_subnet(self):
        fine = device_report() + '\nsubnet = "192.168.10.0/24"\n'
        self.assertEqual(privacy_violations(fine), [])

    def test_detector_does_not_trip_on_version_numbers(self):
        """`bluez 5.87` and `r-quick-share 0.11.5-5` are not addresses."""
        text = 'bluez = "5.87"\ntool = "r-quick-share 0.11.5-5"\nkernel = "7.1.8-arch1-3"'
        self.assertEqual(privacy_violations(text), [])

    # --- the seven that used to get through ---------------------------------
    #
    # Found by code review on 2026-08-15 by attacking the detector rather than
    # trusting it. Each of these walked straight past the first version.

    def test_detector_catches_a_hyphenated_mac(self):
        """The IEEE's canonical form, and what Windows shows in its BT panel.

        This is the leak that will actually happen: a contributor copies the
        address out of Windows and pastes it into a report.
        """
        self.assertTrue(privacy_violations('bt = "10-6F-D9-DA-5A-16"'))

    def test_detector_catches_a_global_ipv6_address(self):
        """A whole address family was missing, not an edge case."""
        self.assertTrue(
            privacy_violations('addr = "2a02:9130:88c1:4e00:1a2b:3c4d:5e6f:7a8b"')
        )

    def test_detector_catches_a_link_local_ipv6_address(self):
        """fe80:: with EUI-64 carries the MAC inside it."""
        self.assertTrue(privacy_violations('addr = "fe80::1a2b:3c4d:5e6f:7a8b"'))

    def test_detector_catches_a_single_host_dressed_as_a_network(self):
        """192.168.10.0/32 is exactly one machine, and /31 is two."""
        for cidr in ("192.168.10.0/32", "192.168.10.0/31"):
            with self.subTest(cidr=cidr):
                self.assertTrue(privacy_violations(f'subnet = "{cidr}"'))

    def test_detector_catches_a_host_ending_in_zero_inside_a_wider_network(self):
        """10.0.5.0 is a host in 10.0.4.0/23, and it ends in .0."""
        self.assertTrue(privacy_violations('subnet = "10.0.5.0/23"'))

    def test_detector_allows_a_genuine_wide_network(self):
        """The other half of the previous case: 10.0.4.0/23 really is a network."""
        self.assertEqual(privacy_violations('subnet = "10.0.4.0/23"'), [])

    def test_detector_allows_an_ipv6_subnet(self):
        self.assertEqual(privacy_violations('subnet = "2a02:9130:88c1::/48"'), [])

    def test_detector_does_not_trip_on_timestamps_or_usb_ids(self):
        """Colons are everywhere. The parser decides, not the shape."""
        text = 'log = "23:15:49 started"\nusb = "18d1:4ee2"\nadapter = "0e8d:0608"'
        self.assertEqual(privacy_violations(text), [])

    def test_a_four_part_version_is_a_known_false_positive(self):
        """It fails closed, so it is a nuisance and not a leak.

        `5.87.2.1` is indistinguishable from an address by shape, and the
        detector chooses to shout. Pinned here so the behaviour is on the
        record, and the failure message says so — a stranger's build going red
        over a version string is how a privacy check loses its welcome.
        """
        self.assertTrue(privacy_violations('bluez = "5.87.2.1"'))

    def test_the_documented_blind_spots_are_still_blind(self):
        """Pins what the docstring promises, so the promise cannot rot.

        Separator-less and Cisco-style MACs are deliberately not detected: a
        false positive on twelve hex digits would be a red build a stranger
        cannot fix. If somebody adds detection, this test fails and the
        docstring gets corrected in the same commit.
        """
        for shape in ("106FD9DA5A16", "106f.d9da.5a16"):
            with self.subTest(shape=shape):
                self.assertEqual(privacy_violations(f'bt = "{shape}"'), [])


class MarkdownLinks(unittest.TestCase):
    """Relative links resolve, anchors included.

    Seven agents write these documents in one tree and cross-reference each
    other's files. A renamed heading kills a link in silence, and the first
    person to notice is a stranger on GitHub.
    """

    def markdown_files(self) -> list[Path]:
        files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md"]
        files += sorted(DOCS.glob("*.md"))
        return [path for path in files if path.exists()]

    def test_every_relative_link_resolves(self):
        for path in self.markdown_files():
            findings = broken_links(path.read_text(), path)
            with self.subTest(file=path.name):
                if findings:
                    self.fail(f"{path.name}: " + "; ".join(findings))

    # --- positive controls: the checker has to be able to fail ---------------
    #
    # Asked by research on 2026-08-15, and a fair question: a link test that
    # silently skips the case it was written for looks exactly like a link test
    # that passes. These prove each shape is really being checked.

    def control(self, body: str) -> list[str]:
        """Run the checker over synthetic markdown next to the real docs."""
        return broken_links(body, DOCS / "synthetic.md")

    def test_control_missing_file_is_caught(self):
        self.assertTrue(self.control("[gone](99-nowhere.md)"))

    def test_control_missing_anchor_in_another_file_is_caught(self):
        self.assertTrue(self.control("[bad](03-roadmap.md#f9--imaginary)"))

    def test_control_same_file_anchor_is_checked_not_skipped(self):
        """`[x](#anchor)` with no path: the commonest link and the frailest."""
        body = "# Title\n\n## E. Earbuds\n\n[good](#e-earbuds)\n[bad](#not-a-heading)\n"
        findings = self.control(body)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("not-a-heading", findings[0])

    def test_control_valid_links_are_left_alone(self):
        self.assertEqual(self.control("[ok](03-roadmap.md#f3--pixel-buds)"), [])

    def test_control_external_links_are_never_fetched(self):
        """No network, ever. A dead URL is not a broken build."""
        self.assertEqual(
            self.control("[up](https://example.invalid/nothing) [m](mailto:a@b.c)"), []
        )

    def test_control_headings_inside_code_fences_do_not_count(self):
        body = "# Real\n\n```\n## Fake heading\n```\n\n[bad](#fake-heading)\n"
        self.assertTrue(self.control(body))


class DerivedDocumentsCarryTheirDate(unittest.TestCase):
    """conventions.md made mechanical.

    A derived document without a date cannot be aged out or reproduced, and
    every claim in these two is derived.
    """

    PROVENANCE = re.compile(
        r"[Dd]erived from .*? on (\d{1,2} \w+ \d{4})", re.DOTALL
    )

    def test_derived_documents_declare_when_they_were_gathered(self):
        for name in ("features.md", "01-landscape.md"):
            path = DOCS / name
            if not path.exists():
                self.skipTest(f"{name} does not exist yet")
            head = "\n".join(path.read_text().splitlines()[:10])
            with self.subTest(file=name):
                match = self.PROVENANCE.search(head)
                self.assertIsNotNone(
                    match,
                    f"{name} must say 'Derived from ... on <D Month YYYY>' in its "
                    f"first ten lines",
                )

    def test_the_date_is_a_real_date_and_not_in_the_future(self):
        from datetime import date, datetime

        for name in ("features.md", "01-landscape.md"):
            path = DOCS / name
            if not path.exists():
                self.skipTest(f"{name} does not exist yet")
            head = "\n".join(path.read_text().splitlines()[:10])
            match = self.PROVENANCE.search(head)
            if match is None:
                continue  # reported by the test above
            with self.subTest(file=name):
                parsed = datetime.strptime(match.group(1), "%d %B %Y").date()
                self.assertLessEqual(
                    parsed, date.today(),
                    f"{name} is dated {parsed}, which has not happened yet",
                )


if __name__ == "__main__":
    unittest.main()
