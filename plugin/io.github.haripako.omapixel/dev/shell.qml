// Standalone harness. Runs the widget's model against a fixture and exits, so
// a change can be checked without restarting the real shell — and therefore
// without blanking the operator's bar. Not part of the plugin: `qs -p` only.
import QtQuick
import Quickshell
import "Model.js" as Model

ShellRoot {
  Component.onCompleted: {
    var payload = JSON.parse(fixture)
    var m = Model.model(payload, Date.now(), 120)
    for (var i = 0; i < m.slots.length; i++) {
      var s = m.slots[i]
      console.log(s.name + " | " + s.tone + " | " + s.glyph + " | " + s.summary
                  + " | action=" + (s.action || "-") + " | stale=" + s.stale)
    }
    Quickshell.quit()
  }
  property string fixture: '{"schema":1,"capabilities":{"buds":{"status":"not_installed","available":false,"reason":"pbpctrl is not installed","as_of":"2026-08-16T00:09:50Z","state":{}},"phone-link":{"status":"ready","available":true,"as_of":"2026-08-16T00:09:50Z","state":{"devices":["a"],"reachable":false}},"file-transfer":{"status":"no_answer","available":false,"reason":"not running","as_of":"2020-01-01T00:00:00Z","state":{}}}}'
}
