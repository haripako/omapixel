# Inventario de la máquina

**Medido el 15 de agosto de 2026** con `scripts/check-entorno.sh`. A diferencia
del panorama, esto no es derivado: sale de la máquina.

## Lo que hay

| Pieza | Estado |
|---|---|
| BlueZ | 5.87-2 |
| Adaptador Bluetooth | `[mac redacted]` — MediaTek MT7922 (USB `0e8d:0608`) |
| Red cableada | `eno1` [ip redacted]/24 |
| Tailscale | `tailscale0` [ip redacted]/32 |
| `wl-clipboard` | instalado |
| `gvfs-mtp`, `libmtp` | instalados (montaje MTP del móvil por USB) |
| `waydroid` | instalado |
| `bluetoothctl`, `gio`, `udisksctl` | disponibles |

## Lo que falta

De los repos oficiales:

```bash
sudo pacman -S kdeconnect android-tools scrcpy
```

Del AUR:

```bash
yay -S r-quick-share pbpctrl
```

Aviso: `pbpctrl` llevaba 482 días sin actualizarse en el AUR el día de la
consulta. Puede no compilar contra Rust actual. Si falla, la alternativa es
`budslink-git`, aunque todavía no lista los Pixel Buds como soportados.

## Dos cosas que condicionan el proyecto

**No hay ningún aparato de Google emparejado en este equipo.** Cero. Lo que hay
emparejado es un MX Master 3S, un teclado RK-S98RGB, unos auriculares Xbox y un
mando de Xbox. Es decir: la fase 0 no es teórica, hace falta traer el Pixel y
los Buds y emparejarlos antes de poder medir nada.

**El PC está por cable, no por WiFi.** `eno1` es Ethernet y no hay interfaz
inalámbrica con IP en la lista. Quick Share exige que los dos aparatos estén en
la misma red: si el móvil va por WiFi al mismo router y la subred es la misma
(192.168.10.0/24), debería valer, pero **hay que comprobarlo** — es el primer
punto de fallo probable y sale gratis verificarlo antes de instalar nada.

Nota aparte: el adaptador Bluetooth de este equipo tiene un historial de
desconexiones sin explicar con el MX Master. Si aparecen rarezas emparejando los
Buds, mirar ahí antes de culpar al software nuevo.
