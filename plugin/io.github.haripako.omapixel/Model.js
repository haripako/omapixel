// Pure presentation logic for the omapixel bar widget.
//
// Kept out of Panel.qml on purpose: QML has no hot-reload here, so every
// change to a .qml file costs a shell restart. This file is plain JavaScript
// and can be exercised by a test runner in milliseconds, which is where the
// interesting decisions live anyway.
//
// The rule this file exists to enforce: **switch on `status`, never on the
// reason text.** The contract gives five statuses and each one is a different
// thing for the user to do. A widget that renders them all as one grey blank
// throws that away, and "no battery showing" becomes unanswerable.
//
// See docs/08-status-contract.md.

.pragma library

// One entry per contract status. `action` is what the user would have to do —
// which is the whole point of the distinction, and the reason four of these
// are not interchangeable.
var PRESENTATION = {
  ready:           { tone: "normal",  glyph: "•",  action: null },
  not_installed:   { tone: "absent",  glyph: "↓",  action: "install" },
  no_answer:       { tone: "stalled", glyph: "!",  action: "start" },
  nothing_present: { tone: "empty",   glyph: "○",  action: "pair" },
  not_probed:      { tone: "held",    glyph: "?",  action: "allow" },
};

// A status we do not know is not the same as a status we know to be bad. An
// older or newer producer must degrade into "unsure", never into a confident
// reading — the same direction the contract insists on for provenance.
var UNKNOWN = { tone: "unsure", glyph: "?", action: null };

function present(status) {
  return PRESENTATION[status] || UNKNOWN;
}

// --- battery -----------------------------------------------------------------

// The case for `source` in one function. With AVRCP, one combined figure is the
// complete and correct answer, so drawing three slots with two of them empty
// lies twice: it invents a missing reading, and it implies the tool failed.
function batteryCells(battery) {
  if (!battery || typeof battery !== "object") {
    return { cells: [], note: "no battery data", complete: false };
  }
  if (battery.kind === "per_bud") {
    var cells = [];
    ["left", "right", "case"].forEach(function (slot) {
      if (battery[slot] !== null && battery[slot] !== undefined) {
        cells.push({ slot: slot, percent: battery[slot] });
      }
    });
    // A null case means unknown, not empty: the case has no radio of its own.
    var missing = 3 - cells.length;
    return {
      cells: cells,
      note: missing > 0 ? missing + " reading(s) did not arrive" : null,
      complete: missing === 0,
    };
  }
  if (battery.kind === "combined") {
    return {
      cells: [{ slot: "combined", percent: battery.combined }],
      // Not a caveat. Over AVRCP this IS the answer.
      note: battery.source === "avrcp" ? "one figure is all AVRCP gives" : null,
      complete: true,
    };
  }
  return { cells: [], note: battery.reason || "unavailable", complete: false };
}

// --- a slot in the bar --------------------------------------------------------

function slot(name, capability) {
  if (!capability || typeof capability !== "object") {
    return {
      name: name, tone: UNKNOWN.tone, glyph: UNKNOWN.glyph,
      summary: "unknown", detail: "the status command returned nothing for " + name,
      action: null,
    };
  }

  var look = present(capability.status);
  var detail = capability.reason || null;

  // available is defined as status === "ready". If a producer ever disagrees
  // with itself, believe neither and say so rather than picking one.
  if (capability.available === true && capability.status !== "ready") {
    return {
      name: name, tone: "unsure", glyph: "?",
      summary: "inconsistent",
      detail: "reported available with status " + capability.status,
      action: null,
    };
  }

  return {
    name: name,
    tone: look.tone,
    glyph: look.glyph,
    summary: capability.status === "ready" ? "ok" : capability.status.replace(/_/g, " "),
    detail: detail,
    action: look.action,
  };
}

// --- the whole widget ---------------------------------------------------------

function model(payload) {
  if (!payload || typeof payload !== "object") {
    return { broken: true, detail: "no output from the status command", slots: [] };
  }
  if (payload.error) {
    // The contract promises a parseable body even when the command fails.
    return { broken: true, detail: payload.error, slots: [] };
  }
  var caps = payload.capabilities || {};
  return {
    broken: false,
    detail: null,
    slots: [
      slot("buds", caps["buds"]),
      slot("phone", caps["phone-link"]),
      slot("transfer", caps["file-transfer"]),
    ],
  };
}
