#!/usr/bin/env bash
#
# Watch a KDE Connect pairing attempt and say which stage it reached.
#
# Run this, then pair from the phone. It installs nothing, starts nothing, and
# never touches Bluetooth: KDE Connect is LAN only.
#
# It exists because "it did not work" is not a measurement. Three failures look
# identical from the desktop — the phone never appeared, it appeared and pairing
# was refused, it paired and nothing transferred — and they have three different
# causes and three different fixes. Without separating them the first attempt
# produces an anecdote.
#
# The silent one is the firewall. docs/05-packaging.md records it: with ufw
# active and the KDE Connect ports closed, discovery finds nothing, with no
# error and no log line on either side. That is indistinguishable from "the
# phone is not running KDE Connect" unless something counts the drops, which is
# what this does.
#
set -uo pipefail

DURATION="${1:-180}"
PORT=1716

say() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

# --- what is true before anything is attempted -------------------------------

say "baseline"

if ! pgrep -x kdeconnectd >/dev/null; then
  say "  FAIL: kdeconnectd is not running. Nothing below will mean anything."
  say "        Start it and re-run. This is stage 0, not a discovery failure."
  exit 1
fi
say "  kdeconnectd running, pid $(pgrep -x kdeconnectd | head -1)"

listening=$(ss -lntup 2>/dev/null | grep -c ":$PORT\b") || listening=0
if [ "$listening" -eq 0 ]; then
  say "  FAIL: nothing is listening on $PORT. The daemon is up but not serving."
  exit 1
fi
say "  listening on $PORT ($listening sockets)"

# The count matters, not the rule. Reading the ufw rules needs root; counting
# what the kernel dropped does not, and a drop is the observable effect while a
# rule is only an intention.
drops_before=$(journalctl -k --since "1 hour ago" 2>/dev/null \
  | grep -c "UFW BLOCK.*DPT=$PORT") || drops_before=0
say "  ufw drops on $PORT in the last hour: $drops_before"

# Asked over D-Bus, not through the CLI. Two reasons, and both are already
# project decisions: kdeconnect-cli --list-devices runs a fixed two-second
# discovery cycle before answering, which is useless in a three-second poll
# loop; and scripts here must not invoke the integration tools directly, so a
# test sandbox can still intercept everything. tests/test_hw_report.py enforces
# the second and caught this script doing it.
kde() {
  busctl --user call org.kde.kdeconnect /modules/kdeconnect \
    org.kde.kdeconnect.daemon devices bb "$1" "$2" 2>/dev/null \
    | tr ' ' '\n' | grep -c '"' || true
}

devices_before=$(kde false true)
say "  devices known: $devices_before"

say ""
say "PAIR FROM THE PHONE NOW. Watching for ${DURATION}s."
say ""

# --- watch --------------------------------------------------------------------

seen_device=0
seen_paired=0
start=$(date +%s)

while [ $(( $(date +%s) - start )) -lt "$DURATION" ]; do
  ids=$(kde true false)
  if [ "$ids" -gt "$devices_before" ] && [ "$seen_device" -eq 0 ]; then
    seen_device=1
    say "STAGE 1 reached: the phone is visible. Discovery works, so the LAN"
    say "  path and the firewall are both fine."
    busctl --user call org.kde.kdeconnect /modules/kdeconnect \
      org.kde.kdeconnect.daemon devices bb true false 2>/dev/null | sed 's/^/    /'
  fi

  if [ "$seen_device" -eq 1 ] && [ "$seen_paired" -eq 0 ]; then
    if [ "$(kde true true)" -gt 0 ]; then
      seen_paired=1
      say "STAGE 2 reached: paired and reachable."
      say "  This is NOT 'notifications work' and NOT 'clipboard works'."
      say "  Those are separate matrix rows and each needs its own measurement."
    fi
  fi
  sleep 3
done

# --- verdict ------------------------------------------------------------------

drops_after=$(journalctl -k --since "1 hour ago" 2>/dev/null \
  | grep -c "UFW BLOCK.*DPT=$PORT") || drops_after=0
new_drops=$(( drops_after - drops_before ))

say ""
say "result"
say "  new ufw drops on $PORT during the window: $new_drops"

if [ "$seen_paired" -eq 1 ]; then
  say "  PAIRED. Measured: discovery and pairing. Nothing else."
elif [ "$seen_device" -eq 1 ]; then
  say "  DISCOVERED BUT NOT PAIRED. The network path works; the failure is in"
  say "  pairing itself — a refused request, a key mismatch, or nobody accepted"
  say "  the prompt on one of the two ends. Not a firewall problem."
elif [ "$new_drops" -gt 0 ]; then
  say "  NOT DISCOVERED, AND THE FIREWALL DROPPED $new_drops PACKETS ON $PORT."
  say "  The phone did try. This is the silent failure from docs/05-packaging.md:"
  say "  open the port and repeat before concluding anything about KDE Connect."
else
  say "  NOT DISCOVERED, AND NOTHING WAS DROPPED."
  say "  Nothing arrived on $PORT at all, so the phone never sent — or it sent"
  say "  somewhere this host never saw. Check that KDE Connect is open on the"
  say "  phone, that it is on this subnet, and that the AP is not isolating"
  say "  clients. Same subnet is not the same thing as reachable."
fi

say ""
say "Whatever this says, it measures discovery and pairing only. Notifications,"
say "clipboard and file transfer are separate rows and none of them follow."
