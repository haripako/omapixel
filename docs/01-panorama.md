# Panorama: qué existe hoy

**Derivado de búsqueda web y consulta al AUR el 15 de agosto de 2026.** Nada de
esto está verificado ejecutándolo todavía; verificarlo es la fase 1.

## Compartir ficheros — Quick Share

**rquickshare** (`Martichou/rquickshare`, AGPL-3.0, Rust) es la reimplementación
del protocolo Nearby Share / Quick Share para Linux y macOS. Es la pieza central
del proyecto y la que está más madura.

- Cómo funciona: emite un **anuncio Bluetooth** para que Android publique su
  mDNS, y la transferencia real va por **WiFi en la LAN**. Consecuencia dura:
  los dos aparatos tienen que estar en la misma red.
- Bidireccional: enviar al móvil y recibir de él.
- Limitación conocida: la visibilidad del dispositivo Android es intermitente,
  porque Android no anuncia su mDNS de forma constante.
- El README se declara WIP.
- Empaquetado en AUR, tres variantes, consultadas el 15 ago 2026:
  `r-quick-share` 0.11.5-5 (actualizado hace 4 días, +15 votos),
  `r-quick-share-bin` 0.11.5-2, `r-quick-share-git`.
- Hay un fork, `oop7/rquickshare-x`, que añade Windows.
- Nada documentado sobre Wayland. **Punto a verificar el primero**: el
  indicador de bandeja y los diálogos bajo Hyprland.

Alternativas que no resuelven lo mismo: LocalSend, Warpinator y Syncthing usan
protocolos propios — sirven para mover ficheros, pero no hablan con el Quick
Share nativo del Pixel, que es justo lo que se busca.

## Pixel Buds

Dos proyectos, con perfiles opuestos:

**pbpctrl** (`qzed/pbpctrl`) — CLI, el de referencia. Lee batería detallada,
información de hardware/software, y lee y cambia ajustes: estado de ANC,
ecualizador. Pensado para Pixel Buds Pro; con otros modelos "puede funcionar o
no". En AUR: `pbpctrl` 0.1.8 y `pbpctrl-git`, **ambos de hace 482 días** — el
proyecto parece parado, riesgo a tener en cuenta. Existe también
`pbpctrl-plasmoid` (widget de Plasma, no nos sirve directamente, pero sí como
referencia de cómo se consume la información).

**BudsLink** — mucho más nuevo (cobertura de prensa en junio de 2026), con
interfaz gráfica, batería, ANC, modos de sonido ambiente y gestos. Habla
directamente por L2CAP/RFCOMM. Soporta AirPods, Galaxy Buds, Sony y Nothing;
**los Pixel Buds figuran como posible desarrollo futuro, no como soportados**.
En AUR: `budslink-git` (hace 90 días).

Dato técnico que condiciona el widget de batería: por AVRCP estándar solo se
obtiene **una batería combinada** para los dos auriculares y ninguna del
estuche. Para tener las tres cifras hace falta el protocolo propietario, que es
lo que hace pbpctrl. El estuche solo reporta si hay un auricular dentro, porque
no tiene radio propia.

## Portapapeles, notificaciones, SMS

**KDE Connect** es lo más completo y está en el repo `extra` de Arch. Da
portapapeles bidireccional, notificaciones, envío de ficheros, control remoto y
SMS. Es la base para toda la parte de "ecosistema".

**GSConnect** es la misma idea integrada en GNOME Shell: no aplica aquí, esto es
Hyprland.

Lo que hay que verificar bajo Hyprland: portapapeles con `wl-clipboard`,
notificaciones contra el daemon de Omarchy, y si el indicador de bandeja se
lleva bien con la barra (que ya sabemos que es Quickshell con SNI).

## Lo que hoy está cerrado

**Cross-device services de Google** — Instant Hotspot (compartir internet sin
contraseña) y Call casting (pasar una llamada de un aparato a otro). Anunciados
en I/O 2024 y desplegados desde julio de 2024, pero **solo entre dispositivos
Android y ChromeOS con la misma cuenta de Google**. No hay ninguna
implementación para Linux, ni oficial ni de terceros, a fecha de hoy.

**Fast Pair** — el emparejado inmediato al abrir el estuche. Sin implementación
Linux conocida.

Estas dos van al cajón de investigación, no al de trabajo.

## Fuentes

- [rquickshare — README](https://github.com/Martichou/rquickshare/blob/master/README.md)
- [rquickshare-x (fork con Windows)](https://github.com/oop7/rquickshare-x)
- [Cómo instalar RQuickShare en Linux](https://linuxtldr.com/install-rquickshare-on-linux/)
- [pbpctrl — README](https://github.com/qzed/pbpctrl/blob/main/README.md)
- [BudsLink llega a los escritorios Linux — Linux Journal](https://www.linuxjournal.com/content/budslink-brings-advanced-earbud-controls-linux-desktops)
- [BudsLink — OMG! Ubuntu](https://www.omgubuntu.co.uk/2026/06/budslink-airpods-galaxy-buds-linux)
- [Alternativas a KDE Connect](https://en.androidsis.com/Alternatives-to-KDE-Connect-for-connecting-Android-and-Linux/)
- [Cross-device services: Call casting e Internet sharing — 9to5Google](https://9to5google.com/2024/07/28/android-cross-device-services-rolling-out/)
- [Instant Hotspot, cómo usarlo — Android Authority](https://www.androidauthority.com/android-cross-device-services-how-to-instant-hotspot-3478597/)
