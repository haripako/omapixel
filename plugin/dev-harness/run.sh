#!/usr/bin/env bash
# Render the widget model through the real QML engine against a fixture.
#
#   plugin/dev-harness/run.sh [fixture.json]
#
# Assembles a temp config so nothing is symlinked into the plugin folder, which
# `omarchy plugin validate` refuses. Measured cycle: about a tenth of a second,
# against a shell restart for the real bar — which is why development never has
# to blank the operator's bar.
set -uo pipefail
LC_ALL=C; export LC_ALL

here=$(cd "$(dirname "$0")" && pwd)
plugin="$here/../io.github.haripako.omapixel"
fixture=${1:-$here/fixtures/nothing-works.json}

[ -r "$fixture" ] || { echo "no such fixture: $fixture" >&2; exit 1; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp "$plugin/Model.js" "$tmp/Model.js"
# The fixture is injected as a property so the QML file stays fixed and only
# the data changes between runs.
sed "s|property string fixture: \"\"|property string fixture: '$(tr -d '\n' < "$fixture" | sed "s/'/\\\\'/g")'|" \
  "$here/shell.qml" > "$tmp/shell.qml"

# Neither Qt.quit() nor Quickshell.quit() ends the process, so it is given a
# short deadline and killed. Not elegant; the whole cycle still lands near a
# tenth of a second, against a shell restart for the real bar.
timeout -s TERM 5 qs -p "$tmp/shell.qml" 2>&1 | sed -n 's/.*qml[^:]*: //p'
exit 0
