#!/usr/bin/env bash
#
# Environment and hardware report for omapixel.
#
#   scripts/hw-report.sh              human-readable check of this machine
#   scripts/hw-report.sh --markdown   block to paste into a GitHub issue
#   scripts/hw-report.sh --toml       [host] section for a device report
#
# This script NEVER installs anything. It prints the exact commands and stops.
#
# Privacy: --markdown and --toml are meant to be published, so they redact MAC
# addresses and host IPs, printing the adapter model and the bare subnet
# instead. The default human output redacts nothing, because it stays on your
# machine.
#
set -uo pipefail

MODE=human
case "${1:-}" in
  --markdown) MODE=markdown ;;
  --toml)     MODE=toml ;;
  --help|-h)  sed -n '2,14p' "$0" | sed 's/^# \?//'; exit 0 ;;
  "")         ;;
  *)          echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

OK=$'\033[32m+\033[0m'; NO=$'\033[31m-\033[0m'; WARN=$'\033[33m!\033[0m'
# Colour only when a terminal is going to read it. "Send me the output of this
# script" usually means a redirect to a file, and escape sequences inside the
# file are noise the reporter then has to explain.
{ [ "$MODE" = human ] && [ -t 1 ]; } || { OK=+; NO=-; WARN='!'; }

# A declared end marker, so that a truncated report is distinguishable from a
# complete one. Measured by the advisor in a clean VM: half a table looks
# exactly like a table. There is no MAC row to be missing, so nothing looks
# absent, and a stranger has nothing to compare against — they only knew the
# Tools section was missing because they had seen a full run hours earlier.
#
# Announced in the header, so its absence carries information instead of being
# noticed by whoever happens to remember. It also helps the other end: whoever
# triages a hardware issue can tell a complete report from a cut-off one at a
# glance, without running anything.
#
# Visible rather than an HTML comment: GitHub renders the report, and a comment
# would be invisible in exactly the place it is most needed.
#
# CHECKING FOR IT: match the last non-blank line exactly, not a substring, and
# not a grep over the whole text. The markdown header quotes this marker in
# order to announce it, so markdown contains it twice — a report cut off just
# after the header still has "end of report" in its last line and would pass a
# substring check. --toml emits it once, at the end, with no announcement,
# which is why a check over data/devices/*.toml can afford the loose form. That
# difference is invisible from the checking side and is the trap waiting for
# whoever extends this to pasted markdown. Verified 2026-08-16: toml 1
# occurrence, markdown 2.
#
# Read the raw text, too: in --toml the marker is a comment, and tomllib drops
# comments, so a check over the parsed dict would never find it and would call
# every report truncated.
END_MARK='*— end of report —*'

# Every bluetoothctl call goes through here, and none of them may block.
#
# bluetoothctl does not exit when bluetooth.service is not running: it waits on
# D-Bus, forever. Measured in a clean Omarchy 4.0.0 VM with no adapter on
# 2026-08-16 by the advisor: hw-report.sh printed half a table and hung, in
# both modes, with no prompt and no error, because stderr was discarded too.
#
# That is the worst possible place for it. This script is the only thing this
# project asks a stranger to run, and the people it hangs on are exactly the
# ones worth hearing from — an absent adapter, a masked service, a VM. The
# ones whose Bluetooth already works were never the problem.
#
# It also swallowed the redaction notice: the footer saying MAC and IP were
# removed is printed after this point, so a user who hit Ctrl+C and pasted what
# they had pasted a table with no notice at all.
bt() {
  timeout 5 bluetoothctl "$@" 2>/dev/null
}

# Prints a value that identifies the person running this, with the warning
# attached to the line rather than left in the header.
#
# The header warns whoever ran the command; it never reaches whoever reads the
# paste. People scroll, select the block they care about — which is this one —
# and paste that, leaving the whole Tools section between the warning and the
# data. Last night's defect was a warning that could be lost to a hang; this is
# the same failure rotated, a warning that cannot be lost but can go
# unselected. Raised by the security agent.
#
# Not marked when there is no value: "unknown (bluetooth service not running)
# (identifies you)" claims that something unknown identifies you, which is the
# kind of sentence this project spends its time deleting.
identifying_line() {
  local label=$1 value=$2
  case "$value" in
    unknown*|"") printf '  %-22s %s\n' "$label" "${value:-unknown}" ;;
    *)           printf '  %-22s %-24s %s\n' "$label" "$value" "(identifies you)" ;;
  esac
}

bt_available() {
  [ "$(systemctl is-active bluetooth 2>/dev/null)" = active ]
}

missing_pacman=()
missing_aur=()

# --- facts about this machine ------------------------------------------------

distro() {
  local name version
  # shellcheck disable=SC1091  # /etc/os-release is not present at lint time
  name=$(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-$NAME}")
  version=$(cat ~/.local/share/omarchy/version 2>/dev/null)
  # A clean install has no version file yet, and PRETTY_NAME alone came out as
  # bare "Omarchy" in the advisor's VM — a hardware report with no distro
  # version is worth noticeably less. Fall back to os-release before giving up.
  # shellcheck disable=SC1091
  [ -n "$version" ] || version=$(. /etc/os-release 2>/dev/null && echo "${VERSION_ID:-$BUILD_ID}")
  case "$name" in
    *"$version"*) echo "$name" ;;
    *) [ -n "$version" ] && echo "$name $version" || echo "${name:-unknown}" ;;
  esac
}

desktop() {
  local compositor
  compositor=$(hyprctl version 2>/dev/null | awk 'NR==1{print $1" "$2}')
  echo "${compositor:-${XDG_CURRENT_DESKTOP:-unknown}}"
}

bluez_version() { pacman -Q bluez 2>/dev/null | awk '{print $2}'; }

# Adapter model rather than its MAC: the MAC identifies the machine.
bt_mac() {
  bt_available || { echo "unknown (bluetooth service not running)"; return; }
  # Capture first, filter second. Not style: `bt show | awk '...{exit}'` closes
  # the pipe early, bluetoothctl dies of SIGPIPE, and `pipefail` faithfully
  # reports 141 for a pipeline that worked. The guard then printed "timed out"
  # on a machine where bluetoothctl answers in 7 ms — a false failure, which is
  # the one kind this script must not invent. Caught by reading the output on a
  # working machine, after a review had cleared the function.
  local out mac
  out=$(bt show) || { echo "unknown (bluetoothctl timed out)"; return; }
  mac=$(printf '%s\n' "$out" | awk '/Controller/{print $2; exit}')
  echo "${mac:-unknown}"
}

bt_adapter() {
  local usb
  usb=$(lsusb 2>/dev/null | grep -iE 'bluetooth|wireless_device' | head -1 \
        | sed -E 's/.*ID ([0-9a-f:]+) (.*)/\2 (usb \1)/i')
  [ -n "$usb" ] && echo "$usb" || echo "unknown"
}

# Subnet only, never the host address.
subnets() {
  ip -4 -o addr show scope global 2>/dev/null \
    | grep -vE ' (docker|br-|virbr|veth|tailscale)' \
    | awk '{split($4,a,"/"); split(a[1],o,"."); print $2" "o[1]"."o[2]"."o[3]".0/"a[2]}' \
    | paste -sd', '
}

wifi_state() {
  local dev
  dev=$(ip -o link show 2>/dev/null | awk -F': ' '/wl/{print $2; exit}')
  [ -z "$dev" ] && { echo "no wireless interface"; return; }
  if ip -4 addr show "$dev" 2>/dev/null | grep -q 'inet '; then
    echo "$dev connected"
  else
    echo "$dev present but not connected"
  fi
}

# Says why it does not know, instead of printing a 0 that reads as "none
# paired". Those are different facts and the second one is a lie when the
# service is down. -c counts matches and never prints a name, which is why a
# device name cannot reach a report through this script.
google_paired() {
  bt_available || { echo "unknown (bluetooth service not running)"; return; }
  local out
  out=$(bt devices Paired) || { echo "unknown (bluetoothctl timed out)"; return; }
  echo "$out" | grep -icE 'pixel|google'
}

# 18d1 is Google's USB vendor id. The product id tells us which USB mode the
# phone is in, which decides whether adb or MTP can see it at all.
pixel_usb() {
  local line id
  line=$(lsusb 2>/dev/null | grep -i '18d1:' | head -1) || true
  [ -z "$line" ] && { echo "none"; return; }
  id=$(echo "$line" | sed -E 's/.*ID (18d1:[0-9a-f]+).*/\1/i')
  case "${id##*:}" in
    4ee1) echo "$id (MTP, file transfer)" ;;
    4ee2) echo "$id (MTP + adb)" ;;
    4ee6) echo "$id (PTP)" ;;
    4ee7) echo "$id (charging + adb, no MTP)" ;;
    *)    echo "$id" ;;
  esac
}

# --- tool checks -------------------------------------------------------------

check() {  # $1=binary $2=package $3=repo $4=purpose
  if command -v "$1" &>/dev/null; then
    [ "$MODE" = human ] && printf '  %s %-16s %s\n' "$OK" "$1" "$4"
    return 0
  fi
  [ "$MODE" = human ] && printf '  %s %-16s %s  -> %s/%s\n' "$NO" "$1" "$4" "$3" "$2"
  [ "$3" = pacman ] && missing_pacman+=("$2") || missing_aur+=("$2")
  return 1
}

tool_line() {  # markdown: one row per tool
  local bin=$1 label=$2
  if command -v "$bin" &>/dev/null; then
    echo "| \`$label\` | installed |"
  else
    echo "| \`$label\` | not installed |"
  fi
}

run_checks() {
  check rquickshare    r-quick-share aur    "Quick Share with the Pixel"
  check kdeconnect-cli kdeconnect    pacman "clipboard, notifications, SMS"
  check wl-copy        wl-clipboard  pacman "Wayland clipboard"
  check pbpctrl        pbpctrl       aur    "buds battery, ANC, equaliser"
  check adb            android-tools pacman "Android debugging"
  check scrcpy         scrcpy        pacman "phone screen on the desktop"
}

# --- output ------------------------------------------------------------------

case "$MODE" in

toml)
  cat <<EOF
[host]
distro = "$(distro)"
desktop = "$(desktop)"
kernel = "$(uname -r)"
bluez = "$(bluez_version)"
bt_adapter = "$(bt_adapter)"
# $END_MARK
EOF
  ;;

markdown)
  # The redaction notice goes first, not last.
  #
  # It used to be the closing <sub> line, fourteen lines after the call that
  # could hang forever. A notice printed at the end is conditional on the
  # program finishing, which makes it a sign-off rather than a warning: a user
  # who hit Ctrl+C and pasted what they had pasted a table with nothing on it.
  # Printed before the first external command, it cannot be lost. Raised by the
  # security agent, and the reordering is the defence — the timeouts below are
  # the bug fix.
  echo "<sub>Generated by \`scripts/hw-report.sh --markdown\`. MAC addresses and"
  echo "host IPs are redacted; subnets are shown so Quick Share reachability can"
  echo "be reasoned about. Read it before you paste it."
  echo "This report ends with \`$END_MARK\` — if you cannot see that line, it is"
  echo "incomplete, and please say so rather than sending it.</sub>"
  echo
  echo "### Host"
  echo
  echo "| | |"
  echo "|---|---|"
  echo "| Distro | $(distro) |"
  echo "| Desktop | $(desktop) |"
  echo "| Kernel | $(uname -r) |"
  echo "| BlueZ | $(bluez_version) |"
  echo "| Bluetooth adapter | $(bt_adapter) |"
  echo "| Subnets | $(subnets) |"
  echo "| Wireless | $(wifi_state) |"
  echo "| Google devices paired | $(google_paired) |"
  echo "| Pixel over USB | $(pixel_usb) |"
  echo
  echo "### Tools"
  echo
  echo "| Tool | State |"
  echo "|---|---|"
  tool_line rquickshare    r-quick-share
  tool_line kdeconnect-cli kdeconnect
  tool_line wl-copy        wl-clipboard
  tool_line pbpctrl        pbpctrl
  tool_line adb            android-tools
  tool_line scrcpy         scrcpy
  echo
  echo "$END_MARK"
  ;;

human)
  # Same reasoning as the markdown header: this is the mode that prints your
  # MAC and IP in full, so saying so has to happen before anything that could
  # fail to return.
  echo "This output contains your MAC and IP addresses in full. To share it,"
  echo "use the redacted form:  scripts/hw-report.sh --markdown"
  echo
  echo "-- Tools --"
  run_checks
  echo
  echo "-- Environment --"
  printf '  %-22s %s\n' "distro"          "$(distro)"
  printf '  %-22s %s\n' "desktop"         "$(desktop)"
  printf '  %-22s %s\n' "kernel"          "$(uname -r)"
  printf '  %-22s %s\n' "bluez"           "$(bluez_version)"
  printf '  %-22s %s\n' "bt adapter"      "$(bt_adapter)"
  # These two lines carry their own warning, because the header's does not
  # travel with them. A header warns whoever ran the command; it never reaches
  # whoever reads the paste. In a terminal people scroll, select the block they
  # care about — which is this one — and paste that, leaving fifteen lines and
  # the whole Tools section between the warning and the data. Last night's bug
  # was that the warning could be lost to a hang; this is the same failure
  # rotated: it cannot be lost now, but it can go unselected. These are the
  # only two lines in the report that identify a person, so the marker is
  # noise in exactly the right place. Raised by the security agent.
  identifying_line "bt adapter mac" "$(bt_mac)"
  identifying_line "addresses" "$(ip -4 -o addr show scope global 2>/dev/null | grep -vE ' (docker|br-|virbr|veth)' | awk '{print $2" "$4}' | paste -sd', ')"
  printf '  %-22s %s\n' "wireless"        "$(wifi_state)"
  printf '  %-22s %s\n' "google paired"   "$(google_paired)"
  printf '  %-22s %s\n' "pixel over usb"  "$(pixel_usb)"
  echo

  # The bare `pacman -S` used to be printed on its own, and on a fresh Omarchy
  # it fails: the package databases are empty, so every name comes back as
  # "target not found". Measured by the advisor in a clean VM on 2026-08-16.
  #
  # Two things make that worse than a failed command. "target not found:
  # kdeconnect" tells someone with modest Arch knowledge that the package does
  # not exist, so they go looking for it or conclude the documentation is
  # wrong. And pacman's own advice, "use '-Sy' to download", is the classic way
  # to break an Arch install: -Sy without -u leaves a partial upgrade. The
  # error message points at the dangerous exit, and it mostly works, which is
  # what makes it a trap.
  if [ ${#missing_pacman[@]} -gt 0 ]; then
    echo "Install from the official repositories:"
    echo "  sudo pacman -Syu ${missing_pacman[*]}"
    printf '  %s On a fresh install, sync first: a bare -S reports "target not found"\n' "$WARN"
    printf '     for packages that exist. Never -Sy on its own; that is a partial\n'
    printf '     upgrade. On Omarchy, "Update System" from the menu does this for you.\n'
  fi
  if [ ${#missing_aur[@]} -gt 0 ]; then
    echo "Install from the AUR:"
    echo "  yay -S ${missing_aur[*]}"
    # Was "it may not build". It builds: measured 2026-08-16 in a clean Omarchy
    # 4.0.0 VM, 48 seconds, pbpctrl 0.1.8-1. The staleness is real and the
    # pessimism was not, so the warning now says the part that is still true —
    # building is not the same as speaking to hardware it was never aimed at.
    printf '  %s pbpctrl was 482 days without an AUR update as of 2026-08-15, but\n' "$WARN"
    printf '     built fine on 2026-08-16 (0.1.8-1, ~48s, clean Omarchy 4.0.0).\n'
    printf '     It targets first-generation Pixel Buds Pro: building says nothing\n'
    printf '     about whether it talks to Buds Pro 2, which use a different SoC.\n'
  fi
  if [ ${#missing_pacman[@]} -eq 0 ] && [ ${#missing_aur[@]} -eq 0 ]; then
    echo "Nothing left to install."
  fi
  echo
  # The warning itself moved to the top, where it cannot be lost. What belongs
  # here is only the end marker: seeing it is how you know nothing was cut.
  echo "$END_MARK"
  ;;
esac

exit 0
