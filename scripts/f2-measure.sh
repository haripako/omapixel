#!/usr/bin/env bash
#
# Measure the F2 rows that need a gesture on the phone: clipboard and file
# transfer, plus the notification count.
#
# Run this, then do the gestures. It observes and never sends: nothing here
# touches the phone, so a failure is the phone's or the link's, not this
# script's.
#
# It exists because "it did not work" costs another gesture. When the clipboard
# does not arrive there are three different answers — the plugin is not loaded,
# the packet arrived and was dropped, or nothing ever left the phone — and they
# have three different fixes. Separating them at the time of the attempt is
# free; reconstructing them afterwards means asking the person to do it again.
#
# PRIVACY: this prints sizes, counts and hashes, never contents. Clipboard text
# and notification bodies are the user's, and this output is the kind of thing
# that ends up pasted into an issue.
#
set -uo pipefail

DURATION="${1:-300}"
DOWNLOADS="${2:-$HOME/Downloads}"
DEV="${KDECONNECT_DEVICE:-}"
BUS=(busctl --user)
KDE=(org.kde.kdeconnect)

say() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

dev_path() { echo "/modules/kdeconnect/devices/$DEV"; }

prop() {
  "${BUS[@]}" get-property "${KDE[@]}" "$(dev_path)$1" "$2" "$3" 2>/dev/null \
    | awk '{print $2}'
}

# Hash, never the text. Comparing hashes answers "did it change" without this
# script ever holding, printing or logging what was copied.
clip_hash() { wl-paste -n 2>/dev/null | sha256sum | cut -c1-12; }

notif_count() {
  "${BUS[@]}" call "${KDE[@]}" "$(dev_path)/notifications" \
    org.kde.kdeconnect.device.notifications activeNotifications 2>/dev/null \
    | tr ' ' '\n' | grep -c '"' || true
}

# --- baseline ----------------------------------------------------------------

if [ -z "$DEV" ]; then
  DEV=$("${BUS[@]}" call "${KDE[@]}" /modules/kdeconnect \
        org.kde.kdeconnect.daemon devices bb true true 2>/dev/null \
        | tr ' ' '\n' | grep -o '"[^"]*"' | tr -d '"' | head -1)
fi

if [ -z "$DEV" ]; then
  say "FAIL: no paired, reachable device. Nothing below would mean anything."
  say "      Try: scripts/omapixel-do retry-link"
  exit 1
fi

say "device $DEV"
say "  reachable: $(prop "" org.kde.kdeconnect.device isReachable)"

plugins=$("${BUS[@]}" call "${KDE[@]}" "$(dev_path)" \
  org.kde.kdeconnect.device loadedPlugins 2>/dev/null)
for p in clipboard share notifications; do
  case "$plugins" in
    *kdeconnect_$p*) say "  plugin $p: loaded" ;;
    *) say "  plugin $p: NOT LOADED — that alone explains a failure below" ;;
  esac
done

clip_before=$(clip_hash)
notif_before=$(notif_count)
files_before=$(ls -1 "$DOWNLOADS" 2>/dev/null | wc -l)
journal_mark=$(date '+%Y-%m-%d %H:%M:%S')

say "  clipboard hash: $clip_before"
say "  notifications:  $notif_before"
say "  files in $(basename "$DOWNLOADS"): $files_before"
say ""
say "DO THE GESTURES NOW, watching for ${DURATION}s:"
say "  1. copy a short text on the phone"
say "  2. share a small file to this PC"
say "  3. let a notification arrive, and look at the screen"
say ""

# --- watch --------------------------------------------------------------------

clip_seen=0
file_seen=0
notif_seen=0
start=$(date +%s)

while [ $(( $(date +%s) - start )) -lt "$DURATION" ]; do
  now=$(clip_hash)
  if [ "$now" != "$clip_before" ] && [ "$clip_seen" -eq 0 ]; then
    clip_seen=1
    say "CLIPBOARD changed: $clip_before -> $now ($(wl-paste -n 2>/dev/null | wc -c) bytes)"
    say "  Note this proves the desktop clipboard changed, not who changed it."
    say "  If you also copied something here, that is the same evidence."
  fi

  files_now=$(ls -1 "$DOWNLOADS" 2>/dev/null | wc -l)
  if [ "$files_now" -gt "$files_before" ] && [ "$file_seen" -eq 0 ]; then
    file_seen=1
    newest=$(ls -t "$DOWNLOADS" | head -1)
    say "FILE arrived: .${newest##*.}, $(stat -c%s "$DOWNLOADS/$newest" 2>/dev/null) bytes"
  fi

  n=$(notif_count)
  if [ "$n" -gt "$notif_before" ] && [ "$notif_seen" -eq 0 ]; then
    notif_seen=1
    say "NOTIFICATION count rose: $notif_before -> $n"
    say "  The desktop RECEIVED it. Whether it was DRAWN is the half only you"
    say "  can confirm — say whether one appeared on screen."
  fi
  sleep 2
done

# --- verdict, one line per matrix row ----------------------------------------

say ""
say "result, one row at a time"

if [ "$clip_seen" -eq 1 ]; then
  say "  clipboard:     ARRIVED"
else
  say "  clipboard:     NOTHING ARRIVED. Which of these is it:"
  hits=$(journalctl --user --since "$journal_mark" 2>/dev/null \
         | grep -ci "clipboard" || true)
  say "                 kdeconnectd said 'clipboard' $hits times since we started."
  say "                 0 means nothing reached this host: the phone did not send,"
  say "                 or the link dropped. More than 0 means it arrived and was"
  say "                 not applied, which is a different bug entirely."
fi

if [ "$file_seen" -eq 1 ]; then
  say "  file transfer: ARRIVED in $DOWNLOADS"
else
  say "  file transfer: NOTHING ARRIVED in $DOWNLOADS."
  say "                 Check the phone said 'sent' rather than 'sending'; a"
  say "                 stalled transfer over a relay looks identical from here."
fi

if [ "$notif_seen" -eq 1 ]; then
  say "  notifications: RECEIVED (drawing still needs a human to confirm)"
else
  say "  notifications: count unchanged. Not evidence either way if no"
  say "                 notification happened to arrive during the window."
fi

say ""
say "Every row above was measured over whatever transport the link is using."
say "Check it before writing any of this down: over Tailscale it says nothing"
say "about the LAN path, and the two fail differently."
