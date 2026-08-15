"""docs/06-design.md: the capabilities each surface assumes.

Rule 2 of CLAUDE.md — design against the matrix, not against the catalogue —
is the one rule in this repository that can verify itself, so it does.

The threshold is deliberately not "everything must be measured". Today every
capability is untested, because the single device report claims no results on
purpose; a test that failed on unmeasured capabilities would be red on every
row from the first commit and ignored by the third day. What fails here is a
design that **claims** more than the matrix supports:

    enhancement  the surface works without the capability, and the fourth
                 column says what it looks like without it
    required     the surface is meaningless without it, and is only legal once
                 the matrix shows it measured works or partial on real hardware

`buds-battery` appears on two rows on purpose: the combined figure and the
per-earbud split are different design decisions about the same capability. Do
not deduplicate by id, or the interesting case disappears.
"""

from __future__ import annotations

import tomllib
import unittest

from tests.support import DATA, DOCS, parse_tables, promoted_ids

DESIGN = DOCS / "06-design.md"
ANCHOR = "<!-- design-assumptions:"
HEADER = ["Surface", "Capability id", "Reliance", "When absent or unmeasured"]

RELIANCE = ("enhancement", "required")
# A surface may call a capability required once somebody has run it.
SUPPORTS_REQUIRED = ("works", "partial")


def measured_statuses() -> dict[str, set[str]]:
    """Per capability, the statuses somebody has actually measured.

    Derived results are excluded on purpose: a design cannot lean on a README.
    """
    out: dict[str, set[str]] = {}
    for path in sorted((DATA / "devices").glob("*.toml")):
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        for result in data.get("result", []):
            if result.get("method") == "measured":
                out.setdefault(result["id"], set()).add(result.get("status"))
    return out


class DesignDocumentAnchor(unittest.TestCase):
    """The anchor itself, checked apart from the table that uses it.

    Asked by the owner of the document, and the reasoning is his: the tests
    below skip when the anchor is missing, so a half-written file does not turn
    the suite red. But a file that *had* an anchor and lost it is a regression,
    and it would look identical. This test tells the two apart.
    """

    def test_the_anchor_is_still_there(self):
        if not DESIGN.exists():
            self.skipTest("docs/06-design.md does not exist")
        self.assertIn(
            ANCHOR, DESIGN.read_text(),
            "docs/06-design.md has lost its design-assumptions anchor. The tests "
            "that check every surface against the matrix are switched off until "
            "it comes back",
        )


class DesignAssumptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DESIGN.exists():
            raise unittest.SkipTest("docs/06-design.md does not exist")
        text = DESIGN.read_text()
        if ANCHOR not in text:
            raise unittest.SkipTest(
                "docs/06-design.md has no design-assumptions anchor yet"
            )
        # The table is the first one after the anchor comment.
        after = text.split(ANCHOR, 1)[1]
        tables = [t for t in parse_tables(after) if t.header == HEADER]
        if not tables:
            raise unittest.SkipTest("no assumptions table under the anchor")
        cls.table = tables[0]
        cls.promoted = promoted_ids()
        cls.measured = measured_statuses()

    def rows(self):
        for _, cells in self.table.rows:
            surface, cap_id, reliance, fallback = (c.strip() for c in cells[:4])
            yield surface, cap_id.strip("`"), reliance.lower(), fallback

    def test_the_table_has_rows(self):
        self.assertTrue(self.table.rows)

    def test_every_id_exists_in_the_matrix(self):
        """A broken join key. The header of capabilities.toml warns about this."""
        for surface, cap_id, _, _ in self.rows():
            with self.subTest(surface=surface, id=cap_id):
                self.assertIn(
                    cap_id, self.promoted,
                    f"{surface!r} assumes `{cap_id}`, which is not in "
                    f"data/capabilities.toml. Ask development to promote it, or "
                    f"design against something that exists",
                )

    def test_reliance_uses_the_closed_vocabulary(self):
        for surface, _, reliance, _ in self.rows():
            with self.subTest(surface=surface):
                self.assertIn(reliance, RELIANCE)

    def test_required_is_only_claimed_for_measured_capabilities(self):
        """The three-figure battery widget test.

        The day a surface is promoted to `required` because the mockup looks
        good, this fails and names what would have to be measured first.
        """
        for surface, cap_id, reliance, _ in self.rows():
            if reliance != "required":
                continue
            statuses = self.measured.get(cap_id, set())
            with self.subTest(surface=surface, id=cap_id):
                self.assertTrue(
                    statuses & set(SUPPORTS_REQUIRED),
                    f"{surface!r} declares `{cap_id}` required, but no device "
                    f"report measures it as works or partial "
                    f"(measured: {sorted(statuses) or 'nothing'}). Until somebody "
                    f"runs it on hardware, the only legal value is enhancement",
                )

    def test_every_enhancement_says_what_it_looks_like_when_absent(self):
        """An enhancement with no declared degradation is a promise with no plan B."""
        for surface, cap_id, reliance, fallback in self.rows():
            if reliance != "enhancement":
                continue
            with self.subTest(surface=surface, id=cap_id):
                self.assertTrue(
                    fallback and fallback not in ("—", "-"),
                    f"{surface!r} relies on `{cap_id}` as an enhancement but does "
                    f"not say how it degrades. No surface may paint a plausible zero",
                )

    def test_a_capability_may_appear_on_more_than_one_row(self):
        """Guard against a future cleanup deduplicating the table by id.

        The combined figure and the per-earbud split are two design decisions
        about `buds-battery`, and collapsing them loses the one the hardware
        may never support.
        """
        ids = [cap_id for _, cap_id, _, _ in self.rows()]
        self.assertEqual(len(ids), len(self.table.rows))


if __name__ == "__main__":
    unittest.main()
