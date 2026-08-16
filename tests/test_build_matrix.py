"""scripts/build-matrix.py: validation, rendering and the --check contract.

Every case runs against a throwaway data directory. Nothing here reads or
writes data/, which belongs to development, and nothing here starts a process.

The failure messages matter as much as the failures. A stranger's first
contact with this project is a malformed report and whatever the script says
about it, so the tests assert that the message names the file and the field.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from tests.support import (
    MINIMAL_CAPABILITIES,
    device_report,
    load_build_matrix,
    temp_data,
)


class CapabilityValidation(unittest.TestCase):
    def assert_error_mentions(self, capabilities: str, *fragments: str) -> None:
        module = load_build_matrix()
        with temp_data(capabilities) as (mod, _):
            with self.assertRaises(mod.ReportError) as caught:
                mod.load_capabilities()
        message = str(caught.exception)
        for fragment in fragments:
            self.assertIn(fragment, message)
        self.assertIsNot(module, None)

    def test_minimal_file_loads(self):
        with temp_data(MINIMAL_CAPABILITIES) as (mod, _):
            caps = mod.load_capabilities()
        self.assertEqual([cap["id"] for cap in caps], ["file-send"])

    def test_empty_file_is_rejected(self):
        self.assert_error_mentions("schema = 1\n", "no [[capability]] entries")

    def test_duplicate_id_is_rejected(self):
        text = MINIMAL_CAPABILITIES + """
[[capability]]
id = "file-send"
name = "Send files, again"
phase = "F1"
"""
        self.assert_error_mentions(text, "duplicate", "file-send")

    def test_missing_name_is_rejected(self):
        text = """
schema = 1

[[capability]]
id = "file-send"
phase = "F1"
"""
        self.assert_error_mentions(text, "file-send", "name")

    def test_missing_phase_is_rejected(self):
        text = """
schema = 1

[[capability]]
id = "file-send"
name = "Send files to the phone"
"""
        self.assert_error_mentions(text, "file-send", "phase")

    def test_invented_phase_is_rejected_and_says_where_it_belongs(self):
        """A capability joins the matrix when it joins a phase, not before.

        The message has to send the author somewhere, or the rule reads as
        bureaucracy. It points at docs/features.md, which is where a target
        with no phase lives.
        """
        text = MINIMAL_CAPABILITIES.replace('phase = "F1"', 'phase = "someday"')
        self.assert_error_mentions(
            text, "file-send", "someday", "F0", "F5", "docs/features.md"
        )

    def test_lowercase_phase_is_rejected(self):
        """Phases are compared exactly. 'f1' is a typo, not a synonym."""
        text = MINIMAL_CAPABILITIES.replace('phase = "F1"', 'phase = "f1"')
        self.assert_error_mentions(text, "file-send", "f1")

    def test_every_declared_phase_is_accepted(self):
        for phase in load_build_matrix().PHASES:
            with self.subTest(phase=phase):
                text = MINIMAL_CAPABILITIES.replace('phase = "F1"', f'phase = "{phase}"')
                with temp_data(text) as (mod, _):
                    self.assertEqual(len(mod.load_capabilities()), 1)


class ReportValidation(unittest.TestCase):
    def assert_report_error(self, report: str, *fragments: str) -> None:
        with temp_data(MINIMAL_CAPABILITIES, {"a-device.toml": report}) as (mod, _):
            with self.assertRaises(mod.ReportError) as caught:
                mod.load_reports({"file-send"})
        message = str(caught.exception)
        self.assertIn("a-device.toml", message)
        for fragment in fragments:
            self.assertIn(fragment, message)

    def test_report_with_no_results_is_valid(self):
        """The honest empty report. It is what the first real one looks like."""
        with temp_data(MINIMAL_CAPABILITIES, {"a.toml": device_report()}) as (mod, _):
            reports = mod.load_reports({"file-send"})
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["results"], [])

    def test_missing_devices_directory_is_not_an_error(self):
        with temp_data(MINIMAL_CAPABILITIES) as (mod, work):
            mod.DEVICES = work / "data" / "nowhere"
            self.assertEqual(mod.load_reports({"file-send"}), [])

    def test_unknown_capability_id_is_rejected(self):
        report = device_report("""
[[result]]
id = "teleportation"
status = "works"
method = "measured"
""")
        self.assert_report_error(report, "teleportation", "data/capabilities.toml")

    def test_unknown_status_is_rejected(self):
        report = device_report("""
[[result]]
id = "file-send"
status = "mostly"
method = "measured"
""")
        self.assert_report_error(report, "status", "mostly", "works", "partial")

    def test_unknown_method_is_rejected(self):
        report = device_report("""
[[result]]
id = "file-send"
status = "works"
method = "vibes"
""")
        self.assert_report_error(report, "method", "vibes", "measured", "derived")

    def test_repeated_result_id_is_rejected(self):
        """Two verdicts on one capability in one report is a contradiction."""
        block = """
[[result]]
id = "file-send"
status = "works"
method = "measured"

[[result]]
id = "file-send"
status = "broken"
method = "measured"
"""
        self.assert_report_error(device_report(block), "repeated", "file-send")

    def test_unknown_device_kind_is_rejected(self):
        self.assert_report_error(device_report(kind="toaster"), "kind", "toaster")

    def test_missing_reporter_handle_is_rejected(self):
        report = device_report().replace('handle = "tester"', 'handle = ""')
        self.assert_report_error(report, "[reporter].handle")

    def test_missing_device_section_is_rejected(self):
        report = """
schema = 1

[reporter]
handle = "tester"
date = "2026-08-15"
"""
        self.assert_report_error(report, "[device]")

    def test_broken_toml_names_the_file(self):
        self.assert_report_error("this is not = = toml", "not valid TOML")


class Summarise(unittest.TestCase):
    """One matrix cell. The rules that decide what a reader sees."""

    def cell(self, *results: tuple[str, str], origin: str = "device") -> str:
        mod = load_build_matrix()
        # origin is part of a loaded report since 2026-08-16, and summarise()
        # reads it: a result from the emulator must not render as a measurement.
        # These fixtures say "device" because they are about status and method.
        reports = [
            {"origin": origin,
             "results": [{"id": "file-send", "status": s, "method": m}]}
            for s, m in results
        ]
        return mod.summarise("file-send", reports)

    def test_no_reports_reads_untested(self):
        self.assertEqual(self.cell(), "untested")

    def test_derived_only_is_flagged(self):
        """A row that looks confident but nobody ran gets marked."""
        self.assertEqual(self.cell(("works", "derived")), "works 1 (derived)")

    def test_one_measured_report_removes_the_flag(self):
        cell = self.cell(("works", "derived"), ("works", "measured"))
        self.assertEqual(cell, "works 2")
        self.assertNotIn("derived", cell)

    def test_statuses_are_counted_not_merged(self):
        self.assertEqual(self.cell(("works", "measured"), ("works", "measured")),
                         "works 2")

    def test_worst_status_leads(self):
        """The summary leads with the problems, not the wins."""
        cell = self.cell(
            ("works", "measured"),
            ("blocked", "measured"),
            ("broken", "measured"),
            ("partial", "measured"),
        )
        self.assertEqual(cell, "broken 1, partial 1, works 1, blocked 1")

    def test_other_capabilities_do_not_leak_into_the_cell(self):
        mod = load_build_matrix()
        reports = [{"results": [{"id": "clipboard", "status": "broken",
                                 "method": "measured"}]}]
        self.assertEqual(mod.summarise("file-send", reports), "untested")


class Rendering(unittest.TestCase):
    def render(self, capabilities=MINIMAL_CAPABILITIES, devices=None) -> str:
        with temp_data(capabilities, devices) as (mod, _):
            caps = mod.load_capabilities()
            return mod.render(caps, mod.load_reports({c["id"] for c in caps}))

    def test_output_warns_that_it_is_generated(self):
        text = self.render()
        self.assertIn("GENERATED FILE", text.splitlines()[0])
        self.assertIn("scripts/build-matrix.py", text)

    def test_no_reports_says_so_rather_than_showing_an_empty_table(self):
        self.assertIn("No device reports yet.", self.render())

    def test_report_count_is_grammatical(self):
        one = self.render(devices={"a.toml": device_report()})
        self.assertIn("Built from 1 device report.", one)
        two = self.render(devices={"a.toml": device_report(),
                                   "b.toml": device_report()})
        self.assertIn("Built from 2 device reports.", two)

    def test_untested_is_explained_in_the_document_itself(self):
        """The matrix is read by strangers who never open conventions.md."""
        self.assertIn("Read `untested` as untested, not as broken.", self.render())

    def test_notes_become_the_constraints_section(self):
        text = self.render(MINIMAL_CAPABILITIES + '\nnotes = "Same subnet only."\n')
        self.assertIn("Constraints worth knowing", text)
        self.assertIn("Same subnet only.", text)

    def test_a_result_is_rendered_with_its_reporter_and_date(self):
        report = device_report("""
[[result]]
id = "file-send"
status = "partial"
method = "measured"
tool = "r-quick-share 0.11.5"
notes = "Only with the screen on."
""")
        text = self.render(devices={"a.toml": report})
        self.assertIn("Reported by **tester** on 2026-08-15", text)
        self.assertIn("Only with the screen on.", text)
        self.assertIn("r-quick-share 0.11.5", text)

    def test_output_is_committable(self):
        """The matrix is a generated file that lives in git.

        Trailing whitespace and a missing final newline both produce diff noise
        on a file nobody edits by hand, which is the fastest way to make a
        generated document look like it was tampered with.
        """
        text = self.render()
        self.assertTrue(text.endswith("\n"))
        for number, line in enumerate(text.splitlines(), start=1):
            self.assertEqual(line, line.rstrip(),
                             f"trailing whitespace on generated line {number}")


class CommandLine(unittest.TestCase):
    """main(): exit codes and what lands on stdout versus stderr."""

    def run_main(self, argv, capabilities=MINIMAL_CAPABILITIES, devices=None):
        with temp_data(capabilities, devices) as (mod, _):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = mod.main(["build-matrix.py", *argv])
            written = mod.OUTPUT.read_text() if mod.OUTPUT.exists() else None
        return code, out.getvalue(), err.getvalue(), written

    def test_write_creates_the_matrix_and_reports_the_counts(self):
        code, out, err, written = self.run_main([])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("1 capabilities", out)
        self.assertIn("GENERATED FILE", written)

    def test_check_passes_when_the_matrix_is_current(self):
        with temp_data(MINIMAL_CAPABILITIES) as (mod, _):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(mod.main(["build-matrix.py"]), 0)
                self.assertEqual(mod.main(["build-matrix.py", "--check"]), 0)
            self.assertIn("matrix current", out.getvalue())

    def test_check_fails_when_the_matrix_is_stale(self):
        with temp_data(MINIMAL_CAPABILITIES) as (mod, _):
            mod.OUTPUT.write_text("# something a human edited\n")
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                code = mod.main(["build-matrix.py", "--check"])
        self.assertEqual(code, 1)
        self.assertIn("out of date", err.getvalue())
        self.assertIn("scripts/build-matrix.py", err.getvalue())

    def test_check_fails_when_the_matrix_is_missing(self):
        with temp_data(MINIMAL_CAPABILITIES) as (mod, _):
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(mod.main(["build-matrix.py", "--check"]), 1)

    def test_check_does_not_write_the_file(self):
        with temp_data(MINIMAL_CAPABILITIES) as (mod, _):
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                mod.main(["build-matrix.py", "--check"])
            self.assertFalse(mod.OUTPUT.exists())

    def test_bad_data_exits_1_with_a_message_not_a_traceback(self):
        broken = MINIMAL_CAPABILITIES.replace('phase = "F1"', 'phase = "someday"')
        code, out, err, _ = self.run_main([], capabilities=broken)
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("error: "), err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
