# Matriz de capacidades

Función por función, qué hace Apple, qué se puede hacer hoy aquí y con qué.
Los estados son una estimación derivada del panorama, **no medidos todavía**.

Leyenda de estado:
- **Listo** — existe herramienta y solo hay que instalarla y validarla
- **Parcial** — existe pero cojea, o le falta la integración con Omarchy
- **Por hacer** — hay que escribirlo
- **Bloqueado** — no hay camino conocido hoy

| Función | Equivalente Apple | Estado | Con qué | Notas |
|---|---|---|---|---|
| Enviar/recibir ficheros con el móvil | AirDrop | Listo | `r-quick-share` | Misma red WiFi obligatoria; descubrimiento intermitente |
| Portapapeles compartido | Universal Clipboard | Listo | KDE Connect | Verificar `wl-clipboard` bajo Hyprland |
| Notificaciones del móvil en el escritorio | Centro de notificaciones | Listo | KDE Connect | Encajar con el daemon de Omarchy |
| SMS desde el escritorio | Mensajes | Listo | KDE Connect | |
| Móvil como mando / teclado | Continuity | Listo | KDE Connect | |
| Batería de los Pixel Buds | Batería de AirPods en el menú | Parcial | `pbpctrl` | AVRCP solo da una cifra combinada; las tres exigen protocolo propietario. Proyecto sin tocar en 482 días |
| Control de ANC de los Buds | Control de ANC | Parcial | `pbpctrl`, quizá BudsLink | BudsLink aún no lista Pixel Buds |
| Widget de barra con Buds y móvil | Menú de control | Por hacer | Plugin de Omarchy | Es nuestro terreno: `manifest.json` + QML |
| Atajos de teclado (ANC, enviar al móvil) | — | Por hacer | Hyprland (Lua) + scripts | |
| Pantalla del móvil en el escritorio | iPhone Mirroring | Parcial | `scrcpy` | Está en `extra`; requiere depuración USB o ADB por WiFi |
| Emparejado inmediato al abrir el estuche | Emparejado de AirPods | Bloqueado | — | Sin Fast Pair para Linux |
| Compartir internet sin contraseña | Instant Hotspot | Bloqueado | — | Cross-device services es Android/ChromeOS |
| Pasar una llamada de un aparato a otro | Handoff de llamadas | Bloqueado | — | Ídem |
| Continuar una app entre aparatos | Handoff | Bloqueado | — | No existe el concepto fuera de Apple/Google-a-Google |

## Cómo leer esto

Las tres primeras filas son casi todo el valor práctico y se pueden tener
funcionando en una tarde. La zona interesante a medio plazo es la de **Por
hacer**: nadie ha integrado esto en Omarchy, y ahí sí aportamos algo original
en vez de instalar paquetes.

Las cuatro **Bloqueado** dependen de protocolos cerrados de Google atados a
cuenta y a Android/ChromeOS. Antes de invertir ahí hay que responder a una
pregunta previa: ¿hay tráfico observable y documentado, o hay que hacer
ingeniería inversa desde cero? Eso es investigación, no desarrollo.
