"""`origin`: nothing simulated may pass for a measurement.

The virtual Pixel produces reports that share the schema, the ids and the join
key with a report from a stranger holding a real phone. Nothing in the data
distinguishes them, and the matrix is what this project publishes.

The field was agreed on 2026-08-16, closed vocabulary, mandatory, and the same
name in the state contract and in the report schema:

    origin = "device"     a real device
    origin = "emulator"   our virtual Pixel
    origin = "unknown"    could not be determined

**Not a boolean, and that is the whole design.** `simulated = true` cannot say
"I do not know": its absence collapses to false, which reads as "real" — the
one reading the rule forbids. With three values the unknown case has somewhere
to live, and the invariant stops depending on nobody forgetting the field.

The negative cases were written before the validation existed, same arrangement
as the `[network]` schema, and went green when backend landed it on 2026-08-16.
They were red first, which is the only way to know they can fail.

Note what is *not* tested here: that a file mentions the word "virtual". A
report generated against the emulator by somebody in a hurry does not contain
the word, so a heuristic over the text would be theatre. Only the declared
field counts.
"""

from __future__ import annotations

import unittest

from tests.support import MINIMAL_CAPABILITIES, temp_data

RESULT = """
[[result]]
id = "file-send"
status = "works"
method = "measured"
tool = "r-quick-share 0.11.5"
"""


def report(origin: str | None = "device", *, results: str = RESULT) -> str:
    line = f'origin = "{origin}"\n' if origin is not None else ""
    return f"""
schema = 1
{line}
[reporter]
handle = "tester"
date = "2026-08-16"

[device]
kind = "phone"
vendor = "Google"
model = "Pixel 7 Pro"
os = "Android 17"
{results}
"""


class OriginIsDeclared(unittest.TestCase):
    def load(self, text: str):
        with temp_data(MINIMAL_CAPABILITIES, {"a-device.toml": text}) as (mod, _):
            return mod.load_reports({"file-send"})

    def assert_rejected(self, text: str, *fragments: str) -> None:
        with temp_data(MINIMAL_CAPABILITIES, {"a-device.toml": text}) as (mod, _):
            with self.assertRaises(mod.ReportError) as caught:
                mod.load_reports({"file-send"})
        message = str(caught.exception)
        self.assertIn("a-device.toml", message)
        for fragment in fragments:
            self.assertIn(fragment, message)

    def test_a_real_report_declaring_its_origin_is_accepted(self):
        """Must pass now and keep passing. The rest are the negatives."""
        self.assertEqual(len(self.load(report("device"))), 1)

    def test_a_report_without_origin_is_rejected(self):
        """Mandatory, because a missing field must never mean "real"."""
        self.assert_rejected(report(None), "origin")

    def test_an_invented_origin_is_rejected(self):
        self.assert_rejected(report("simulated"), "origin", "device", "emulator")

    def test_an_emulator_report_is_accepted_but_marked(self):
        """The emulator may report. It may not be mistaken for hardware."""
        reports = self.load(report("emulator"))
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["origin"], "emulator")


class SimulatedResultsAreNotMeasurements(unittest.TestCase):
    """The point of the field, asserted on what gets published.

    Rejecting a value in the loader is the mechanism; what matters is that the
    matrix never shows an emulator result the way it shows a measured one. The
    assertion is deliberately shape-independent: the cell must carry *some*
    qualifier, whatever wording backend picks. Pinning the wording here would
    force a decision that is not mine.
    """

    def cell(self, origin: str | None) -> str:
        with temp_data(MINIMAL_CAPABILITIES, {"a.toml": report(origin)}) as (mod, _):
            caps = mod.load_capabilities()
            reports = mod.load_reports({cap["id"] for cap in caps})
            return mod.summarise("file-send", reports)

    def test_a_real_measured_report_reads_as_measured(self):
        self.assertEqual(self.cell("device"), "works 1")

    def test_an_emulator_result_does_not_read_as_a_measurement(self):
        cell = self.cell("emulator")
        self.assertNotEqual(
            cell, "works 1",
            "an emulator result is rendered exactly like a measurement on real "
            "hardware. Whatever the qualifier is, there has to be one",
        )

    def test_an_unknown_origin_does_not_read_as_a_measurement(self):
        """Unknown is not real. That is the rule the three values exist for."""
        self.assertNotEqual(self.cell("unknown"), "works 1")

    def test_emulator_and_unknown_are_distinguishable_from_each_other(self):
        """Not only from a real measurement: from each other.

        They have different fixes. An unknown origin is corrected by declaring
        it; an emulator origin is not corrected at all, because the run really
        did happen against the emulator. Collapsing them into one qualifier
        would tell a contributor to fix something that is not broken.
        """
        self.assertNotEqual(self.cell("emulator"), self.cell("unknown"))


if __name__ == "__main__":
    unittest.main()
