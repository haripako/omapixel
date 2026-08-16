# omapixel

Bringing the Google ecosystem — Pixel phones, Pixel Buds, and whatever else gets
added — as close to Arch Linux with [Omarchy](https://omarchy.org) on
Hyprland/Wayland as Apple manages between an iPhone and a Mac: file sharing
without friction, a shared clipboard, notifications, instant pairing, and
control over the earbuds.

This is not a from-scratch product. The strategy is to **integrate what already
exists and works, measure where it fails, and write only the missing pieces** —
above all the Omarchy layer (bar widgets, keybindings, menu), which is where
nobody has done the work.

> **Status: early.** Two different things are true at once, and keeping them
> apart is the point of this repository. The reference machine has been measured
> in detail — its adapter, its network, whether the phone is actually reachable —
> and that lives in [docs/04-reference-setup.md](docs/04-reference-setup.md).
> But **no capability has been measured on any device yet**: every row of the
> [capability matrix](docs/02-capability-matrix.md) still reads `untested`,
> because it is. A measured host is not a measured capability.

## The one rule

Every claim here is tagged **measured** (somebody ran it and watched what
happened) or **derived** (it came from a README, an AUR page or a news article).
The two never get blurred, and derived never graduates to measured by being
repeated. See [conventions](docs/conventions.md).

## Documentation

| File | What is in it |
|---|---|
| [docs/conventions.md](docs/conventions.md) | The measured/derived rule and what the statuses mean. Read this first |
| [docs/01-landscape.md](docs/01-landscape.md) | State of the art, with sources and a date. Entirely derived |
| [docs/02-capability-matrix.md](docs/02-capability-matrix.md) | Generated. Function by function, per device, with a name and a date on every cell |
| [docs/03-roadmap.md](docs/03-roadmap.md) | Phases F0 to F5, from what works this afternoon to pure research |
| [docs/04-reference-setup.md](docs/04-reference-setup.md) | The maintainer's machine, measured. The baseline others get compared against |
| [docs/05-packaging.md](docs/05-packaging.md) | Development environment vs. the final product, and the bring-up friction that decided the difference |
| [docs/features.md](docs/features.md) | Every Apple Continuity and AirPods feature, translated into a target here, tiered by what kind of work it is. Entirely derived |
| [docs/06-design.md](docs/06-design.md) | Design rules: the Omarchy token system measured, the Material pieces worth importing, and who wins where they conflict |
| [docs/07-plan.md](docs/07-plan.md) | The plan of record: what gets built, in which blocks, in what order, and the six things a user should end up able to say |
| [docs/journal.md](docs/journal.md) | What was established, on what day, and by what kind of evidence. Read it to find out whether a claim has aged |

## Scripts

**None of these install anything.** `hw-report.sh` prints the exact commands it
would need and stops; running them is your decision.

```bash
scripts/hw-report.sh              # check this machine
scripts/hw-report.sh --markdown   # block to paste into a hardware report issue
scripts/omapixel-status --json    # what works right now, machine-readable
scripts/build-matrix.py           # regenerate the capability matrix from data/
scripts/run-tests.sh              # the suite; standard library only
```

`omapixel-status` is the interface everything else reads, so that swapping a
tool underneath costs one file — see the [status
contract](docs/08-status-contract.md). It never talks to Bluetooth unless asked
with `--probe-bluetooth`, and it emits valid JSON even when nothing at all is
installed.

## Contributing

**The most useful thing you can send is a measurement from hardware nobody here
owns.** One Pixel and one pair of Buds Pro 2 is the entire hardware pool behind
this repository; everything said about a Pixel 9, first-generation Buds Pro,
Buds A-Series or a different Bluetooth adapter is guesswork until somebody
reports it.

```bash
git clone https://github.com/haripako/omapixel.git
cd omapixel
scripts/hw-report.sh --markdown
```

Then open a **Hardware report** issue and paste the output. That is the whole
ask. Details in [CONTRIBUTING.md](CONTRIBUTING.md).

The generator needs `bash`; regenerating the matrix additionally needs
`python3`. Both ship with Omarchy, but this repository is meant to be useful
from other setups too, so it is worth saying.

## Licence

GPL-3.0. See [LICENSE](LICENSE).

---

# omapixel (español)

Integrar el ecosistema de Google — móviles Pixel, Pixel Buds y lo que se sume —
con Arch Linux y [Omarchy](https://omarchy.org) sobre Hyprland/Wayland, tan cerca
como se pueda de lo que hace Apple entre iPhone y Mac: compartir ficheros sin
fricción, portapapeles común, notificaciones, emparejado inmediato y control de
los auriculares.

No es un producto nuevo desde cero. La estrategia es **integrar lo que ya existe
y funciona, medir dónde falla, y escribir solo las piezas que falten** — sobre
todo la capa de Omarchy (widgets de barra, atajos, menú), que es donde nadie ha
hecho el trabajo.

> **Estado: fase temprana.** No hay nada instalado todavía en la máquina de
> referencia y ninguna función se ha medido en ningún aparato. La matriz de
> capacidades lo dice sin adornos: casi todo pone `untested`, porque lo está.

## La regla que manda

Cada afirmación está marcada como **medida** (alguien lo ejecutó y vio qué
pasaba) o **derivada** (sale de un README, del AUR o de una noticia). Las dos
cosas no se mezclan nunca, y lo derivado no asciende a medido por repetirse.

## Documentación

La documentación técnica está en inglés para que pueda colaborar gente con
hardware que aquí no tenemos. Empieza por
[docs/conventions.md](docs/conventions.md).

## Cómo colaborar

Lo más útil que puedes aportar es **una medida hecha sobre hardware que aquí no
hay**: unos Buds Pro de primera generación, un Pixel de otra gama, otro
adaptador Bluetooth.

```bash
git clone https://github.com/haripako/omapixel.git
cd omapixel
scripts/hw-report.sh --markdown   # bloque para pegar en una issue (redacta MAC e IP)
```

Abre una issue de tipo *Hardware report* y pega la salida. Ya está. No instala
nada: imprime las órdenes que harían falta y para ahí.

Los demás guiones, por si te sirven:

```bash
scripts/hw-report.sh              # estado de esta máquina — ojo, la salida por
                                  # defecto lleva tu MAC y tus IP sin redactar
scripts/omapixel-status --json    # qué funciona ahora mismo, legible por máquina
scripts/build-matrix.py           # regenera la matriz de capacidades desde data/
scripts/run-tests.sh              # la suite; solo biblioteca estándar
```

Las issues en español son bienvenidas: nadie debería quedarse fuera de reportar
un aparato por el idioma.

## Licencia

GPL-3.0.
