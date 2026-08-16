// The omapixel bar widget.
//
// Draws what `omapixel-status --json` reports and nothing else. It never runs
// pbpctrl, kdeconnect-cli or rquickshare, and it never touches Bluetooth: on
// this machine a tool bringing up a BLE listener segfaults bluetoothd and takes
// the pointer with it, so a bar widget must not be the thing that does that.
//
// All the decisions live in Model.js, which a test runner exercises in
// milliseconds. QML has no hot-reload here, so anything put in this file costs
// a shell restart to check. Keep this file about pixels.
//
// See docs/08-status-contract.md.

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import "Model.js" as Model

BarWidget {
  id: root
  moduleName: "io.github.haripako.omapixel"

  readonly property string statusCommand: root.setting("statusCommand", "")
  readonly property int refreshSeconds: root.setting("refreshSeconds", 30)
  readonly property bool hideWhenNothingAvailable:
    root.setting("hideWhenNothingAvailable", false)

  // The parsed model, or a broken one. Never null, so the bindings below never
  // have to guard — same reason the contract always emits every capability.
  property var view: Model.model(null, Date.now(), root.staleAfter)

  // Two missed polls before a reading is called stale. Tied to the interval
  // rather than fixed, so changing the interval cannot silently make every
  // reading look fresh.
  readonly property int staleAfter: Math.max(60, root.refreshSeconds * 2)

  readonly property var worst: {
    // Rank by how much the user can do about it, not by severity. "Install a
    // package" is more actionable than "nothing paired", and that is the one
    // worth surfacing when the bar has room for one glyph.
    // "waiting" sits below everything actionable: an hourglass is not a thing
    // the user can do anything about today, so it should not push aside a
    // missing package they could install right now.
    var order = ["unsure", "stalled", "absent", "held", "empty", "waiting", "normal"]
    var pick = null
    for (var i = 0; i < view.slots.length; i++) {
      var s = view.slots[i]
      if (pick === null || order.indexOf(s.tone) < order.indexOf(pick.tone)) pick = s
    }
    return pick
  }

  visible: !(root.hideWhenNothingAvailable && root.worst
             && root.worst.tone !== "normal")
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  // One glyph per tone, so the four absent states stay four different things
  // at a glance rather than one grey blank. The mapping is here and not in
  // Model.js because it is the only genuinely visual decision.
  function glyphFor(tone) {
    // Chosen by rendering them at bar size and looking, not from memory. The
    // first set was picked blind and two of them were wrong: "everything is
    // fine" was a QR code, and "unknown" was a glyph that reads as a tick —
    // which would have drawn doubt as confirmation, the exact failure this
    // widget exists to prevent.
    switch (tone) {
      case "normal":  return "\uf012c"  // check: nothing to do
      case "absent":  return "\uf01da"  // download: a package is missing
      case "stalled": return "\uf0026"  // warning: it is there and not answering
      case "empty":   return "\uf00b2"  // bluetooth off: nothing paired, or out of range
      case "held":    return "\uf03e4"  // pause: deliberately not asked
      case "waiting": return "\uf051f"  // hourglass: blocked on a condition, not broken
      default:        return "\uf02d7"  // question: we do not know, and say so
    }
  }

  function line(s) {
    var text = s.name + ": " + s.summary
    if (s.action) text += "  → " + s.action
    // A reading from the emulator, or one whose origin nobody declared, is
    // never presented as a measurement. Absent origin degrades to unknown.
    if (s.qualifier) text += "  (" + s.qualifier + ")"
    if (s.stale === true) text += "  (stale)"
    if (s.unblockedBy) text += "\n    clears when: " + s.unblockedBy
    if (s.detail) text += "\n    " + s.detail
    return text
  }

  readonly property string tooltip: {
    if (view.broken) return "omapixel: " + view.detail
    var lines = []
    for (var i = 0; i < view.slots.length; i++) lines.push(line(view.slots[i]))
    return lines.join("\n")
  }

  Process {
    id: probe
    // An empty setting means "find it on PATH", which is what a normal install
    // gives. sh -c so the fallback is one command either way.
    command: ["sh", "-c",
      (root.statusCommand !== "" ? "'" + root.statusCommand + "'" : "omapixel-status")
      + " --json 2>/dev/null || echo '{\"error\":\"omapixel-status is not on PATH\"}'"]

    stdout: StdioCollector {
      onStreamFinished: {
        var parsed = null
        try {
          parsed = JSON.parse(this.text)
        } catch (e) {
          // Unparseable output is its own failure and says so, rather than
          // leaving the last good reading on screen pretending to be current.
          root.view = Model.model({ error: "unparseable output from omapixel-status" },
                                  Date.now(), root.staleAfter)
          return
        }
        root.view = Model.model(parsed, Date.now(), root.staleAfter)
      }
    }
  }

  Timer {
    // 84 ms per call as measured on 2026-08-16, so polling is affordable now.
    // It was 2090 ms before KDE Connect was asked over D-Bus instead of its
    // CLI, and at that cost this timer would have been indefensible.
    interval: Math.max(5, root.refreshSeconds) * 1000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: probe.running = true
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.glyphFor(root.worst ? root.worst.tone : "unsure")
    active: root.worst && root.worst.tone === "normal"
    tooltipText: root.tooltip
    // Refresh on demand. Nothing here writes to a device: changing ANC or
    // sending a file means talking to hardware, and that belongs to the
    // backend side, behind its own command.
    onPressed: function(b) { probe.running = true }
  }
}
