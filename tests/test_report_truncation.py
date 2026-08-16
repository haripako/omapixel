"""A truncated report must not pass for a complete one.

Raised by backend on 2026-08-16, and the reason it matters is not obvious: a
truncated TOML file **is still valid TOML**. The structure is flat, so cutting
it in half does not break the parse the way half a markdown document is
obviously half. It loads, with fewer `[[result]]` blocks than its author
measured, and those rows then read `untested` — which the matrix defines as
"nobody has tried it on that hardware".

So the file fabricates that claim against somebody who did try it and took the
trouble to send it in. Same asset the markdown injection attacked — the
traceability the matrix promises — reached by accident instead of on purpose,
and with nobody ever noticing.

Every report therefore ends with `# *— end of report —*`, emitted by
`hw-report.sh --toml` and by the fixtures in tests/support.py.

The rejection lives in `build-matrix.py` and is backend's; it was reverted once
because the fixtures did not emit the marker. They do now. These are the
negatives; they were written before the rejection existed and went green when
it landed, which is what says they can fail.

Two traps, both verified, both failing in opposite directions:

  * the marker is a TOML comment, so it never appears in the parsed dict. A
    check over parsed data would declare every report truncated.
  * `--markdown` quotes the marker in its header to announce it, so that mode
    contains the string twice and a report cut off after the header would pass
    a grep over the whole text. The check has to look at the last non-empty
    line and nothing else.
"""

from __future__ import annotations

import unittest

from tests.support import (
    END_MARKER_LINE,
    MINIMAL_CAPABILITIES,
    device_report,
    temp_data,
)

RESULT = """
[[result]]
id = "file-send"
status = "works"
method = "measured"
"""


def truncated(text: str) -> str:
    """The same report with its final marker cut off, as a transfer would."""
    kept = [line for line in text.splitlines() if END_MARKER_LINE not in line]
    return "\n".join(kept) + "\n"


class TruncatedReportsAreRefused(unittest.TestCase):
    def load(self, text: str):
        with temp_data(MINIMAL_CAPABILITIES, {"a-device.toml": text}) as (mod, _):
            return mod.load_reports({"file-send"})

    def assert_rejected(self, text: str) -> None:
        with temp_data(MINIMAL_CAPABILITIES, {"a-device.toml": text}) as (mod, _):
            with self.assertRaises(mod.ReportError) as caught:
                mod.load_reports({"file-send"})
        self.assertIn("a-device.toml", str(caught.exception))

    def test_a_complete_report_is_accepted(self):
        """Has to pass now and keep passing once the rejection lands."""
        self.assertEqual(len(self.load(device_report(RESULT))), 1)

    def test_the_fixtures_emit_the_marker_on_the_last_line(self):
        """Guards the harness: without this, every negative below is vacuous.

        A fixture that stopped emitting the marker would make the truncation
        tests pass for the wrong reason, and the rejection would be reverted a
        second time for the same avoidable cause.
        """
        lines = [ln for ln in device_report(RESULT).splitlines() if ln.strip()]
        self.assertIn(END_MARKER_LINE, lines[-1])

    def test_a_truncated_toml_file_still_parses(self):
        """The premise, asserted rather than assumed.

        If cutting a report broke the parse, none of this would be needed —
        tomllib would reject it and the matter would end there.
        """
        import tomllib

        cut = truncated(device_report(RESULT))
        self.assertIn("file-send", str(tomllib.loads(cut)))

    def test_a_report_without_the_marker_is_rejected(self):
        self.assert_rejected(truncated(device_report(RESULT)))

    def test_a_report_cut_before_its_results_is_rejected(self):
        """The damaging shape: it loads, and reports nothing its author measured."""
        cut = truncated(device_report(RESULT)).split("[[result]]")[0]
        self.assert_rejected(cut)

    def test_the_marker_must_be_last_not_merely_present(self):
        """The grep trap, in the form a real file would take.

        `--markdown` quotes the marker in its header, so a report can carry the
        string and still be cut. Searching the whole text would pass it.
        """
        text = device_report(RESULT).replace(
            'os = "Android 17"',
            f'os = "Android 17"\nnote = "ends with {END_MARKER_LINE}"',
        )
        self.assert_rejected(truncated(text))

    def test_trailing_blank_lines_do_not_make_a_report_truncated(self):
        """The other direction: over-strictness rejecting a correct file.

        A report saved with a trailing newline has an empty last line. Checking
        `lines[-1]` without dropping blanks would refuse it, and the
        contributor would have no idea what they did wrong.
        """
        self.assertEqual(len(self.load(device_report(RESULT) + "\n\n\n")), 1)


if __name__ == "__main__":
    unittest.main()
