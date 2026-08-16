// Fixture harness for the widget model. Runs under `qs -p` against a copy of
// Model.js in a temp directory, so it never lives inside the plugin folder
// (symlinks are rejected there) and never restarts the operator's shell.
//
// Use run.sh; it assembles the temp directory and reads the output back.
import QtQuick
import Quickshell
import "Model.js" as Model

ShellRoot {
  property string fixture: ""
  Component.onCompleted: {
    var m = Model.model(JSON.parse(fixture), Date.now(), 120)
    if (m.broken) { console.log("BROKEN | " + m.detail); return }
    for (var i = 0; i < m.slots.length; i++) {
      var s = m.slots[i]
      console.log(s.name + " | " + s.tone + " | " + s.summary
                  + " | action=" + (s.action || "-")
                  + " | origin=" + s.origin
                  + " | qualifier=" + (s.qualifier || "-")
                  + " | stale=" + s.stale)
    }
  }
}
