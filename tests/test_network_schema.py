"""The [network] table: negative cases, written before the validation exists.

Device reports for phones may carry a [network] table. build-matrix.py does not
look at it today, so a malformed one is accepted silently — including
`subnet = "[ip redacted]/24"`, which is a host address that slips past the CI
privacy grep because the grep only checks for a `/NN` suffix.

Agreed with development on 2026-08-15: these cases are written here first, and
the validation is implemented in build-matrix.py against them. That file
belongs to development; this one belongs to the test suite.

Until then each case is marked `expectedFailure`, so the suite stays green and
still records what is missing. **When the validation lands, unittest will
report these as unexpected successes, which fails the run.** That is the
intended signal: delete the decorator, and the test becomes a real one.
"""

from __future__ import annotations

import unittest

from tests.support import MINIMAL_CAPABILITIES, device_report, temp_data


def network(body: str, *, kind: str = "phone") -> str:
    return device_report(f"\n[network]\n{body}\n", kind=kind)


class NetworkTable(unittest.TestCase):
    def assert_rejected(self, report: str, *fragments: str) -> None:
        with temp_data(MINIMAL_CAPABILITIES, {"a-device.toml": report}) as (mod, _):
            with self.assertRaises(mod.ReportError) as caught:
                mod.load_reports({"file-send"})
        message = str(caught.exception)
        self.assertIn("a-device.toml", message)
        for fragment in fragments:
            self.assertIn(fragment, message)

    def test_a_valid_network_table_is_accepted(self):
        """The one case that must pass now and keep passing after validation."""
        report = network(
            'same_subnet_as_host = true\n'
            'subnet = "192.168.10.0/24"\n'
            'reachable = "30/30 ICMP replies, TTL 64"\n'
            'rtt_ms = { min = 4.8, median = 338.0, p90 = 694.0, max = 1141.0 }'
        )
        with temp_data(MINIMAL_CAPABILITIES, {"a-device.toml": report}) as (mod, _):
            self.assertEqual(len(mod.load_reports({"file-send"})), 1)

    @unittest.expectedFailure
    def test_subnet_with_host_bits_set_is_rejected(self):
        """Not schema hygiene: this one is a privacy leak.

        docs/conventions.md, "Privacy in public reports". [ip redacted]/24
        identifies the reporter's machine, and a hand-written report is exactly
        where it will appear, because whoever writes it copies what `ip addr`
        printed. The current CI grep accepts it, since it only looks for a
        `/NN` suffix.

        Two things that must survive a future reader who finds this pedantic:
        it never softens into a warning — a report merged into a public
        repository cannot be unpublished — and it is never "fixed" by
        normalising the address to 192.168.10.0/24, which hides a leak that has
        already travelled in the contributor's pull request. Reject, and tell
        the sender.
        """
        self.assert_rejected(network('subnet = "[ip redacted]/24"'), "subnet")

    @unittest.expectedFailure
    def test_subnet_without_a_prefix_is_rejected(self):
        self.assert_rejected(network('subnet = "192.168.10.0"'), "subnet")

    @unittest.expectedFailure
    def test_subnet_with_an_impossible_prefix_is_rejected(self):
        self.assert_rejected(network('subnet = "192.168.10.0/33"'), "subnet")

    @unittest.expectedFailure
    def test_same_subnet_as_host_must_be_a_boolean(self):
        """`"true"` is a string that reads as truth and is not one."""
        self.assert_rejected(
            network('same_subnet_as_host = "true"'), "same_subnet_as_host"
        )

    @unittest.expectedFailure
    def test_rtt_values_must_be_numbers(self):
        self.assert_rejected(
            network('rtt_ms = { min = "4.8", median = 338.0, max = 1141.0 }'),
            "rtt_ms",
        )

    @unittest.expectedFailure
    def test_rtt_values_must_be_ordered(self):
        """min <= median <= p90 <= max. Out of order means a parsing mistake.

        Development hit exactly this on 2026-08-15: a decimal-comma locale
        turned a percentile calculation into nonsense. The numbers looked
        plausible, which is the dangerous kind of wrong.
        """
        self.assert_rejected(
            network('rtt_ms = { min = 900.0, median = 12.0, max = 1141.0 }'),
            "rtt_ms",
        )

    @unittest.expectedFailure
    def test_p90_above_max_is_rejected(self):
        self.assert_rejected(
            network('rtt_ms = { min = 4.8, median = 20.0, p90 = 2000.0, max = 1141.0 }'),
            "rtt_ms",
        )

    @unittest.expectedFailure
    def test_earbuds_cannot_have_a_network_table(self):
        """Earbuds have no subnet. A [network] table on one is a copied template."""
        self.assert_rejected(
            network('subnet = "192.168.10.0/24"', kind="earbuds"), "network"
        )


if __name__ == "__main__":
    unittest.main()
