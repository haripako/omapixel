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
[ "$MODE" = human ] || { OK=+; NO=-; WARN='!'; }

missing_pacman=()
missing_aur=()

# --- facts about this machine ------------------------------------------------

distro() {
  local name version
  # shellcheck disable=SC1091  # /etc/os-release is not present at lint time
  name=$(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-$NAME}")
  version=$(cat ~/.local/share/omarchy/version 2>/dev/null)
  [ -n "$version" ] && echo "$name $version" || echo "${name:-unknown}"
}

desktop() {
  local compositor
  compositor=$(hyprctl version 2>/dev/null | awk 'NR==1{print $1" "$2}')
  echo "${compositor:-${XDG_CURRENT_DESKTOP:-unknown}}"
}

bluez_version() { pacman -Q bluez 2>/dev/null | awk '{print $2}'; }

# Adapter model rather than its MAC: the MAC identifies the machine.
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

google_paired() { bluetoothctl devices Paired 2>/dev/null | grep -icE 'pixel|google'; }

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
EOF
  ;;

markdown)
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
  echo "<sub>Generated by \`scripts/hw-report.sh --markdown\`. MAC addresses and"
  echo "host IPs are redacted; subnets are shown so Quick Share reachability can"
  echo "be reasoned about.</sub>"
  ;;

human)
  echo "-- Tools --"
  run_checks
  echo
  echo "-- Environment --"
  printf '  %-22s %s\n' "distro"          "$(distro)"
  printf '  %-22s %s\n' "desktop"         "$(desktop)"
  printf '  %-22s %s\n' "kernel"          "$(uname -r)"
  printf '  %-22s %s\n' "bluez"           "$(bluez_version)"
  printf '  %-22s %s\n' "bt adapter"      "$(bt_adapter)"
  printf '  %-22s %s\n' "bt adapter mac"  "$(bluetoothctl show 2>/dev/null | awk '/Controller/{print $2; exit}')"
  printf '  %-22s %s\n' "addresses"       "$(ip -4 -o addr show scope global 2>/dev/null | grep -vE ' (docker|br-|virbr|veth)' | awk '{print $2" "$4}' | paste -sd', ')"
  printf '  %-22s %s\n' "wireless"        "$(wifi_state)"
  printf '  %-22s %s\n' "google paired"   "$(google_paired)"
  printf '  %-22s %s\n' "pixel over usb"  "$(pixel_usb)"
  echo

  if [ ${#missing_pacman[@]} -gt 0 ]; then
    echo "Install from the official repositories:"
    echo "  sudo pacman -S ${missing_pacman[*]}"
  fi
  if [ ${#missing_aur[@]} -gt 0 ]; then
    echo "Install from the AUR:"
    echo "  yay -S ${missing_aur[*]}"
    printf '  %s pbpctrl had not been updated in 482 days as of 2026-08-15: it may not build\n' "$WARN"
  fi
  if [ ${#missing_pacman[@]} -eq 0 ] && [ ${#missing_aur[@]} -eq 0 ]; then
    echo "Nothing left to install."
  fi
  echo
  echo "This output contains your MAC and IP addresses in full. To share it,"
  echo "use the redacted form:  scripts/hw-report.sh --markdown"
  ;;
esac

exit 0
