# Roadmap

Cada fase entra con algo concreto y sale con algo comprobable. Nada de pasar a
la siguiente sin haber medido la anterior.

## F0 — Inventario y entorno

Entras con: una máquina limpia y este repo.
Sales con: saber exactamente qué hardware hay y qué falta instalar.

- [ ] Ejecutar `scripts/check-entorno.sh` y volcar el resultado en `04-inventario.md`
- [ ] Anotar qué aparatos Google hay realmente (modelo de Pixel, modelo de Buds, versión de Android)
- [ ] Emparejar los Buds por Bluetooth y anotar la MAC
- [ ] Comprobar que el móvil y el PC están en la misma subred WiFi (requisito duro de Quick Share)

## F1 — Transferencia de ficheros

Entras con: F0 cerrada.
Sales con: mandar y recibir del Pixel sin tocar un cable.

- [ ] Instalar `r-quick-share` desde AUR
- [ ] Probar recepción PC ← móvil y envío PC → móvil
- [ ] Medir el problema de descubrimiento: cuántos intentos hasta que aparece, y si mejora con la pantalla del móvil encendida
- [ ] Verificar el indicador de bandeja bajo Hyprland y con la barra de Quickshell
- [ ] Si el arranque automático es necesario, dejarlo como servicio de usuario

## F2 — Portapapeles y notificaciones

Entras con: F1 funcionando.
Sales con: copiar en el móvil y pegar en el PC.

- [ ] Instalar `kdeconnect` y la app de Android
- [ ] Emparejar y validar: portapapeles en los dos sentidos, notificaciones, SMS
- [ ] Verificar el portapapeles bajo Wayland (`wl-clipboard`)
- [ ] Decidir cómo arranca el daemon en la sesión de Hyprland
- [ ] Comprobar si el icono de bandeja convive con la barra

## F3 — Pixel Buds

Entras con: los Buds emparejados.
Sales con: batería y ANC desde el escritorio.

- [ ] Instalar `pbpctrl` desde AUR (ojo: 482 días sin actualizar, puede no compilar)
- [ ] Comprobar qué modelo de Buds responde y qué campos devuelve
- [ ] Si `pbpctrl` está muerto, evaluar `budslink-git` y si ha añadido Pixel Buds
- [ ] Envolver la lectura de batería en un script estable para consumir desde la barra

## F4 — Integración con Omarchy (aquí empieza lo original)

Entras con: F1-F3 dando datos por línea de órdenes.
Sales con: que todo esto se vea y se use desde el escritorio.

- [ ] Plugin de barra: batería de los Buds y estado del móvil
- [ ] Atajos de Hyprland: ciclar ANC, enviar el fichero seleccionado al móvil
- [ ] Entrada en el menú de Omarchy
- [ ] Empaquetar el plugin siguiendo `manifest.json` + `omarchy plugin validate`

## F5 — Investigación (sin compromiso de que salga)

- [ ] Fast Pair: ¿hay especificación pública del lado *provider*? ¿Sirve de algo sin los servicios de Google Play?
- [ ] Cross-device services: ¿tráfico observable? ¿está atado a atestación de dispositivo?
- [ ] Decidir con honestidad si esto es viable o si se cierra la puerta y se documenta el porqué

## Principio del proyecto

Antes de escribir código propio, comprobar que no existe ya. Y antes de dar por
buena una función, medirla contra el aparato real — no contra el README de
nadie.
