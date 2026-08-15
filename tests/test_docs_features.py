"""docs/features.md: the format research asked to have locked down.

The document belongs to research and none of these tests judge its content.
They enforce the machine-checkable half of the format, and one invariant in
particular that no human remembers to maintain:

    **id** in bold  <=>  the id exists in data/capabilities.toml
    `id` in ticks   <=>  it does not

The drift that matters is the second one going stale: development promotes a
capability, the catalogue keeps saying it does not exist yet, and the two
documents disagree about what this project has committed to. Same class of bug
as a stale matrix, and invisible in review.

data/capabilities.toml is read here only to learn which ids exist. Nothing in
this file has an opinion about its contents; that is development's call.
"""

from __future__ import annotations

import re
import unittest

from tests.support import DOCS, normalise_id, parse_tables, promoted_ids

FEATURES = DOCS / "features.md"

DATA_HEADER = [
    "Apple", "What it actually does", "Path on Linux today",
    "Target here", "Tier", "id", "Phase",
]

# A second table that carries ids, registered by research on 2026-08-15 after
# two ids slipped into it in the wrong style and the suite stayed green.
# Declared by header, not swept for: prose in this file is full of backticked
# tool names — `pbpctrl`, `wl-clipboard`, `btmgmt info` — and a global sweep
# would demand bold on every passing mention of a promoted capability.
EXPOSURE_HEADER = [
    "Target", "Produced by", "Would have to expose", "Desktop consumes",
    'What "unknown" has to look like',
]

# (header, index of the id column) for every table under the id contract.
ID_TABLES = ((DATA_HEADER, -2), (EXPOSURE_HEADER, 0))

ID_COLUMN = -2
TIER_COLUMN = -3
PHASE_COLUMN = -1

TIER_RE = re.compile(r"^T[1-4](\s*/\s*T[1-4])?$")
PHASE_RE = re.compile(r"^(F[0-5](\s*/\s*F[0-5])?|—)$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

BOLD = re.compile(r"^\*\*([^*]+)\*\*$")
TICKED = re.compile(r"^`([^`]+)`$")


class FeaturesFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not FEATURES.exists():
            raise unittest.SkipTest("docs/features.md does not exist")
        cls.text = FEATURES.read_text()
        cls.tables = parse_tables(cls.text)
        # Data tables are the seven-column ones. The tier legend and the other
        # narrow tables are distinguished by width, never by position.
        cls.data_tables = [t for t in cls.tables if t.header == DATA_HEADER]
        cls.promoted = promoted_ids()

    def rows(self):
        for table in self.data_tables:
            for line, cells in table.rows:
                yield line, cells

    def id_cells(self, only: list[str] | None = None):
        """Every id cell in every table registered under the id contract."""
        for header, column in ID_TABLES:
            if only is not None and header != only:
                continue
            for table in self.tables:
                if table.header != header:
                    continue
                for line, cells in table.rows:
                    if len(cells) != len(header):
                        continue  # reported by the ragged-row test
                    cell = cells[column]
                    if cell in ("—", "-", ""):
                        continue
                    # A cell may carry two ids: `call-notify`, `call-audio`.
                    for part in cell.split(","):
                        yield line, part.strip()

    # --- shape --------------------------------------------------------------

    def test_there_are_data_tables(self):
        self.assertTrue(self.data_tables, "no seven-column data tables found")

    def test_every_registered_id_table_is_present(self):
        """A renamed header silently removes a table from the contract.

        Ausencia de rojo no es cobertura: if one of these stops matching, the
        ids inside it stop being checked and nothing says so.
        """
        for header, _ in ID_TABLES:
            with self.subTest(table=header[0]):
                self.assertTrue(
                    any(t.header == header for t in self.tables),
                    f"no table with header {header!r}. If it was renamed, update "
                    f"ID_TABLES; if it was deleted, delete its entry",
                )

    def test_every_data_table_has_the_agreed_header(self):
        for table in self.data_tables:
            with self.subTest(header=table.header[0]):
                self.assertEqual(table.header, DATA_HEADER)

    def test_no_row_is_ragged(self):
        for table in self.data_tables:
            for line, cells in table.rows:
                with self.subTest(line=line):
                    self.assertEqual(
                        len(cells), len(DATA_HEADER),
                        f"features.md:{line} has {len(cells)} cells, expected 7",
                    )

    # --- closed vocabularies ------------------------------------------------

    def test_tier_column_uses_the_closed_vocabulary(self):
        for line, cells in self.rows():
            tier = cells[TIER_COLUMN]
            if tier in ("—", "-", ""):
                continue
            with self.subTest(line=line, tier=tier):
                self.assertRegex(
                    tier, TIER_RE,
                    f"features.md:{line}: Tier is {tier!r}; expected T1-T4 or a pair",
                )

    def test_tier_pairs_ascend(self):
        for line, cells in self.rows():
            tier = cells[TIER_COLUMN]
            if "/" not in tier:
                continue
            low, high = (part.strip() for part in tier.split("/"))
            with self.subTest(line=line, tier=tier):
                self.assertLess(
                    low, high,
                    f"features.md:{line}: {tier!r} should read low tier first",
                )

    def test_phase_column_uses_the_closed_vocabulary(self):
        for line, cells in self.rows():
            phase = cells[PHASE_COLUMN]
            with self.subTest(line=line, phase=phase):
                self.assertRegex(
                    phase, PHASE_RE,
                    f"features.md:{line}: Phase is {phase!r}; expected F0-F5, "
                    f"a pair, or an em dash",
                )

    def test_phase_pairs_ascend(self):
        for line, cells in self.rows():
            phase = cells[PHASE_COLUMN]
            if "/" not in phase:
                continue
            low, high = (part.strip() for part in phase.split("/"))
            with self.subTest(line=line, phase=phase):
                self.assertLess(low, high)

    # --- the bold/backtick contract -----------------------------------------

    def test_bold_ids_exist_and_ticked_ids_do_not(self):
        for line, raw in self.id_cells():
            bold, ticked = BOLD.match(raw), TICKED.match(raw)
            with self.subTest(line=line, cell=raw):
                self.assertTrue(
                    bold or ticked,
                    f"features.md:{line}: {raw!r} is neither **bold** nor `ticked`. "
                    f"Bold means the id is in data/capabilities.toml, ticks mean "
                    f"it is not, and an em dash means the row proposes none",
                )
            # fail() rather than assertIn/assertNotIn: those print the whole
            # set of promoted ids before the message, and the reader needs the
            # one-character fix, not an inventory.
            if bold and bold.group(1) not in self.promoted:
                self.fail(
                    f"features.md:{line}: `{bold.group(1)}` is not in "
                    f"data/capabilities.toml — put it in backticks"
                )
            if ticked and ticked.group(1) in self.promoted:
                self.fail(
                    f"features.md:{line}: `{ticked.group(1)}` is already in "
                    f"capabilities.toml — put it in bold in docs/features.md"
                )

    # Deliberately not tested: "every promoted id appears in features.md".
    # The mapping is injective, not onto. `hotkeys` and `menu-entry` are
    # Omarchy-layer capabilities with no Apple analogue, so the catalogue —
    # which is organised by what Apple does — has no row to put them in.
    # A test for that rule would be red forever and correctly so.

    # --- id hygiene ---------------------------------------------------------

    def test_proposed_ids_are_kebab_case(self):
        for line, raw in self.id_cells():
            cap_id = re.sub(r"[`*]", "", raw)
            with self.subTest(line=line, id=cap_id):
                self.assertRegex(cap_id, KEBAB_RE)

    def test_proposed_ids_are_unique_within_the_catalogue(self):
        """Uniqueness applies to the catalogue rows, which define the ids.

        Not to the document: the exposure table discusses ids the catalogue
        already proposed, so repetition there is the point, not a mistake.
        """
        seen: dict[str, int] = {}
        for line, raw in self.id_cells(only=DATA_HEADER):
            cap_id = re.sub(r"[`*]", "", raw)
            with self.subTest(id=cap_id):
                self.assertNotIn(
                    cap_id, seen,
                    f"features.md:{line}: {cap_id!r} already appears on line "
                    f"{seen.get(cap_id)}",
                )
            seen[cap_id] = line

    def test_every_exposure_row_names_an_id_the_catalogue_proposed(self):
        """The exposure table elaborates; it does not invent.

        An id that appears only here is one nobody defined, and it would carry
        the backtick style of a proposal without any row proposing it.
        """
        catalogue = {re.sub(r"[`*]", "", raw) for _, raw in self.id_cells(only=DATA_HEADER)}
        for line, raw in self.id_cells(only=EXPOSURE_HEADER):
            cap_id = re.sub(r"[`*]", "", raw)
            with self.subTest(line=line, id=cap_id):
                self.assertIn(
                    cap_id, catalogue,
                    f"features.md:{line}: `{cap_id}` appears in the exposure table "
                    f"but no catalogue row proposes it",
                )

    def test_no_proposed_id_nearly_collides_with_a_promoted_one(self):
        """`buds_anc` against `buds-anc` corrupts the join key silently."""
        promoted_by_key = {normalise_id(i): i for i in self.promoted}
        for line, raw in self.id_cells():
            cap_id = re.sub(r"[`*]", "", raw)
            twin = promoted_by_key.get(normalise_id(cap_id))
            if twin is None or twin == cap_id:
                continue
            self.fail(
                f"features.md:{line}: {cap_id!r} differs from the promoted "
                f"{twin!r} only in case or separators. Ids are the join key with "
                f"every hardware report"
            )


if __name__ == "__main__":
    unittest.main()
