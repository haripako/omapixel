"""scripts/omapixel-status: the contract every consumer will depend on.

Documented in docs/08-status-contract.md. This is the file a bar widget, a
keybinding and a doctor command all read instead of parsing pbpctrl, so the
tests care about two things above the rest:

  * **valid JSON when nothing underneath works.** The empty machine is the case
    that ships broken, because the developer's machine always has something
    installed. Here the sandbox guarantees it: PATH holds no tools at all.
  * **nothing is unavailable without saying why**, in both forms — `status` for
    code and `reason` for humans. Every failure found during bring-up on this
    machine was silent.

Everything runs against stub commands. The status command is never allowed to
reach the real Bluetooth stack from a test, and one of the tests below proves
it does not even try: the stubs log every invocation, so the suite can assert
what was *not* run.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import (
    SCRIPTS,
    privacy_violations,
    sandbox_env,
    write_sandbox,
)

STATUS = SCRIPTS / "omapixel-status"
# Resolved before PATH is replaced: the sandbox has no interpreter.
INTERPRETER = sys.executable

HOST_MAC = "AA:BB:CC:DD:EE:FF"
HOST_IP = "[ip redacted]"

STATUSES = {"not_installed", "no_answer", "nothing_present", "not_probed", "ready"}
CAPABILITY_KEYS = {"available", "status", "reason", "provider", "state"}

# An empty machine: no rquickshare, no kdeconnect-cli, no pbpctrl. Only the
# things that describe the host, and a bluetoothctl that refuses to do anything
# but read.
BASE_STUBS = {
    "ip": f"""#!/bin/sh
echo "2: eno1    inet {HOST_IP}/24 brd 192.168.10.255 scope global eno1"
echo "4: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0"
""",
    "hyprctl": """#!/bin/sh
echo "Hyprland 0.56.2 built from branch main"
""",
    "pacman": """#!/bin/sh
case "$2" in
  r-quick-share) echo "r-quick-share 0.11.5-5" ;;
  kdeconnect)    echo "kdeconnect 25.08.0-1" ;;
  pbpctrl)       echo "pbpctrl 0.1.8-1" ;;
  *) exit 1 ;;
esac
""",
    "bluetoothctl": f"""#!/bin/sh
case "$1 $2" in
  "devices Paired") echo "Device {HOST_MAC} Pixel Buds Pro 2" ;;
  "devices "*)      ;;
  *) echo "STUB REFUSED: bluetoothctl $*" >&2; exit 90 ;;
esac
""",
    "pgrep": """#!/bin/sh
exit 1
""",
}


class StatusContract(unittest.TestCase):
    def run_status(self, *args: str, stubs: dict[str, str] | None = None):
        """Run the status command in a sandbox. Returns (result, invocations)."""
        with tempfile.TemporaryDirectory(prefix="omapixel-status-") as tmp:
            sandbox = Path(tmp)
            log = sandbox / "invocations.log"
            write_sandbox(sandbox, {**BASE_STUBS, **(stubs or {})}, log=log)
            result = subprocess.run(
                [INTERPRETER, str(STATUS), *args],
                capture_output=True, text=True, timeout=60,
                env=sandbox_env(sandbox),
            )
            invocations = log.read_text().splitlines() if log.exists() else []
        return result, invocations

    def json_status(self, *args: str, stubs: dict[str, str] | None = None):
        result, invocations = self.run_status("--json", *args, stubs=stubs)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            return json.loads(result.stdout), invocations
        except json.JSONDecodeError as exc:
            self.fail(f"output is not valid JSON: {exc}\n{result.stdout!r}")

    # --- the empty machine --------------------------------------------------

    def test_json_is_valid_when_nothing_is_installed(self):
        """The case that matters and the one nobody tests."""
        data, _ = self.json_status()
        self.assertEqual(data["schema"], 1)
        self.assertIn("capabilities", data)
        self.assertTrue(data["capabilities"])

    def test_every_capability_is_unavailable_and_says_why(self):
        data, _ = self.json_status()
        for name, cap in data["capabilities"].items():
            with self.subTest(capability=name):
                self.assertFalse(cap["available"])
                self.assertEqual(cap["status"], "not_installed")
                self.assertTrue(cap["reason"], "unavailable with no reason given")
                self.assertIn("not installed", cap["reason"])

    def test_human_output_also_survives_the_empty_machine(self):
        result, _ = self.run_status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("host", result.stdout)
        for name in ("file-transfer", "phone-link", "buds"):
            self.assertIn(name, result.stdout)

    # --- shape --------------------------------------------------------------

    def test_capability_objects_have_the_documented_shape(self):
        data, _ = self.json_status()
        for name, cap in data["capabilities"].items():
            with self.subTest(capability=name):
                self.assertEqual(set(cap), CAPABILITY_KEYS)
                self.assertIsInstance(cap["available"], bool)
                self.assertIsInstance(cap["state"], dict)

    def test_status_vocabulary_is_closed(self):
        for stubs in (None, self.everything_working()):
            data, _ = self.json_status(stubs=stubs)
            for name, cap in data["capabilities"].items():
                with self.subTest(capability=name):
                    self.assertIn(cap["status"], STATUSES)

    def test_available_means_ready_and_nothing_else(self):
        """One truth, two fields. They must never disagree."""
        for stubs in (None, self.everything_working()):
            data, _ = self.json_status(stubs=stubs)
            for name, cap in data["capabilities"].items():
                with self.subTest(capability=name, status=cap["status"]):
                    self.assertEqual(cap["available"], cap["status"] == "ready")

    def test_nothing_is_unavailable_in_silence(self):
        for stubs in (None, self.everything_working()):
            data, _ = self.json_status(stubs=stubs)
            for name, cap in data["capabilities"].items():
                if cap["available"]:
                    continue
                with self.subTest(capability=name):
                    self.assertTrue(
                        isinstance(cap["reason"], str) and cap["reason"].strip(),
                        f"{name} is unavailable with no reason. A consumer cannot "
                        f"tell 'install a package' from 'pair a device'",
                    )

    def test_generated_timestamp_is_utc_and_parses(self):
        from datetime import datetime

        data, _ = self.json_status()
        datetime.strptime(data["generated"], "%Y-%m-%dT%H:%M:%SZ")

    # --- privacy ------------------------------------------------------------

    def test_output_carries_the_subnet_and_never_the_host_address(self):
        """This output gets pasted into issues, same as the hardware report."""
        data, _ = self.json_status()
        self.assertEqual(data["host"]["subnet"], "192.168.10.0/24")
        self.assertEqual(privacy_violations(json.dumps(data)), [])

    def test_virtual_interfaces_are_skipped(self):
        data, _ = self.json_status()
        self.assertNotIn("172.17", json.dumps(data))

    def test_paired_device_addresses_do_not_reach_the_output(self):
        """bluetoothctl hands back MAC addresses. None may survive."""
        data, _ = self.json_status(stubs={"pbpctrl": "#!/bin/sh\n"})
        self.assertNotIn(HOST_MAC, json.dumps(data))

    # --- what it must not do ------------------------------------------------

    def test_it_never_executes_the_tools_it_reports_on(self):
        """Detection is `which`. Execution is an incident.

        Launching rquickshare segfaults bluetoothd on this machine, 3 of 3 on
        2026-08-15. A status command that consumers may poll from a bar widget
        must never be the thing that does it.
        """
        stubs = {name: "#!/bin/sh\n" for name in
                 ("rquickshare", "kdeconnect-cli", "pbpctrl")}
        _, invocations = self.json_status(stubs=stubs)
        ran = {line.split()[0] for line in invocations}
        self.assertNotIn("rquickshare", ran)
        self.assertNotIn("pbpctrl", ran)

    def test_it_only_ever_reads_from_bluetoothctl(self):
        """Reading the pairing list is safe. Talking is not."""
        stubs = {"pbpctrl": "#!/bin/sh\n"}
        _, invocations = self.json_status(stubs=stubs)
        for line in invocations:
            if not line.startswith("bluetoothctl"):
                continue
            with self.subTest(call=line):
                self.assertRegex(
                    line, r"^bluetoothctl (devices|show|info)\b",
                    f"the status command ran a state-changing Bluetooth call: {line}",
                )

    def test_paired_buds_are_reported_but_not_queried_by_default(self):
        """The refusal is a feature, and it has to explain itself."""
        data, _ = self.json_status(stubs={"pbpctrl": "#!/bin/sh\n"})
        buds = data["capabilities"]["buds"]
        self.assertEqual(buds["status"], "not_probed")
        self.assertFalse(buds["available"])
        self.assertIn("--probe-bluetooth", buds["reason"])
        for field in ("battery", "anc"):
            with self.subTest(field=field):
                self.assertEqual(buds["state"][field]["kind"], "unavailable")
                self.assertTrue(buds["state"][field]["reason"])

    def test_unpaired_buds_are_nothing_present_not_not_installed(self):
        """Three fixes, three statuses. This is the distinction the field exists for."""
        stubs = {
            "pbpctrl": "#!/bin/sh\n",
            "bluetoothctl": "#!/bin/sh\nexit 0\n",
        }
        data, _ = self.json_status(stubs=stubs)
        self.assertEqual(data["capabilities"]["buds"]["status"], "nothing_present")

    # --- degraded machines --------------------------------------------------

    def everything_working(self) -> dict[str, str]:
        return {
            "rquickshare": "#!/bin/sh\n",
            "pgrep": "#!/bin/sh\nexit 0\n",
            "kdeconnect-cli": "#!/bin/sh\necho abcd1234\n",
            "pbpctrl": "#!/bin/sh\n",
        }

    def test_installed_but_not_running_is_no_answer(self):
        data, _ = self.json_status(stubs={"rquickshare": "#!/bin/sh\n"})
        transfer = data["capabilities"]["file-transfer"]
        self.assertEqual(transfer["status"], "no_answer")
        self.assertIn("not running", transfer["reason"])
        self.assertEqual(transfer["provider"], "r-quick-share 0.11.5-5")

    def test_running_transfer_is_ready(self):
        stubs = {"rquickshare": "#!/bin/sh\n", "pgrep": "#!/bin/sh\nexit 0\n"}
        data, _ = self.json_status(stubs=stubs)
        transfer = data["capabilities"]["file-transfer"]
        self.assertEqual(transfer["status"], "ready")
        self.assertTrue(transfer["available"])
        self.assertIsNone(transfer["reason"])

    def test_no_port_is_published(self):
        """Measured: the port changes on every launch. A consumer must not cache it."""
        stubs = {"rquickshare": "#!/bin/sh\n", "pgrep": "#!/bin/sh\nexit 0\n"}
        data, _ = self.json_status(stubs=stubs)
        self.assertNotIn("port", json.dumps(data["capabilities"]["file-transfer"]))

    def test_daemon_that_does_not_answer_is_distinguished_from_absent(self):
        stubs = {"kdeconnect-cli": "#!/bin/sh\nexit 1\n"}
        data, _ = self.json_status(stubs=stubs)
        link = data["capabilities"]["phone-link"]
        self.assertEqual(link["status"], "no_answer")
        self.assertIn("daemon", link["reason"])

    def test_paired_phone_is_ready(self):
        stubs = {"kdeconnect-cli": "#!/bin/sh\necho abcd1234\n"}
        data, _ = self.json_status(stubs=stubs)
        link = data["capabilities"]["phone-link"]
        self.assertEqual(link["status"], "ready")
        self.assertEqual(link["state"]["devices"], ["abcd1234"])

    def test_hosts_without_hyprland_or_pacman_still_produce_json(self):
        """The product must not assume Omarchy, Hyprland or Arch.

        docs/05-packaging.md is explicit about this, so the empty-host case is
        a contract test rather than a curiosity.
        """
        with tempfile.TemporaryDirectory(prefix="omapixel-bare-") as tmp:
            sandbox = Path(tmp)
            write_sandbox(sandbox, {})  # coreutils only: no ip, no pacman, no hyprctl
            result = subprocess.run(
                [INTERPRETER, str(STATUS), "--json"],
                capture_output=True, text=True, timeout=60,
                env=sandbox_env(sandbox, XDG_CURRENT_DESKTOP=""),
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIsNone(data["host"]["subnet"])
        self.assertEqual(data["capabilities"]["buds"]["status"], "not_installed")

    def test_help_does_not_probe_anything(self):
        result, invocations = self.run_status("--help")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(invocations, [], f"--help ran commands: {invocations}")


class StatusScriptHygiene(unittest.TestCase):
    def test_script_is_executable(self):
        import os

        self.assertTrue(os.access(STATUS, os.X_OK))

    def test_it_compiles(self):
        # compile() rather than py_compile: the latter writes scripts/__pycache__
        # into a directory that belongs to development.
        source = STATUS.read_text()
        try:
            compile(source, str(STATUS), "exec")
        except SyntaxError as exc:
            self.fail(f"{STATUS.name} does not compile: {exc}")

    def test_the_contract_document_exists_and_names_the_statuses(self):
        """The document and the code have to agree on the vocabulary."""
        from tests.support import DOCS

        contract = DOCS / "08-status-contract.md"
        if not contract.exists():
            self.skipTest("docs/08-status-contract.md does not exist")
        text = contract.read_text()
        for status in sorted(STATUSES):
            with self.subTest(status=status):
                self.assertIn(status, text)


if __name__ == "__main__":
    unittest.main()
