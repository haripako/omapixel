"""tools/virtual-pixel/: the simulated Quick Share peer, driven from tests.

The emulator belongs to backend. These tests drive it and never edit it.

**Why running it is allowed at all**, when nothing else in this suite starts a
program that talks to hardware: backend measured the gate on 2026-08-15 and
published it — self-check clean; and from outside, bluetoothd on the same pid,
the segfault count unchanged, the mouse still connected, one line in the
bluetooth journal, and no Bluetooth file descriptors in the process. That is
observable effect, not a promise, which is the only kind of clearance this
project accepts.

Two harness rules follow from it:

  * every run happens under a replaced PATH, so `avahi-publish-service` is a
    stub. **The suite never publishes anything on Hari's LAN**, and the stub
    records its own arguments, which is how the TXT record gets asserted.
  * the invocation log is checked for Bluetooth binaries after every run, so
    the claim "it did not touch Bluetooth" is re-measured per test rather than
    inherited from the gate.

And the rule that outlives all of it: **nothing green here is a measurement.**
A pass is "measured against the emulator", never "measured", and closes no F1
box. Neither is a red one — a failure the emulator produces is also only a fact
about the emulator, and that half gets forgotten first, because an error is
more convincing than a win.
"""

from __future__ import annotations

import importlib.util
import re
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import ROOT, privacy_violations, sandbox_env, write_sandbox

PEER = ROOT / "tools" / "virtual-pixel" / "virtual-pixel.py"
INTERPRETER = sys.executable
MARK = "virtual-pixel[simulated]"

# Records its arguments and then blocks, the way the real one stays alive for as
# long as the advertisement should exist.
AVAHI_STUB = """#!/bin/sh
sleep 300
"""

BLUETOOTH_BINARIES = ("bluetoothctl", "btmgmt", "hcitool", "bluetoothd", "btmon")


def read_invocations(log: Path, *, settle: float = 2.0) -> list[str]:
    """The stub log, after giving a just-terminated stub time to have written.

    Measured while writing these tests: the emulator withdraws its
    advertisement by terminating the publisher, and it can do that before the
    shell has been scheduled to run the log line at all. Reading immediately
    then shows "never advertised", which is a race dressed as a finding.

    An empty result after the settle window is a real absence, which is what
    the `absent` mode test relies on.
    """
    import time

    deadline = time.monotonic() + settle
    while time.monotonic() < deadline:
        if log.exists() and log.read_text().strip():
            break
        time.sleep(0.05)
    return log.read_text().splitlines() if log.exists() else []


def load_peer():
    """Import the emulator as a module, to unit-test its audit directly."""
    spec = importlib.util.spec_from_file_location("virtual_pixel", PEER)
    module = importlib.util.module_from_spec(spec)
    previously = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previously
    return module


def compile_error() -> str | None:
    """Whatever stops the emulator compiling, or None."""
    if not PEER.exists():
        return "tools/virtual-pixel/virtual-pixel.py is absent"
    try:
        compile(PEER.read_text(), str(PEER), "exec")
    except SyntaxError as exc:
        return f"{PEER.name} does not compile: line {exc.lineno}: {exc.msg}"
    return None


class EmulatorIsRunnable(unittest.TestCase):
    """One red line instead of twenty when the emulator is mid-edit.

    Four agents write to this tree at once and the emulator belongs to backend.
    A half-saved file used to fail every test that drives it, which reads like
    twenty findings about the transfer path and is really one fact about a file
    someone is still typing. This is that one fact; the rest skip.
    """

    def test_the_emulator_compiles(self):
        problem = compile_error()
        if problem and "is absent" in problem:
            self.skipTest(problem)
        self.assertIsNone(problem)


@unittest.skipIf(compile_error(), compile_error() or "")
class VirtualPeer(unittest.TestCase):
    maxDiff = None

    def run_peer(self, *args: str, timeout: int = 20):
        """Run the peer to completion in a sandbox. Returns (result, invocations)."""
        with tempfile.TemporaryDirectory(prefix="omapixel-peer-") as tmp:
            sandbox = Path(tmp)
            log = sandbox / "invocations.log"
            write_sandbox(sandbox, {"avahi-publish-service": AVAHI_STUB}, log=log)
            result = subprocess.run(
                [INTERPRETER, str(PEER), *args],
                capture_output=True, text=True, timeout=timeout,
                env=sandbox_env(sandbox),
            )
            # No settle window here: these subcommands run nothing, and waiting
            # two seconds to confirm an emptiness would just be slow.
            invocations = log.read_text().splitlines() if log.exists() else []
        return result, invocations

    def transfer(self, mode: str, *, read_timeout: float = 5.0):
        """Start the peer in `mode`, connect once, and collect everything.

        Returns (reply_bytes, output_lines, invocations). The peer is always
        stopped, including when the mode is one that never answers.
        """
        with tempfile.TemporaryDirectory(prefix="omapixel-peer-") as tmp:
            sandbox = Path(tmp)
            log = sandbox / "invocations.log"
            write_sandbox(sandbox, {"avahi-publish-service": AVAHI_STUB}, log=log)

            process = subprocess.Popen(
                [INTERPRETER, str(PEER), "--once", "--mode", mode],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env=sandbox_env(sandbox),
            )
            reply = b""
            lines: list[str] = []
            try:
                port = None
                for line in process.stdout:
                    lines.append(line.rstrip("\n"))
                    if "listening" in line and "tcp/" in line:
                        # The line carries more than the port now ("tcp/34391,
                        # loopback only"), so take the digits rather than the
                        # first whitespace-separated field.
                        port = int(re.search(r"tcp/(\d+)", line).group(1))
                    if " ready" in line:
                        break
                self.assertIsNotNone(port, "the peer never said which port it took")

                with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                    client.settimeout(read_timeout)
                    try:
                        reply = client.recv(4096)
                    except TimeoutError:
                        reply = b""
            finally:
                process.terminate()
                try:
                    rest, _ = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    rest, _ = process.communicate()
                lines += [line for line in rest.splitlines() if line]
            invocations = read_invocations(log)
        return reply, lines, invocations

    # --- rule 1: it never touches Bluetooth ---------------------------------

    def test_self_check_passes(self):
        result, _ = self.run_peer("--self-check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("self-check passed", result.stdout)

    def test_self_check_names_the_binaries_it_never_ran(self):
        result, invocations = self.run_peer("--self-check")
        for binary in BLUETOOTH_BINARIES:
            self.assertIn(binary, result.stdout)
        self.assertEqual(invocations, [], f"the self-check ran something: {invocations}")

    def test_the_audit_can_actually_fail(self):
        """An audit nobody has seen fail is a hypothesis, not a guarantee.

        Exercised without going anywhere near the adapter: the audit flags any
        file descriptor whose target mentions bluetooth, so it is given a plain
        file called `bluetooth` to hold. No socket, no adapter, no daemon — and
        the detector that rule 1 depends on is shown to fire.
        """
        peer = load_peer()
        with tempfile.TemporaryDirectory(prefix="omapixel-audit-") as tmp:
            decoy = Path(tmp) / "bluetooth"
            decoy.write_text("not a socket\n")
            with decoy.open() as handle:
                self.assertGreaterEqual(handle.fileno(), 0)
                problems = peer.bluetooth_audit()
        self.assertTrue(
            problems, "bluetooth_audit() saw nothing while holding a bluetooth fd"
        )

    def test_no_run_ever_executes_a_bluetooth_binary(self):
        """Re-measured per mode, not inherited from the gate."""
        for mode in ("none", "reject", "absent"):
            with self.subTest(mode=mode):
                _, _, invocations = self.transfer(mode)
                ran = {line.split()[0] for line in invocations if line.strip()}
                self.assertEqual(ran & set(BLUETOOTH_BINARIES), set())

    # --- rule 4: it declares its limits, in the tool ------------------------

    def test_limits_say_the_f1_flakiness_box_can_never_be_closed_here(self):
        """The most important sentence the emulator prints.

        Discovery flakiness lives in Android's radio management. This peer
        advertises continuously, so it cannot reproduce it — structurally, not
        yet. A green transfer here is not evidence for that box, and the tool
        says so itself rather than leaving it in a document nobody opens.
        """
        result, invocations = self.run_peer("--limits")
        self.assertEqual(result.returncode, 0)
        self.assertIn("CAN NEVER VALIDATE", result.stdout)
        self.assertIn("structurally never", result.stdout)
        self.assertIn("may be written as measured", result.stdout)
        self.assertEqual(invocations, [], "--limits is not supposed to run anything")

    def test_limits_are_printed_on_every_run_not_only_on_request(self):
        _, lines, _ = self.transfer("none")
        self.assertTrue(
            any("CAN NEVER VALIDATE" in line for line in lines),
            "a run that never states its limits leaves them to be rediscovered",
        )

    # --- rule 3: everything is marked ---------------------------------------

    def test_every_line_carries_the_simulated_mark(self):
        """It has to survive a screenshot pasted into an issue.

        Checked on the error paths too, since those are the lines that get
        photographed and the ones a happy-path test never sees.
        """
        for mode in ("none", "reject", "drop"):
            with self.subTest(mode=mode):
                _, lines, _ = self.transfer(mode)
                unmarked = [line for line in lines if line.strip() and MARK not in line]
                self.assertEqual(unmarked, [], f"unmarked output: {unmarked}")

    def test_the_mark_is_on_the_help_and_the_audit_too(self):
        for flag in ("--limits", "--self-check"):
            with self.subTest(flag=flag):
                result, _ = self.run_peer(flag)
                unmarked = [line for line in result.stdout.splitlines()
                            if line.strip() and MARK not in line]
                self.assertEqual(unmarked, [])

    # --- the modes ----------------------------------------------------------

    def test_none_accepts(self):
        reply, lines, _ = self.transfer("none")
        self.assertIn(b"ACCEPTED", reply)
        self.assertIn(b"no data was stored", reply)
        self.assertTrue(any("accepted" in line for line in lines))

    def test_reject_is_a_decision_not_a_breakage(self):
        """Rejected and failed must never collapse into each other.

        Rejected is the other end deciding; failed is something breaking. A
        surface that shows one for the other sends the user to fix the wrong
        thing — the same class of error as reporting a dead daemon as "nothing
        paired".
        """
        reply, lines, _ = self.transfer("reject")
        self.assertIn(b"REJECTED", reply)
        self.assertNotIn(b"ACCEPTED", reply)
        self.assertTrue(any("rejected" in line for line in lines))
        self.assertFalse(any("failed" in line for line in lines))

    def test_drop_accepts_and_then_fails(self):
        reply, lines, _ = self.transfer("drop")
        self.assertIn(b"ACCEPTED", reply)
        self.assertTrue(any("failed" in line for line in lines),
                        "a transfer that died mid-way said nothing about it")

    def test_timeout_answers_nothing_and_says_it_is_hanging(self):
        reply, lines, _ = self.transfer("timeout", read_timeout=1.5)
        self.assertEqual(reply, b"")
        self.assertTrue(any("hanging" in line for line in lines))

    def test_absent_never_advertises_but_still_listens(self):
        reply, lines, invocations = self.transfer("absent")
        self.assertIn(b"ACCEPTED", reply)
        self.assertTrue(any("not advertising" in line for line in lines))
        self.assertNotIn("avahi-publish-service",
                         {line.split()[0] for line in invocations if line.strip()})

    def test_vanish_withdraws_the_advertisement(self):
        """Only the state change is asserted, not the publisher.

        On a loopback run there is no advertisement to withdraw, and forcing
        --lan just to observe the withdrawal would trade a real network
        listener for a log line.
        """
        _, lines, _ = self.transfer("vanish")
        self.assertTrue(any("vanishing" in line for line in lines))

    def test_an_unknown_mode_is_refused(self):
        result, _ = self.run_peer("--mode", "explode", "--once")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)

    # --- the advertisement --------------------------------------------------

    def test_the_advertisement_declares_itself_simulated(self):
        """Anything discovering this peer learns it is fake without being told.

        Driven through the Advertisement object rather than through a --lan
        run, deliberately: asserting the TXT record must not require binding
        0.0.0.0 on the machine of whoever runs this suite. No socket is opened
        here at all — only the stubbed publisher, which records its arguments.
        """
        peer = load_peer()
        with tempfile.TemporaryDirectory(prefix="omapixel-adv-") as tmp:
            sandbox = Path(tmp)
            log = sandbox / "invocations.log"
            write_sandbox(sandbox, {"avahi-publish-service": AVAHI_STUB}, log=log)

            import os

            # Both, and the second one is the one that matters. shutil.which()
            # reads os.environ, but Popen resolves the program name through the
            # env it is *given*, and the emulator captured ENV at import time —
            # with the real PATH. Overriding only os.environ made this test run
            # /usr/bin/avahi-publish-service and publish a real mDNS record on
            # the LAN. Measured, not theorised: it happened here on 2026-08-15.
            saved_path = os.environ["PATH"]
            saved_env = peer.ENV
            os.environ["PATH"] = str(sandbox)
            peer.ENV = {**peer.ENV, "PATH": str(sandbox)}
            try:
                advert = peer.Advertisement("Virtual Pixel (simulated)", 41617)
                self.assertTrue(advert.start(), "the publisher was not started")
                # Read before stopping: stop() kills the publisher, and it can
                # die before the shell has run its first line. Same race as in
                # read_invocations(), from the other side.
                invocations = read_invocations(log)
            finally:
                advert.stop()
                os.environ["PATH"] = saved_path
                peer.ENV = saved_env

        published = [line for line in invocations
                     if line.startswith("avahi-publish-service")]
        self.assertTrue(published, "nothing was advertised")
        self.assertIn("simulated=true", published[0])
        self.assertIn("_FC9F5ED42C8A._tcp", published[0])

    def test_by_default_it_never_listens_on_the_lan(self):
        """The network-surface rule, measured rather than read off a log line.

        Rule 1 says no Bluetooth; it says nothing about what the peer binds,
        and a listener on 0.0.0.0 is new surface on Hari's network and on the
        network of anybody running this suite. Checked by effect: while the
        peer is up, this test binds the same port on the machine's own LAN
        address. That only succeeds if the peer did not take all interfaces.
        """
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("192.0.2.1", 9))  # documentation net: no packet is sent
            lan_address = probe.getsockname()[0]
        except OSError:
            self.skipTest("no routable address to test against")
        finally:
            probe.close()
        if lan_address.startswith("127."):
            self.skipTest("this machine has only loopback")

        with tempfile.TemporaryDirectory(prefix="omapixel-bind-") as tmp:
            sandbox = Path(tmp)
            write_sandbox(sandbox, {"avahi-publish-service": AVAHI_STUB},
                          log=sandbox / "invocations.log")
            process = subprocess.Popen(
                [INTERPRETER, str(PEER), "--once"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env=sandbox_env(sandbox),
            )
            try:
                port = None
                for line in process.stdout:
                    if "listening" in line and "tcp/" in line:
                        port = int(re.search(r"tcp/(\d+)", line).group(1))
                    if " ready" in line:
                        break
                self.assertIsNotNone(port)

                mine = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    mine.bind((lan_address, port))
                except OSError as exc:
                    self.fail(
                        f"port {port} was already taken on {lan_address}: the peer "
                        f"bound all interfaces without --lan ({exc})"
                    )
                finally:
                    mine.close()
            finally:
                process.terminate()
                process.communicate(timeout=10)

    def test_a_loopback_run_publishes_nothing(self):
        """Bind and advertisement are one decision, not two.

        Advertising a loopback endpoint over mDNS would publish something
        nobody can reach, and would put a record on the network anyway.
        """
        _, lines, invocations = self.transfer("none")
        self.assertTrue(any("not advertising" in line for line in lines))
        self.assertEqual(
            [line for line in invocations if line.startswith("avahi-publish-service")],
            [], "a loopback run published an mDNS record",
        )

    # --- privacy ------------------------------------------------------------

    def test_the_output_never_carries_an_address(self):
        """Same rule as everywhere: this output gets pasted into issues.

        The peer logs the port it was connected from and never the address.
        """
        _, lines, _ = self.transfer("none")
        self.assertEqual(privacy_violations("\n".join(lines)), [])


if __name__ == "__main__":
    unittest.main()
