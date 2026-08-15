#!/usr/bin/env bash
# Comprueba qué hace falta para pixel-omarchy y qué falta por instalar.
# NO instala nada: solo informa y escupe las órdenes exactas.
set -uo pipefail

OK=$'\033[32m✓\033[0m'; NO=$'\033[31m✗\033[0m'; WARN=$'\033[33m!\033[0m'
falta_pacman=()
falta_aur=()

check() {  # $1=binario  $2=paquete  $3=repo(pacman|aur)  $4=para qué
  if command -v "$1" &>/dev/null; then
    printf '  %s %-22s %s\n' "$OK" "$1" "$4"
  else
    printf '  %s %-22s %s  → %s/%s\n' "$NO" "$1" "$4" "$3" "$2"
    [ "$3" = pacman ] && falta_pacman+=("$2") || falta_aur+=("$2")
  fi
}

echo "── Transferencia de ficheros ──"
check rquickshare  r-quick-share  aur     "Quick Share nativo con el Pixel"

echo "── Portapapeles, notificaciones, SMS ──"
check kdeconnect-cli kdeconnect   pacman  "puente con Android"
check wl-copy        wl-clipboard pacman  "portapapeles de Wayland"

echo "── Pixel Buds ──"
check pbpctrl      pbpctrl        aur     "batería detallada, ANC, ecualizador"

echo "── Android / depuración ──"
check adb          android-tools  pacman  "ADB, imprescindible para depurar"
check scrcpy       scrcpy         pacman  "pantalla del móvil en el escritorio"

echo "── Ya en el sistema ──"
for c in bluetoothctl gio udisksctl; do
  command -v "$c" &>/dev/null && printf '  %s %-22s\n' "$OK" "$c"
done

echo
echo "── Entorno ──"
printf '  bluez: %s\n' "$(pacman -Q bluez 2>/dev/null | awk '{print $2}' || echo '?')"
printf '  adaptador BT: %s\n' "$(bluetoothctl show 2>/dev/null | awk '/Controller/{print $2; exit}')"
printf '  red: %s\n' "$(ip -4 -o addr show scope global 2>/dev/null \
  | grep -vE ' (docker|br-|virbr)' | awk '{print $2" "$4}' | paste -sd', ')"
printf '  aparatos Google emparejados: %s\n' \
  "$(bluetoothctl devices Paired 2>/dev/null | grep -icE 'pixel|google' | head -1)"

echo
if [ ${#falta_pacman[@]} -gt 0 ]; then
  echo "Instalar de los repos oficiales:"
  echo "  sudo pacman -S ${falta_pacman[*]}"
fi
if [ ${#falta_aur[@]} -gt 0 ]; then
  echo "Instalar del AUR:"
  echo "  yay -S ${falta_aur[*]}"
  echo "  ${WARN} pbpctrl lleva 482 días sin actualizarse (consultado 15 ago 2026): puede no compilar"
fi
if [ ${#falta_pacman[@]} -eq 0 ] && [ ${#falta_aur[@]} -eq 0 ]; then echo "Nada que instalar."; fi

exit 0
