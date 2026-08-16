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
  // Not an error and not permanent. "Wait", with a condition somebody can
  // check. It clears on its own when the condition does — the gate is on a
  // version, not on a tool — so drawing it as a red failure would be a lie in
  // a few weeks' time.
  blocked:         { tone: "waiting", glyph: "…",  action: "wait" },
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


// --- staleness ----------------------------------------------------------------

// `as_of` is the moment a capability was probed, never the moment this was
// drawn. The reason it matters to a widget: the bar redraws far more often than
// it polls, so without the stamp a reading from a minute ago and a fresh one
// are painted identically.
//
// An absent or unparseable stamp is UNKNOWN, not fresh. Degrading the other way
// would let an old producer pass its readings off as current, which is the same
// direction the contract forbids for provenance.
function freshness(asOf, nowMs, staleAfterSeconds) {
  if (typeof asOf !== "string" || asOf === "") {
    return { known: false, stale: null, ageSeconds: null };
  }
  var t = Date.parse(asOf);
  if (isNaN(t)) return { known: false, stale: null, ageSeconds: null };
  var age = Math.max(0, Math.round((nowMs - t) / 1000));
  return { known: true, stale: age > staleAfterSeconds, ageSeconds: age };
}

// --- reachability -------------------------------------------------------------

// "paired but out of range" and "nothing paired" are two states with two
// different fixes -- turn the phone on, or pair it -- and they were
// indistinguishable until the contract split them. The widget has to say which.
function phoneSummary(capability) {
  var st = (capability && capability.state) || {};
  var paired = Array.isArray(st.devices) ? st.devices : [];
  if (paired.length === 0) return null;

  // `reachable` is a list of the device ids that answered, not a boolean. It
  // was a boolean when this was first written and the shape changed under it,
  // which silently killed the out-of-range case: `=== false` simply never
  // matched a list. Handled both ways now, and unknown stays unknown rather
  // than being read as reachable.
  var reachable;
  if (Array.isArray(st.reachable)) {
    reachable = paired.filter(function (id) { return st.reachable.indexOf(id) !== -1; });
  } else if (st.reachable === true) {
    reachable = paired;
  } else if (st.reachable === false) {
    reachable = [];
  } else {
    return null;  // no reachability information: say nothing rather than guess
  }

  if (reachable.length > 0) return null;

  // Paired and none of them answering. Two different fixes -- wake the phone,
  // or pair one -- and they were indistinguishable until the contract split
  // them, so the widget has to say which.
  return { summary: "out of range", action: "wake", tone: "empty",
           paired: paired.length };
}

// --- origin -------------------------------------------------------------------

// device | emulator | unknown. Absent counts as unknown, never as device.
//
// The direction matters more than the field. The emulator is the cheapest thing
// in this project to run and the only one always available while the hardware
// is missing, so an unqualified reading will not become wrong through bad faith
// — it will become wrong because running the emulator is easy. A widget that
// paints emulator data like hardware is the screenshot that ends up in an issue
// as evidence of something nobody measured.
//
// Note as of 2026-08-16: `origin` exists in the device-report schema but is NOT
// yet emitted by omapixel-status, so everything here currently resolves to
// unknown. Written now because the defaulting direction is the whole point, and
// getting it wrong later is a retrofit across every consumer.
function originOf(thing) {
  var value = thing && thing.origin;
  if (value === "device" || value === "emulator") return value;
  return "unknown";
}

// What a reading is allowed to claim, given where it came from.
function trust(origin) {
  if (origin === "device") return { real: true, qualifier: null };
  if (origin === "emulator") return { real: false, qualifier: "emulator" };
  return { real: false, qualifier: "origin unknown" };
}

// --- a slot in the bar --------------------------------------------------------

function slot(name, capability, nowMs, staleAfterSeconds) {
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

  var summary = capability.status === "ready" ? "ok"
              : capability.status.replace(/_/g, " ");

  // `blocked` carries the two things that make waiting bearable: why, and
  // until when. unblocked_by is written to be shown verbatim.
  var st = capability.state || {};
  if (capability.status === "blocked" && st.unblocked_by) {
    summary = "waiting for " + st.unblocked_by.split(",")[0];
  }
  var action = look.action;

  // Paired-but-unreachable outranks the generic status text, because it is the
  // one the user can act on.
  var reach = name === "phone" ? phoneSummary(capability) : null;
  if (reach) {
    summary = reach.summary;
    action = reach.action;
    look = { tone: reach.tone, glyph: "○", action: reach.action };
  }

  var fresh = freshness(capability.as_of, nowMs, staleAfterSeconds);
  var trusted = trust(originOf(capability));

  return {
    name: name,
    // A stale or unstamped reading is not drawn with the confidence of a fresh
    // one, whatever it says.
    tone: (!fresh.known || fresh.stale) && capability.status === "ready"
          ? "unsure" : look.tone,
    glyph: look.glyph,
    summary: summary,
    detail: detail,
    action: action,
    ageSeconds: fresh.ageSeconds,
    stale: fresh.known ? fresh.stale : null,
    // Never null: a consumer that forgets to check gets a qualifier rather
    // than silence, which is the safe direction.
    unblockedBy: (capability.state || {}).unblocked_by || null,
    origin: originOf(capability),
    qualifier: trusted.qualifier,
    real: trusted.real,
  };
}

// --- the whole widget ---------------------------------------------------------

function model(payload, nowMs, staleAfter) {
  staleAfter = staleAfter || 120;
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
      slot("buds", caps["buds"], nowMs, staleAfter),
      slot("phone", caps["phone-link"], nowMs, staleAfter),
      slot("transfer", caps["file-transfer"], nowMs, staleAfter),
    ],
  };
}
