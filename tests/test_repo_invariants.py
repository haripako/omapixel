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

# The canonical example MAC, and the one a copy-paste recipe has to show so the
# reader knows the shape of what to substitute. Exempted here rather than in the
# detector, deliberately: the detector stays strict, so a real address still
# fails everywhere, and this exception is visible in the test that grants it.
PLACEHOLDER_MAC = "AA:BB:CC:DD:EE:FF"

# Addresses that appear in the tree on purpose: placeholders in recipes and
# fixtures in this suite. Declared as literals here, which is the point — a new
# address-shaped string anywhere in the repository fails this sweep until
# somebody states that it is synthetic, and the statement is reviewable.
#
# The lesson that produced the list: fixtures in this very directory used to
# carry a real MAC and a real host IP from the reference machine, which is why a
# history rewrite had to touch test files. A fixture holding real data is a leak
# with a test wrapped around it.
DECLARED_SYNTHETIC = (
    PLACEHOLDER_MAC, PLACEHOLDER_MAC.lower(),   # the canonical example MAC
    "aa-bb-cc-dd-ee-ff",                        # the same, in IEEE hyphen form
    "11:22:33:44:55:66",                        # a second placeholder in docs
    "02:11:22:33:44:55",                        # this suite's synthetic MAC
    "10-6F-D9-DA-5A-16",                        # the hyphen-form evasion example
    "10.42.7.99",                               # this suite's synthetic host
    "100.99.0.1",                               # this suite's synthetic CGNAT host
    "172.17.0.1",                               # the default docker bridge
    # Addresses that exist only to explain the rules that flag them: the /32
    # that is one machine, a host ending in .0 inside a wider network, and the
    # bad arithmetic of zeroing the fourth octet of a /16.
    "192.168.10.0", "10.0.5.0", "10.1.2.0",
    "fe80::", "fe80::1a2b:3c4d:5e6f:7a8b",      # the link-local example
)


# A carrier-grade NAT address in this suite's own range. The first version of
# the test below used the reference machine's actual Tailscale address, copied
# out of the message that reported it — the same mistake, one paragraph after
# writing that a fixture holding real data is a leak with a test around it. The
# committed-content sweep caught it in the only window where a fix exists.
SYNTHETIC_CGNAT = "100.99.0.1"


def identifies_a_machine(finding: str) -> bool:
    """True for the address families that can point at somebody's machine.

    A tree-wide sweep meets every address a document uses to explain
    addressing, so the target has to be narrower than the one used on a device
    report: the private ranges, the carrier-grade NAT block Tailscale hands out,
    and link-local. A four-component version number — `5.87.2.1`, the detector's
    known false positive — is not in any of them and stops being noise here,
    while a Tailscale address, which a filter written around RFC1918 alone would
    have missed, is.

    MAC findings always count: there is no such thing as a MAC that identifies
    nothing.
    """
    import ipaddress

    if finding.startswith("MAC address"):
        return True
    token = finding.rsplit(" ", 1)[-1]
    try:
        address = ipaddress.ip_address(token)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_link_local
        or address in ipaddress.ip_network("100.64.0.0/10")
    )


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

    def test_every_real_report_declares_where_it_came_from(self):
        """The published data, not the loader.

        The loader's rules are tested with fixtures; this is the live directory
        that feeds the matrix a stranger reads. A report here without `origin`
        would be one whose provenance nobody can establish after the fact.
        """
        for path in sorted(DEVICES.glob("*.toml")):
            with path.open("rb") as fh:
                data = tomllib.load(fh)
            with self.subTest(file=path.name):
                self.assertIn(
                    "origin", data,
                    f"{path.name} does not say whether it came from a device, "
                    f"the emulator, or something undetermined",
                )
                self.assertIn(data["origin"], ("device", "emulator", "unknown"))

    def test_no_committed_report_claims_hardware_it_did_not_run_on(self):
        """A simulated run must not be sitting in the published data as real.

        Not a check on the word "virtual" anywhere in the file — a report
        generated against the emulator by somebody in a hurry does not contain
        it. The declared field is the only thing that counts, and this asserts
        the two cannot disagree: a report marked `device` must not name the
        emulator as the tool that produced its results.
        """
        for path in sorted(DEVICES.glob("*.toml")):
            with path.open("rb") as fh:
                data = tomllib.load(fh)
            if data.get("origin") != "device":
                continue
            for result in data.get("result", []):
                tool = str(result.get("tool", "")).lower()
                with self.subTest(file=path.name, id=result.get("id")):
                    self.assertNotIn(
                        "virtual-pixel", tool,
                        f"{path.name} claims origin=device but {result.get('id')} "
                        f"was produced by the emulator",
                    )

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

    def test_what_is_committed_is_clean_not_only_the_working_tree(self):
        """The working tree is not what gets published; the commit is.

        Raised by code review on 2026-08-17, and measured: a redaction had
        landed in the working tree while the committed blob — and the sha the
        remote was serving — still carried the real address. Every sweep in
        this file read files from disk, so all of them were green over a HEAD
        that leaked.

        This reads the committed content instead. It cannot undo anything
        already pushed — published is published — but it fails before the next
        push, which is the only moment a fix is still possible.
        """
        import subprocess

        listing = subprocess.run(
            # The whole tree, not a directory. The leak that was published
            # entered through docs/ while the detector watched data/devices/,
            # and the fixtures that carried real data were in tests/. Scoping
            # this to where the last leak came from is how the next one gets in.
            ["git", "ls-tree", "-r", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=ROOT,
        )
        if listing.returncode != 0:
            self.skipTest("not a git checkout")

        for name in listing.stdout.split():
            blob = subprocess.run(
                ["git", "show", f"HEAD:{name}"],
                capture_output=True, text=True, cwd=ROOT,
            )
            if blob.returncode != 0:
                continue
            found = [
                item for item in privacy_violations(blob.stdout)
                if identifies_a_machine(item)
                and not any(known in item for known in DECLARED_SYNTHETIC)
            ]
            with self.subTest(file=name):
                if found:
                    self.fail(
                        f"the committed {name} leaks {', '.join(found)}.\n"
                        f"The working tree may already be clean — that is not "
                        f"what gets pushed. Amend or commit the redaction "
                        f"before this reaches the remote, because afterwards "
                        f"there is no fix: published is published."
                    )

    def test_no_document_we_write_ourselves_leaks_either(self):
        """The discipline was on the stranger's input, not on our own output.

        Found by code review on 2026-08-17: the sweep covered data/devices/ and
        the generated matrix, and nothing else in docs/. The document that
        actually leaked was ours — raw `bluetoothctl` output pasted into the
        journal, MAC addresses with the device name beside them, and the host
        IP twice.

        Same publication risk, same git history, and a stricter rule than for a
        contributor: we know better.
        """
        for path in sorted(DOCS.glob("**/*.md")):
            found = [
                item for item in privacy_violations(path.read_text())
                if PLACEHOLDER_MAC not in item
            ]
            with self.subTest(file=path.relative_to(DOCS).as_posix()):
                if found:
                    self.fail(
                        f"docs/{path.relative_to(DOCS)} leaks {', '.join(found)}.\n"
                        f"Redact it: the adapter model instead of its MAC, the "
                        f"bare subnet instead of the host address. A device name "
                        f"next to a MAC is worse than either alone.\n"
                        f"Loopback and four-part version numbers are exempt "
                        f"already, so this is not one of those."
                    )

    # --- positive controls: prove the detector actually detects --------------

    def test_detector_catches_a_mac_address(self):
        leaky = device_report() + '\nbt_mac = "02:11:22:33:44:55"\n'
        self.assertIn("MAC address 02:11:22:33:44:55", privacy_violations(leaky))

    def test_detector_catches_a_bare_host_ip(self):
        leaky = device_report() + '\naddress = "10.42.7.99"\n'
        self.assertIn("host IP 10.42.7.99", privacy_violations(leaky))

    def test_detector_catches_a_host_ip_wearing_a_prefix(self):
        """The gap in the CI grep: it accepts anything ending in /NN."""
        leaky = device_report() + '\nsubnet = "10.42.7.99/24"\n'
        self.assertIn("host IP 10.42.7.99", privacy_violations(leaky))

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

    def test_detector_catches_a_carrier_grade_nat_address(self):
        """100.64/10 is what Tailscale hands out, and it is not RFC1918.

        Confirmed the hard way on 2026-08-17: a filter written around the
        private ranges alone would never have seen an address on the overlay,
        which identifies a machine to everybody else on that overlay exactly as
        precisely as a LAN address does on a LAN. Generic shape, no real
        address: putting one in a test would publish it again.
        """
        self.assertTrue(privacy_violations(f'ts = "{SYNTHETIC_CGNAT}"'))
        self.assertTrue(identifies_a_machine(f"host IP {SYNTHETIC_CGNAT}"))

    def test_a_bare_network_or_broadcast_is_not_a_host(self):
        """What a document writes when it means "the subnet".

        Flagging these would flag the redaction the rules ask for, and a check
        that punishes compliance gets switched off.
        """
        for address in ("10.42.7.0", "10.42.7.255"):
            with self.subTest(address=address):
                self.assertEqual(privacy_violations(f'a = "{address}"'), [])

    def test_a_version_number_is_not_an_identifying_address(self):
        """The tree-wide sweep meets version strings; it must not stop on them.

        The detector still flags `5.87.2.1` when reading a device report, where
        four dotted numbers have no business being — it fails closed there. On a
        sweep across every file, that same shape is noise, and noise is what
        gets an invariant disabled.
        """
        self.assertTrue(privacy_violations('bluez = "5.87.2.1"'))
        self.assertFalse(identifies_a_machine("host IP 5.87.2.1"))

    def test_detector_exempts_the_documentation_ranges(self):
        """RFC 5737 and RFC 3849 exist so documents need not use real addresses.

        Flagging them would push an author back towards pasting a real one,
        which is the opposite of what this check is for.
        """
        for address in ("192.0.2.34", "198.51.100.7", "203.0.113.9",
                        "2001:db8::1"):
            with self.subTest(address=address):
                self.assertEqual(privacy_violations(f'addr = "{address}"'), [])

    def test_detector_still_catches_a_real_address_beside_a_documented_one(self):
        """The exemption must not become a way of smuggling one in."""
        found = privacy_violations('example = "192.0.2.1", real = "10.42.7.99"')
        self.assertEqual(found, ["host IP 10.42.7.99"])

    def test_detector_exempts_loopback(self):
        """127.0.0.1 identifies nobody, and appears in every local example.

        Flagging it would train people to ignore this check, which is how a
        privacy invariant dies.
        """
        self.assertEqual(privacy_violations("curl http://127.0.0.1:8080"), [])
        self.assertEqual(privacy_violations("connect to [::1]:8080"), [])

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
