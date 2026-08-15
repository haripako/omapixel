"""scripts/hw-report.sh: the contract, the privacy rule, and what it must never do.

The script is run against **stubbed commands**, not against this machine. A
stub directory takes over PATH, so `ip`, `bluetoothctl`, `lsusb`, `pacman` and
`hyprctl` return fixed output. Two reasons, and the second is the important one:

  * the output becomes deterministic, so the privacy assertions can use a MAC
    address and a host IP that are known to be in the input. Testing redaction
    on a machine that happens to have nothing to redact proves nothing.
  * nothing here touches the Bluetooth stack. Development reproduced 3 of 3 on
    2026-08-15 that talking to that subsystem on this adapter can take
    bluetoothd down and with it the user's mouse. A suite meant to run
    continuously must not be able to do that.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from tests.support import ROOT, SCRIPTS, privacy_violations

SCRIPT = SCRIPTS / "hw-report.sh"
# Resolved before PATH is replaced: the sandbox has no bash of its own.
BASH = shutil.which("bash") or "/bin/bash"

# Values that must never reach --markdown or --toml output.
HOST_MAC = "AA:BB:CC:DD:EE:FF"
HOST_IP = "[ip redacted]"
EXPECTED_SUBNET = "192.168.10.0/24"

STUBS = {
    "ip": f"""#!/bin/sh
case "$*" in
  *"-o addr show scope global"*)
    echo "2: eno1    inet {HOST_IP}/24 brd 192.168.10.255 scope global eno1"
    echo "4: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0"
    ;;
  *"-o link show"*)
    echo "2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500"
    echo "3: wlp11s0: <BROADCAST,MULTICAST> mtu 1500"
    ;;
  *"addr show wlp11s0"*) ;;
esac
""",
    # Read-only verbs only. If the script ever grows a `connect`, the stub says so.
    "bluetoothctl": f"""#!/bin/sh
case "$1" in
  show)    echo "Controller {HOST_MAC} (public)" ;;
  devices) echo "Device 11:22:33:44:55:66 Pixel 7 Pro" ;;
  *)       echo "STUB REFUSED: bluetoothctl $*" >&2; exit 90 ;;
esac
""",
    "lsusb": """#!/bin/sh
echo "Bus 001 Device 003: ID 0e8d:0608 MediaTek Inc. Wireless_Device"
echo "Bus 003 Device 007: ID 18d1:4ee2 Google Inc. Pixel 7 Pro"
""",
    "pacman": """#!/bin/sh
[ "$1" = "-Q" ] && echo "bluez 5.87"
""",
    "hyprctl": """#!/bin/sh
echo "Hyprland 0.56.2 built from branch main"
""",
}


# The script needs these to run at all. Everything else it calls is stubbed or
# absent, so the sandbox PATH decides exactly which tools count as installed —
# on this machine several of them really are, and a test that depended on that
# would pass here and fail on a fresh checkout.
COREUTILS = ("awk", "sed", "cat", "grep", "head", "paste", "uname", "tr")


def _write_stubs(directory: Path, extra: dict[str, str] | None = None) -> None:
    for name, body in {**STUBS, **(extra or {})}.items():
        path = directory / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    for name in COREUTILS:
        for prefix in ("/usr/bin", "/bin"):
            source = Path(prefix) / name
            if source.exists():
                (directory / name).symlink_to(source)
                break


class HwReport(unittest.TestCase):
    def run_script(self, *args: str, stubs: dict[str, str] | None = None):
        with tempfile.TemporaryDirectory(prefix="omapixel-stub-") as tmp:
            stub_dir = Path(tmp)
            _write_stubs(stub_dir, stubs)
            env = dict(os.environ)
            # PATH is the stub directory and nothing else. Not shadowing: total
            # replacement. If a stub does not cover a command the script calls,
            # the command is simply not found — it never falls through to the
            # real binary, which for `bluetoothctl` is the difference between a
            # test and an incident.
            env["PATH"] = str(stub_dir)
            env["LC_ALL"] = "C"  # localised output has already cost this project once
            return subprocess.run(
                [BASH, str(SCRIPT), *args],
                capture_output=True, text=True, env=env, timeout=60,
            )

    # --- interface ----------------------------------------------------------

    def test_syntax_is_valid(self):
        result = subprocess.run([BASH, "-n", str(SCRIPT)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_is_executable(self):
        self.assertTrue(os.access(SCRIPT, os.X_OK), f"{SCRIPT} is not executable")

    def test_help_lists_every_mode(self):
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0)
        for mode in ("--markdown", "--toml"):
            self.assertIn(mode, result.stdout)
        self.assertNotIn("#", result.stdout, "comment markers leaked into --help")

    def test_unknown_option_fails_loudly(self):
        result = self.run_script("--nonsense")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_human_mode_runs_clean(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-- Tools --", result.stdout)
        self.assertIn("-- Environment --", result.stdout)

    def test_missing_tools_are_reported_as_commands_to_run_not_run(self):
        """The install line is printed. Nothing installs anything, ever.

        Deterministic because the sandbox PATH contains none of the six tools,
        whatever this machine happens to have installed.
        """
        result = self.run_script()
        self.assertIn("sudo pacman -S", result.stdout)
        self.assertIn("yay -S", result.stdout)
        self.assertIn("pbpctrl had not been updated", result.stdout,
                      "the AUR staleness warning went missing")

    def test_nothing_to_install_is_said_plainly(self):
        present = {name: "#!/bin/sh\n" for name in
                   ("rquickshare", "kdeconnect-cli", "wl-copy", "pbpctrl",
                    "adb", "scrcpy")}
        result = self.run_script(stubs=present)
        self.assertIn("Nothing left to install.", result.stdout)
        self.assertNotIn("sudo pacman -S", result.stdout)

    def test_present_tools_are_detected(self):
        result = self.run_script("--markdown", stubs={"adb": "#!/bin/sh\n"})
        self.assertIn("| `android-tools` | installed |", result.stdout)
        self.assertIn("| `pbpctrl` | not installed |", result.stdout)

    def test_the_sandbox_is_hermetic(self):
        """Guards the test harness, not the script.

        If PATH ever leaks the real system directories, these tests would call
        the real bluetoothctl on a machine where that has taken bluetoothd down
        three times out of three. The stub refuses any verb but `show` and
        `devices`, and this proves the stub is the one being reached.
        """
        probe = {"probe": "#!/bin/sh\ncommand -v bluetoothctl\n"}
        with tempfile.TemporaryDirectory(prefix="omapixel-stub-") as tmp:
            stub_dir = Path(tmp)
            _write_stubs(stub_dir, probe)
            env = dict(os.environ, PATH=str(stub_dir), LC_ALL="C")
            result = subprocess.run([BASH, str(stub_dir / "probe")],
                                    capture_output=True, text=True, env=env)
            self.assertEqual(result.stdout.strip(), str(stub_dir / "bluetoothctl"))

    def test_the_bluetooth_stub_refuses_anything_but_reading(self):
        """The stub is the tripwire: a state-changing verb fails, loudly."""
        with tempfile.TemporaryDirectory(prefix="omapixel-stub-") as tmp:
            stub_dir = Path(tmp)
            _write_stubs(stub_dir)
            env = dict(os.environ, PATH=str(stub_dir), LC_ALL="C")
            result = subprocess.run(
                [str(stub_dir / "bluetoothctl"), "connect", "AA:BB:CC:DD:EE:FF"],
                capture_output=True, text=True, env=env,
            )
        self.assertEqual(result.returncode, 90)
        self.assertIn("STUB REFUSED", result.stderr)

    # --- privacy ------------------------------------------------------------

    def test_markdown_redacts_the_mac_and_the_host_ip(self):
        """The published block. The stubs feed it both; neither may come out."""
        result = self.run_script("--markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(HOST_MAC, result.stdout)
        self.assertNotIn(HOST_IP, result.stdout)
        self.assertEqual(privacy_violations(result.stdout), [])

    def test_markdown_keeps_the_subnet_because_that_is_the_useful_fact(self):
        result = self.run_script("--markdown")
        self.assertIn(EXPECTED_SUBNET, result.stdout)

    def test_markdown_keeps_the_adapter_model(self):
        """Model, not MAC: it identifies the hardware without the machine."""
        self.assertIn("MediaTek", self.run_script("--markdown").stdout)

    def test_toml_output_parses_and_is_clean(self):
        result = self.run_script("--toml")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = tomllib.loads(result.stdout)
        self.assertIn("host", parsed)
        for field in ("distro", "desktop", "kernel", "bluez", "bt_adapter"):
            self.assertIn(field, parsed["host"])
        self.assertEqual(privacy_violations(result.stdout), [])

    def test_toml_host_section_matches_the_report_template(self):
        """Paste-ready means the fields line up with data/report-template.toml."""
        from tests.support import DATA

        with (DATA / "report-template.toml").open("rb") as fh:
            template = tomllib.load(fh)
        produced = tomllib.loads(self.run_script("--toml").stdout)
        self.assertEqual(
            set(produced["host"]), set(template["host"]),
            "hw-report.sh --toml and the [host] template have drifted apart",
        )

    def test_virtual_interfaces_are_left_out(self):
        """docker0 is not a fact about the user's network."""
        self.assertNotIn("172.17", self.run_script("--markdown").stdout)


class ScriptsNeverActOnTheSystem(unittest.TestCase):
    """Static contract over every shell script. Grep, not execution."""

    def scripts(self) -> list[Path]:
        found = sorted(SCRIPTS.glob("*.sh"))
        self.assertTrue(found, "no shell scripts found under scripts/")
        return found

    def code_lines(self, path: Path):
        """Lines that could run, with comments and printed text stripped out."""
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            if re.match(r"^\s*(echo|printf)\b", stripped):
                continue
            yield number, line

    def test_no_script_installs_anything(self):
        pattern = re.compile(
            r"\b(sudo\s+pacman|yay|pacman\s+-S|apt(-get)?\s+install|pip\s+install)\b"
        )
        for path in self.scripts():
            for number, line in self.code_lines(path):
                self.assertIsNone(
                    pattern.search(line),
                    f"{path.name}:{number} runs a package manager. Print it instead:"
                    f"\n  {line.strip()}",
                )

    def test_no_script_changes_bluetooth_state(self):
        """Read the adapter, never drive it.

        Measured on this machine: driving the Bluetooth stack can take
        bluetoothd down by SIGSEGV and leave the user without a mouse for
        fifteen seconds or, if the HID profile does not reattach, indefinitely.
        A reporting script has no business doing that, and neither has a test.
        """
        pattern = re.compile(
            r"\b(bluetoothctl\s+(connect|disconnect|pair|remove|power|scan|trust)"
            r"|rfkill\s+(block|unblock)"
            r"|systemctl\s+(start|stop|restart)\s+bluetooth)\b"
        )
        for path in self.scripts():
            for number, line in self.code_lines(path):
                self.assertIsNone(
                    pattern.search(line),
                    f"{path.name}:{number} changes Bluetooth state:\n  {line.strip()}",
                )

    def test_no_script_calls_a_hardware_tool_by_absolute_path(self):
        """The lock that keeps the sandbox argument true.

        Replacing PATH protects against PATH lookups and nothing else. A script
        that called /usr/bin/bluetoothctl directly would walk straight through
        every stub in this suite. No script does today; this is what makes that
        still true in six months.
        """
        pattern = re.compile(
            r"(/usr)?/s?bin/(bluetoothctl|rquickshare|pbpctrl|kdeconnect-cli"
            r"|scrcpy|rfkill|btmgmt|hcitool)\b"
        )
        for path in self.scripts():
            for number, line in self.code_lines(path):
                self.assertIsNone(
                    pattern.search(line),
                    f"{path.name}:{number} calls a hardware tool by absolute path, "
                    f"which no test sandbox can intercept:\n  {line.strip()}",
                )

    def test_no_script_launches_the_integration_tools(self):
        """`command -v rquickshare` is a check. `rquickshare` is an incident.

        Starting rquickshare is reproducibly fatal to bluetoothd here, 3 of 3
        on 2026-08-15. Detection must stay detection.
        """
        binaries = ("rquickshare", "pbpctrl", "kdeconnect-cli", "scrcpy")
        for path in self.scripts():
            for number, line in self.code_lines(path):
                for binary in binaries:
                    if binary not in line:
                        continue
                    self.assertRegex(
                        line,
                        rf"(command -v|check\s+{binary}|tool_line\s+{binary}|#)",
                        f"{path.name}:{number} appears to run {binary}:"
                        f"\n  {line.strip()}",
                    )


class NothingSpeaksBluetoothInProcess(unittest.TestCase):
    """The half the invocation log cannot see.

    The sandbox records processes, so it catches `bluetoothctl`, `btmgmt` and
    `hcitool`. It is blind to a program that opens an AF_BLUETOOTH socket or
    talks to org.bluez over D-Bus without executing anything — which is exactly
    how a Python emulator would do it. Raised by code review on 2026-08-15.

    This is a static check over every program in the repository, so it holds
    for code the suite has never run, including anything that lands in
    tools/virtual-pixel/. It cannot prove a running process stays off the
    stack: that measurement belongs to backend and is the gate before any test
    drives the emulator.
    """

    FORBIDDEN = re.compile(
        r"AF_BLUETOOTH|BTPROTO_|org\.bluez"
        r"|import\s+bluetooth\b|from\s+bluetooth\s+import|pybluez|bleak|dbus_next"
    )

    def programs(self) -> list[Path]:
        roots = [ROOT / "scripts", ROOT / "tools"]
        found: list[Path] = []
        for root in roots:
            if not root.is_dir():
                continue
            found += [p for p in sorted(root.rglob("*"))
                      if p.is_file() and p.suffix in ("", ".py", ".sh")
                      and "__pycache__" not in p.parts]
        return found

    @staticmethod
    def code_only(text: str) -> dict[int, str]:
        """Executable code by line, with comments and string literals removed.

        Necessary rather than fastidious. The virtual Pixel contains a
        self-audit that checks it is holding no AF_BLUETOOTH socket, and it
        names the thing it is refusing to do — in prose and in a string. A
        checker that cannot tell "opens a Bluetooth socket" from "verifies it
        opened none" would punish exactly the code doing the right thing.

        Consequence worth stating: a reference built out of string literals
        would slip past. Same posture as the privacy detector — this catches
        accidents, not somebody determined to hide one.
        """
        import io
        import tokenize

        # Python 3.12 splits f-strings into FSTRING_START/MIDDLE/END instead of
        # one STRING token, so the literal text inside them has to be skipped by
        # name. Without this, a message *describing* a Bluetooth socket reads
        # like one being opened.
        skip = {tokenize.COMMENT, tokenize.STRING} | {
            getattr(tokenize, name)
            for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END")
            if hasattr(tokenize, name)
        }

        lines: dict[int, list[str]] = {}
        try:
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type in skip:
                    continue
                lines.setdefault(token.start[0], []).append(token.string)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            # Not Python, or not valid Python. Fall back to stripping comments.
            return {
                number: line
                for number, line in enumerate(text.splitlines(), start=1)
                if not line.strip().startswith("#")
            }
        return {number: " ".join(parts) for number, parts in lines.items()}

    def test_no_program_opens_bluetooth_itself(self):
        for path in self.programs():
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue  # a binary; not something this check can reason about
            for number, line in self.code_only(text).items():
                with self.subTest(file=path.name, line=number):
                    self.assertIsNone(
                        self.FORBIDDEN.search(line),
                        f"{path.relative_to(ROOT)}:{number} talks to the Bluetooth "
                        f"stack in-process, which no PATH sandbox can intercept:"
                        f"\n  {line.strip()}",
                    )

    def test_the_check_still_catches_a_real_use(self):
        """Positive control: stripping strings must not strip the invariant."""
        real = "import socket\ns = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW)\n"
        hits = [n for n, line in self.code_only(real).items()
                if self.FORBIDDEN.search(line)]
        self.assertTrue(hits, "the check no longer detects an AF_BLUETOOTH socket")

    def test_the_check_tolerates_an_audit_that_names_what_it_refuses(self):
        audit = (
            'import socket\n'
            '# 2. The AF_BLUETOOTH constant must not be reachable.\n'
            'family = getattr(socket, "AF_BLUETOOTH", None)\n'
        )
        hits = [n for n, line in self.code_only(audit).items()
                if self.FORBIDDEN.search(line)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
