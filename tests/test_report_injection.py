"""A device report must not be able to write markdown into the matrix.

Reported by security on 2026-08-15 and reproduced: `notes` accepts a TOML
multi-line string, the newline escapes the table, and from there a report
writes free markdown into docs/02-capability-matrix.md — including a fabricated
`### Google Pixel 11 Pro` section attributed to a real reporter, with a `works`
nobody measured. `build-matrix.py --check` returns ok and exit 0, and the
privacy tests do not see it either, because their lens is MAC and IP and the
payload carries neither.

That matters more than it looks: the matrix promises in its own header that
every cell traces back to a named reporter and a date. A report that can forge
a section breaks the one claim this project makes about itself.

Backend fixed it the same day, and chose the right shape: reject loudly at load
time rather than escape at render time, so the contributor is told to fix the
file instead of having their text silently rewritten. These are the regression
tests. They were written against the broken version and went green when the fix
landed, which is the only way to know a regression test can fail.

The last test is the one that keeps the fix honest: an ordinary report with a
hyphen, a parenthesis and an accent has to keep working. A rejection tuned too
tight turns an injection filter into a contributor filter.
"""

from __future__ import annotations

import unittest

from tests.support import MINIMAL_CAPABILITIES, temp_data

REPORT = """
schema = 1
origin = "device"

[reporter]
handle = "{handle}"
date = "2026-08-15"

[device]
kind = "phone"
vendor = "{vendor}"
model = "{model}"
os = "Android 17"
{host}

[[result]]
id = "file-send"
status = "works"
method = "measured"
tool = {tool}
notes = {notes}
"""


def report(
    *,
    handle: str = "tester",
    vendor: str = "Google",
    model: str = "Pixel 7 Pro",
    tool: str = '"r-quick-share 0.11.5"',
    notes: str = '"Worked on the third attempt."',
    host: str = "",
) -> str:
    return REPORT.format(
        handle=handle, vendor=vendor, model=model, tool=tool, notes=notes, host=host
    )


class ReportsCannotWriteMarkdown(unittest.TestCase):
    def assert_rejected(self, text: str) -> None:
        with temp_data(MINIMAL_CAPABILITIES, {"zz-attacker.toml": text}) as (mod, _):
            with self.assertRaises(mod.ReportError):
                mod.load_reports({"file-send"})

    def rendered(self, text: str) -> str:
        with temp_data(MINIMAL_CAPABILITIES, {"zz-attacker.toml": text}) as (mod, _):
            caps = mod.load_capabilities()
            return mod.render(caps, mod.load_reports({cap["id"] for cap in caps}))

    # --- the rejections, written before the validation ----------------------

    def test_a_newline_in_notes_is_rejected(self):
        """The one that forges a section. Everything else is a variation."""
        payload = '"""Nothing to see\n\n### Google Pixel 11 Pro\n\nReported by **haripako**\n"""'
        self.assert_rejected(report(notes=payload))

    def test_a_pipe_in_notes_is_rejected(self):
        self.assert_rejected(report(notes='"works | broken | whatever"'))

    def test_a_backtick_in_tool_is_rejected(self):
        """`tool` is rendered inside a code span, and a backtick escapes it."""
        self.assert_rejected(report(tool='"pbpctrl` and **bold**"'))

    def test_a_control_character_is_rejected(self):
        self.assert_rejected(report(notes='"carriage\\r return"'))

    def test_markup_in_the_device_name_is_rejected(self):
        """vendor and model become a heading, handle becomes bold text."""
        self.assert_rejected(report(model="Pixel 7 Pro\\n\\n### Fabricated"))

    def test_an_unknown_host_key_is_rejected(self):
        """[host] keys and values are dumped into the document verbatim.

        No allow-list today, so a key can open an HTML comment and swallow the
        rest of the line.
        """
        self.assert_rejected(report(host='[host]\n"<!-- injected" = "x"'))

    # --- the whole path, not just the loader --------------------------------

    def test_the_forged_section_never_reaches_the_document(self):
        """The end state the attack was aiming at, asserted on the output.

        Rejecting at load time is the mechanism; this is the promise. The
        matrix says every cell traces back to a named reporter, and a report
        must not be able to fabricate a section attributed to someone else.
        """
        payload = '"""ok\n\n### Google Pixel 11 Pro\n\nReported by **haripako**\n"""'
        with self.assertRaises(Exception) as caught:
            self.rendered(report(notes=payload))
        self.assertIn("zz-attacker.toml", str(caught.exception))

    def test_the_refusal_names_the_file_and_exits_nonzero(self):
        """What a contributor actually sees. No traceback, no silent rewrite."""
        import io
        from contextlib import redirect_stderr, redirect_stdout

        payload = '"""ok\n\n### Fabricated\n"""'
        with temp_data(MINIMAL_CAPABILITIES,
                       {"zz-attacker.toml": report(notes=payload)}) as (mod, _):
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                code = mod.main(["build-matrix.py", "--check"])
        self.assertEqual(code, 1)
        self.assertIn("zz-attacker.toml", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    # --- the case that keeps the fix usable ---------------------------------

    def test_an_ordinary_report_still_passes(self):
        """A hyphen, a parenthesis, an accent and a slash are not an attack.

        If this ever fails, the injection fix has become a contributor filter,
        and the first stranger to hit it gets a CI error they cannot read.
        """
        ordinary = (
            '"Worked on the 3rd attempt (screen on) — 2/3 files arrived; '
            "the sender was José's phone, 100% battery.\""
        )
        with temp_data(MINIMAL_CAPABILITIES, {"ok.toml": report(notes=ordinary)}) as (
            mod,
            _,
        ):
            reports = mod.load_reports({"file-send"})
        self.assertEqual(len(reports), 1)
        self.assertIn("José", reports[0]["results"][0]["notes"])


if __name__ == "__main__":
    unittest.main()
