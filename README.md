# pixel-omarchy

Integrar el ecosistema de Google (móviles Pixel, Pixel Buds y lo que se sume) con
Arch Linux + Omarchy sobre Hyprland/Wayland, tan cerca como se pueda de lo que
hace Apple entre iPhone y Mac: compartir ficheros sin fricción, portapapeles
común, notificaciones, emparejado inmediato y control de los auriculares.

No es un producto nuevo desde cero. La estrategia es **integrar lo que ya existe
y funciona, medir dónde falla, y escribir solo las piezas que falten** — sobre
todo la capa de Omarchy (widgets de barra, atajos, menú), que es donde nadie ha
hecho el trabajo.

## Estado

**Fase 0 — inventario y panorama.** Nada instalado todavía. La máquina parte de
cero: ni Quick Share, ni KDE Connect, ni herramientas de Android.

## Documentos

| Fichero | Qué contiene |
|---|---|
| `docs/01-panorama.md` | Estado del arte real, con fuentes y fecha. Qué existe, qué está vivo y qué está muerto |
| `docs/02-matriz-capacidades.md` | Función por función: equivalente Apple, si es posible hoy en Linux y con qué |
| `docs/03-roadmap.md` | Fases, de lo que funciona esta tarde a lo que es investigación pura |
| `docs/04-inventario.md` | Qué hay medido en esta máquina y qué falta |

## Scripts

- `scripts/check-entorno.sh` — comprueba qué está instalado y escupe las órdenes
  exactas de instalación de lo que falte. No instala nada por su cuenta.

## Aviso sobre las fuentes

Todo lo de `docs/01-panorama.md` viene de búsqueda web del **15 de agosto de
2026** y de consultar el AUR en esa fecha; está marcado como derivado. Lo de
`docs/04-inventario.md` está **medido** en esta máquina. No mezclar las dos cosas:
en este terreno las cosas envejecen rápido.
