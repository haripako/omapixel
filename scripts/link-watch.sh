#!/usr/bin/env bash
#
# Record how often the KDE Connect link drops, and how long recovery takes.
#
#   scripts/link-watch.sh [seconds] [--recover]
#
# Observes by default. With --recover it also calls omapixel-do retry-link on
# each drop and times the recovery, which is the only way to measure that
# number rather than assert it.
#
# It exists because nobody can honestly write "KDE Connect works over
# Tailscale" without it. The link dropped twice within a few hours on
# 2026-08-17, both times with the phone still answering pings — the IP path
# fine and KDE Connect simply not reconnecting. Two events is an observation.
# A rate needs a window and a count, and that is what this produces.
#
# Nothing here touches Bluetooth, and the phone is never contacted directly:
# every question goes to the local daemon over D-Bus.
#
set -uo pipefail

DURATION="${1:-3600}"
RECOVER=0
[ "${2:-}" = "--recover" ] && RECOVER=1

BUS=(busctl --user)
KDE=(org.kde.kdeconnect /modules/kdeconnect org.kde.kdeconnect.daemon)
HERE="$(dirname "$(readlink -f "$0")")"

say() { printf '[%s] %s\n' "$(date '+%F %H:%M:%S')" "$*"; }

reachable_count() {
  "${BUS[@]}" call "${KDE[@]}" devices bb true true 2>/dev/null \
    | tr ' ' '\n' | grep -c '"' || true
}

paired_count() {
  "${BUS[@]}" call "${KDE[@]}" devices bb false true 2>/dev/null \
    | tr ' ' '\n' | grep -c '"' || true
}

paired=$(paired_count)
if [ "$paired" -eq 0 ]; then
  say "nothing is paired; a drop count would be meaningless. Stopping."
  exit 1
fi

say "watching for ${DURATION}s, $paired paired, recover=$RECOVER"

start=$(date +%s)
was=$(reachable_count)
drops=0
recovered=0
total_down=0
down_since=0
say "baseline reachable=$was"

while [ $(( $(date +%s) - start )) -lt "$DURATION" ]; do
  now=$(reachable_count)

  if [ "$now" -lt "$was" ]; then
    drops=$(( drops + 1 ))
    down_since=$(date +%s)
    say "DROP #$drops (reachable $was -> $now, still paired $(paired_count))"
    if [ "$RECOVER" -eq 1 ]; then
      "$HERE/omapixel-do" retry-link >/dev/null 2>&1
      say "  asked for rediscovery"
    fi
  elif [ "$now" -gt "$was" ] && [ "$down_since" -gt 0 ]; then
    secs=$(( $(date +%s) - down_since ))
    total_down=$(( total_down + secs ))
    recovered=$(( recovered + 1 ))
    down_since=0
    say "  back after ${secs}s"
  fi

  was=$now
  sleep 30
done

elapsed=$(( $(date +%s) - start ))
say ""
say "result over ${elapsed}s"
say "  drops:            $drops"
say "  recoveries:       $recovered"
# Zero drops has two causes and they are opposites: the link never fell, or it
# was already down and never rose. Both produce drops=0, and the first draft of
# this script reported "the link held for the whole window" while the link had
# been down the entire time. Exactly the failure this project keeps finding in
# other people's tools, in a script written to measure it.
up_now=$(reachable_count)
if [ "$drops" -eq 0 ] && [ "$was" -eq 0 ] && [ "$up_now" -eq 0 ]; then
  say "  NOTHING MEASURED. The link was already down when the window opened and"
  say "  never came up, so zero drops says nothing about stability. Run"
  say "  scripts/omapixel-do retry-link first, confirm it is up, then measure."
elif [ "$drops" -eq 0 ]; then
  say "  The link held for the whole window. That is one window, not a"
  say "  guarantee — say the window length wherever this gets written down."
else
  say "  mean time between drops: $(( elapsed / drops ))s"
  [ "$recovered" -gt 0 ] && say "  mean recovery: $(( total_down / recovered ))s"
  [ "$down_since" -gt 0 ] && say "  still down at the end of the window"
fi
