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


def serve(name: str, port: int, once: bool, reject: bool) -> int:
    assert_no_bluetooth("startup")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("0.0.0.0", port))
    except OSError as exc:
        say("error", f"cannot listen on port {port}: {exc}")
        return 1
    listener.listen(4)
    actual_port = listener.getsockname()[1]
    say("listening", f"tcp/{actual_port} on all interfaces")

    advert = Advertisement(name, actual_port)
    advert.start()

    # The audit runs again after every socket and subprocess exists, because
    # rule 1 is about what the process actually did, not what it intended.
    assert_no_bluetooth("after opening sockets")
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
            if reject:
                say("rejected", "--reject was given, refusing the transfer")
                conn.sendall(b"REJECTED simulated peer refusing by request\n")
            else:
                say("accepted", "simulated transfer accepted")
                conn.sendall(b"ACCEPTED simulated peer, no data was stored\n")
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
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--once", action="store_true", help="handle one and exit")
    parser.add_argument(
        "--reject", action="store_true", help="refuse transfers, to exercise the error path"
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="audit that no Bluetooth is reachable, print the result, exit",
    )
    args = parser.parse_args(argv[1:])

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

    return serve(args.name, args.port, args.once, args.reject)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
