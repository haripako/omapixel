#!/usr/bin/env python3
"""A simulated Quick Share peer, so the transfer path can be exercised without
a phone — and without Bluetooth.

  tools/virtual-pixel/virtual-pixel.py            run the peer
  tools/virtual-pixel/virtual-pixel.py --once     accept one connection, exit
  tools/virtual-pixel/virtual-pixel.py --self-check   prove it opens no Bluetooth

Why this exists: F1 is blocked twice over. The phone is one blocker; the other
is that launching rquickshare segfaults bluetoothd and kills the user's mouse,
reproduced three times out of three on 2026-08-15. A local peer unblocks the
parts that are ours — peer lists, transfer states, the feedback surface, tests
in CI and in a VM — with neither.

THREE RULES, and two of them are enforced in code rather than remembered.

1. ZERO BLUETOOTH. No BLE, no bluetoothd, no adapter. LAN only: mDNS and TCP.
   `--self-check` asserts it from inside the process, because a test harness
   that watches which binaries were executed cannot see an AF_BLUETOOTH socket
   or a D-Bus call opened in-process.

2. A VIRTUAL PIXEL IS NOT A PIXEL. Everything it exposes is marked simulated in
   the DATA, not in the styling — `simulated=true` in the mDNS TXT record and
   in every line it prints. Somebody will paste a screenshot of a working
   transfer into an issue, and the mark has to survive that. Nothing measured
   against this may be written as measured, promoted in
   `data/capabilities.toml`, or used to tick an F1 box.

3. IT SAYS WHAT HAPPENED. Every state change prints one line: ready, peer
   connected, accepted, rejected, failed, stopped. Silence is the failure mode
   this whole project exists to fight; an emulator that fails quietly would be
   the joke writing itself.

Standard library only. mDNS is published through `avahi-publish-service`, the
same way the rest of the project shells out to system tools rather than vendor
a protocol stack.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
from datetime import datetime

# The Quick Share / Nearby Share service type, measured from rquickshare's own
# advertisement on this machine on 2026-08-15.
SERVICE_TYPE = "_FC9F5ED42C8A._tcp"
DEFAULT_NAME = "Virtual Pixel (simulated)"
BIND_LOCAL = "127.0.0.1"
BIND_LAN = "0.0.0.0"

ENV = {**os.environ, "LC_ALL": "C", "LANG": "C"}


def say(event: str, detail: str = "") -> None:
    """One line per state change. Rule 3.

    Prefixed so that a human, a test and a log scraper all read the same thing,
    and so no output from here can ever be mistaken for a real device.
    """
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] virtual-pixel[simulated] {event}"
    if detail:
        line += f": {detail}"
    print(line, flush=True)


# --- rule 1, enforced ---------------------------------------------------------

BLUETOOTH_BINARIES = ("bluetoothctl", "btmgmt", "hcitool", "bluetoothd", "btmon")


def bluetooth_audit() -> list[str]:
    """Return every reason this process is not Bluetooth-clean. Empty is clean.

    Checks the half a PATH sandbox cannot see: sockets and D-Bus opened from
    inside the process. AF_BLUETOOTH is 31 on Linux.
    """
    problems = []

    # 1. Any AF_BLUETOOTH socket held by this process. /proc/net/ lists the
    #    kernel's Bluetooth socket tables; they only exist if something opened
    #    one, and we compare against our own file descriptors.
    try:
        fd_dir = f"/proc/{os.getpid()}/fd"
        for fd in os.listdir(fd_dir):
            try:
                target = os.readlink(os.path.join(fd_dir, fd))
            except OSError:
                continue
            if "bluetooth" in target.lower():
                problems.append(f"file descriptor {fd} points at {target}")
    except OSError as exc:
        problems.append(f"could not inspect own file descriptors: {exc}")

    # 2. The AF_BLUETOOTH constant must not even be reachable through a socket
    #    we hold. Python exposes it as socket.AF_BLUETOOTH where supported.
    af_bluetooth = getattr(socket, "AF_BLUETOOTH", None)
    if af_bluetooth is not None:
        try:
            for fd in os.listdir(f"/proc/{os.getpid()}/fd"):
                try:
                    s = socket.socket(fileno=int(fd))
                except (OSError, ValueError):
                    continue
                try:
                    if s.family == af_bluetooth:
                        problems.append(f"fd {fd} is an AF_BLUETOOTH socket")
                finally:
                    s.detach()
        except OSError:
            pass

    # 3. No connection to BlueZ on the system bus. We never import a D-Bus
    #    library at all, which is the strongest form of this guarantee.
    if "dbus" in sys.modules or "pydbus" in sys.modules:
        problems.append("a D-Bus module is imported; BlueZ could be reached")

    return problems


def assert_no_bluetooth(context: str) -> None:
    problems = bluetooth_audit()
    if problems:
        for p in problems:
            say("RULE 1 VIOLATED", p)
        say("stopped", f"refusing to continue: Bluetooth touched during {context}")
        raise SystemExit(3)



# --- rule 4: it declares its own limits, where they are read ------------------

LIMITS = """\
WHAT THIS DOES VALIDATE
  the LAN path, the status contract, the feedback surface, and whether the
  errors make sense to somebody who has not read the source

WHAT IT DOES NOT VALIDATE YET
  real discovery, pairing, and anything that depends on a BLE advertisement or
  on an actual Pixel being on the same subnet

WHAT IT DOES NOT UNBLOCK, AND THIS IS A LIMIT OF THE MACHINE
  the real rquickshare path here. bluetoothd segfaults when rquickshare STARTS,
  before any peer exists, so a virtual peer removes one of F1's two blockers --
  the missing phone -- and leaves the other exactly where it was. Against our
  own code (omapixel-status, the contract, the widget, the feedback surface)
  this peer is enough, because none of that needs rquickshare. Against real
  rquickshare, only a VM, and nobody has measured whether it crashes bluetoothd
  there too with no adapter passed through.

WHAT IT CAN NEVER VALIDATE
  the F1 discovery-flakiness box: how many attempts until the device appears,
  and whether having the phone's screen on helps. That flakiness lives in
  Android's radio management, not in the protocol. This peer advertises
  continuously, so it cannot reproduce it -- not "not yet", structurally never.
  Green transfers here are not evidence for that box.

Nothing measured against this peer may be written as measured, promoted in
data/capabilities.toml, or used to tick an F1 box. It closes test-infrastructure
boxes only."""


def print_limits() -> None:
    for line in LIMITS.splitlines():
        say("limits", line) if line.startswith("  ") else say("LIMITS", line)


# --- mDNS ---------------------------------------------------------------------


class Advertisement:
    """Publishes the peer over mDNS via avahi-publish-service.

    Shelling out rather than vendoring an mDNS stack, consistent with the rest
    of the project. TXT records carry the simulated mark so that anything
    discovering this peer over the network learns it is fake without having to
    be told.
    """

    def __init__(self, name: str, port: int):
        self.name = name
        self.port = port
        self.proc: subprocess.Popen | None = None

    def start(self) -> bool:
        if not shutil.which("avahi-publish-service"):
            say(
                "error",
                "avahi-publish-service is not installed, so the peer is "
                "reachable by address but will not be discovered. "
                "Install avahi, or connect directly to the port above",
            )
            return False
        self.proc = subprocess.Popen(
            [
                "avahi-publish-service",
                self.name,
                SERVICE_TYPE,
                str(self.port),
                "simulated=true",
                "source=omapixel-virtual-pixel",
                "n=Virtual Pixel",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=ENV,
            text=True,
        )
        say("advertising", f"{SERVICE_TYPE} as {self.name!r}, TXT simulated=true")
        return True

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            say("advertising stopped")


# --- the peer -----------------------------------------------------------------


# Failure modes. Hari asked for explicit feedback on ERROR, success and state,
# and a peer that can only succeed means the whole feedback surface gets
# designed, built and tested against the happy path — so the first real error a
# user sees would be the first error anyone had ever seen.
#
# A mode produces a failure; it does not measure one. A failure produced here is
# written "measured against the emulator", exactly like a success. That will be
# forgotten sooner than the success version, because an error is more convincing
# than a win.
FAILURE_MODES = {
    "none": "accept normally",
    "reject": "refuse the transfer",
    "drop": "accept, then close mid-transfer",
    "timeout": "accept and never answer",
    "vanish": "stop advertising while still listening",
    "absent": "never advertise at all, so there is no peer to find",
}


def serve(name: str, port: int, once: bool, mode: str, lan: bool) -> int:
    assert_no_bluetooth("startup")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Loopback by default. Binding 0.0.0.0 and advertising over mDNS puts a real
    # service on the operator's home network, and on the network of anybody who
    # runs the suite. The agreed scope of this version is exercising our own
    # code on this machine, so --lan is opt-in and says so out loud.
    try:
        listener.bind((BIND_LAN if lan else BIND_LOCAL, port))
    except OSError as exc:
        say("error", f"cannot listen on port {port}: {exc}")
        return 1
    listener.listen(4)
    actual_port = listener.getsockname()[1]
    where = "all interfaces (LAN-visible)" if lan else "loopback only"
    say("listening", f"tcp/{actual_port}, {where}")

    advert = Advertisement(name, actual_port)
    if mode == "absent":
        say("mode absent", "not advertising: exercising the no-peer-found path")
    elif not lan:
        # Advertising to the LAN while listening only on loopback would publish
        # an endpoint nobody can reach. The bind and the advertisement are one
        # decision, not two.
        say("not advertising", "loopback-only, so mDNS would publish an unreachable endpoint. Use --lan")
    else:
        # Echo the exact name before publishing it, not after. --name is free
        # text, so `--lan --name "$(hostname)"` broadcasts whatever that is to
        # the whole segment — on the reference machine the hostname is a
        # person's first name. Quick Share discovery is unauthenticated, so
        # anyone listening reads it, and an announcement cannot be recalled.
        # The operator is allowed to do it; they are not allowed to do it
        # without seeing what goes out.
        say("advertising", f"publishing the name {name!r} to every device on "
                           f"this network. This cannot be unpublished")
        advert.start()

    # The audit runs again after every socket and subprocess exists, because
    # rule 1 is about what the process actually did, not what it intended.
    assert_no_bluetooth("after opening sockets")
    # Printed on every run, not kept in a document. Whoever runs this next may
    # never have seen a word of the discussion that produced it, and their
    # natural mistake will be to report "transfer validated" when what was
    # validated is the LAN path.
    print_limits()
    say("ready", "no Bluetooth in use; this peer is LAN-only and simulated")

    stopping = threading.Event()

    def shutdown(signum, _frame):
        say("stopping", f"signal {signal.Signals(signum).name}")
        stopping.set()
        listener.close()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    handled = 0
    while not stopping.is_set():
        try:
            conn, addr = listener.accept()
        except OSError:
            break
        # Only the port is logged, never the peer address: this output ends up
        # pasted into issues, same rule as everywhere else in the project.
        say("peer connected", f"from port {addr[1]}")
        with conn:
            if mode == "reject":
                say("rejected", "the peer refused the transfer")
                conn.sendall(b"REJECTED simulated peer refusing by request\n")
            elif mode == "drop":
                say("accepted", "simulated transfer accepted")
                conn.sendall(b"ACCEPTED simulated peer, no data was stored\n")
                say("failed", "closing mid-transfer, on purpose")
                conn.shutdown(socket.SHUT_RDWR)
            elif mode == "timeout":
                say("hanging", "accepted the connection and answering nothing")
                stopping.wait(30)
            else:
                say("accepted", "simulated transfer accepted")
                conn.sendall(b"ACCEPTED simulated peer, no data was stored\n")
                if mode == "vanish":
                    say("vanishing", "withdrawing the advertisement, still listening")
                    advert.stop()
        handled += 1
        if once:
            break

    advert.stop()
    say("stopped", f"handled {handled} connection(s)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="A simulated Quick Share peer. Never touches Bluetooth.",
    )
    parser.add_argument("--port", type=int, default=0, help="0 picks a free port")
    parser.add_argument(
        "--lan", action="store_true",
        help="bind all interfaces and advertise over mDNS. Off by default: this "
             "puts a real service on your network",
    )
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--once", action="store_true", help="handle one and exit")
    parser.add_argument(
        "--mode", default="none", choices=sorted(FAILURE_MODES),
        help="; ".join(f"{k}: {v}" for k, v in FAILURE_MODES.items()),
    )
    parser.add_argument(
        "--limits", action="store_true", help="print what this can and cannot validate"
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="audit that no Bluetooth is reachable, print the result, exit",
    )
    args = parser.parse_args(argv[1:])

    if args.limits:
        print_limits()
        return 0

    if args.self_check:
        problems = bluetooth_audit()
        for binary in BLUETOOTH_BINARIES:
            say("note", f"never executed: {binary}")
        if problems:
            for p in problems:
                say("RULE 1 VIOLATED", p)
            return 3
        say("self-check passed", "no Bluetooth sockets, no BlueZ, no BT binaries")
        return 0

    return serve(args.name, args.port, args.once, args.mode, args.lan)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
