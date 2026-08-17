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
  // Paired and not answering. Its own status since 2026-08-17, because it was
  // arriving as nothing_present and telling the user to pair a phone that was
  // already paired.
  unreachable:     { tone: "dropped", glyph: "/",  action: "wake" },
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

// Reachability used to be worked out here, by reading state.devices against
// state.reachable, because `status` said nothing_present for a paired phone.
// That code was right and the reason it was right was the problem: a widget
// only got the answer by ignoring the contract's own rule to switch on status.
//
// Removed on 2026-08-17, when `unreachable` became a status. The rule now in
// the contract: if you need the state to know what the status means, the
// status means nothing, and a disagreement between them is a defect in the
// status rather than a hint to read the state.

// --- devices, which now have names -------------------------------------------

// `devices` and `reachable` went from lists of ids to lists of {id, name} on
// 2026-08-17. Backend warned first this time, which is the whole point of the
// deal: the previous shape change to `reachable` killed a distinction silently
// and nobody noticed for hours.
//
// `name` is null rather than absent when the daemon does not supply one, so
// "has no name" and "was not asked" stay apart. A null name is shown as the
// short id: an id is unpleasant in a bar but it is true, and inventing a
// friendly label for a device we cannot name would be the plausible zero with
// better manners.
function deviceLabel(entry) {
  if (typeof entry === "string") return entry.slice(0, 8);  // the old shape
  if (!entry || typeof entry !== "object") return null;
  if (typeof entry.name === "string" && entry.name !== "") return entry.name;
  return typeof entry.id === "string" ? entry.id.slice(0, 8) : null;
}

function deviceNames(list) {
  if (!Array.isArray(list)) return [];
  var out = [];
  for (var i = 0; i < list.length; i++) {
    var label = deviceLabel(list[i]);
    if (label) out.push(label);
  }
  return out;
}

// --- how old, in words --------------------------------------------------------

// Design's ruling, and it is stricter than what this file did before: past the
// freshness window the age is shown NEXT TO the value, not instead of it. A
// remembered number drawn as a current one is the plausible zero again wearing
// a timestamp it hid — and a tone change alone cannot say how stale "stale" is.
// "84 %, 6 min ago" answers that; a dimmer 84 % does not.
function ageLabel(seconds) {
  if (seconds === null || seconds === undefined) return null;
  if (seconds < 45) return "just now";
  if (seconds < 90) return "1 min ago";
  if (seconds < 3600) return Math.round(seconds / 60) + " min ago";
  if (seconds < 7200) return "1 hour ago";
  if (seconds < 86400) return Math.round(seconds / 3600) + " hours ago";
  return "over a day ago";
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


// --- actions ------------------------------------------------------------------

// The fourth primitive. `actions` is absent whenever there is nothing to do,
// which is most of the time, so this must never assume the key exists — a
// consumer that reads it unguarded breaks in the normal case and works in the
// exceptional one, which is the worst way round.
//
// Absent means no action. It never means "there is one and we are not saying".
function actionsFrom(capability) {
  var list = capability && capability.actions;
  if (!Array.isArray(list)) return [];
  var out = [];
  for (var i = 0; i < list.length; i++) {
    var a = list[i];
    if (!a || typeof a.id !== "string" || a.id === "") continue;
    out.push({
      id: a.id,
      // A label we were not given is not invented from the id: an id is a
      // vocabulary token, not English.
      label: typeof a.label === "string" && a.label !== "" ? a.label : a.id,
      available: a.available === true,
      reason: a.reason || null,
    });
  }
  return out;
}

// The one worth putting on a button. Only an available action qualifies:
// offering a button that cannot work is worse than offering none.
function primaryAction(capability) {
  var list = actionsFrom(capability);
  for (var i = 0; i < list.length; i++) if (list[i].available) return list[i];
  return null;
}

// --- a slot in the bar --------------------------------------------------------

// The freshness window is per capability and comes from the contract, because
// it depends on how fast each value actually goes wrong — 30 s for phone
// reachability, which can be false seconds after being true; 300 s for a
// transfer, which turns on an installed package and a running process; 120 s
// for earbuds, whose battery moves slowly but which vanish between glances.
//
// The widget used to invent this as two missed polls. That instinct was right
// for a made-up number and is worse than a measured one. If the contract does
// not say, the caller's default is used and nothing pretends otherwise.
function windowFor(capability, fallbackSeconds) {
  var w = capability && capability.stale_after;
  return (typeof w === "number" && w > 0) ? w : fallbackSeconds;
}

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

  var fresh = freshness(capability.as_of, nowMs,
                        windowFor(capability, staleAfterSeconds));
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
    // Only carried when it changes what should be drawn: past the window, or
    // when there is no stamp at all. A fresh reading needs no caveat.
    age: fresh.known ? (fresh.stale ? ageLabel(fresh.ageSeconds) : null)
                     : "age unknown",
    // Never null: a consumer that forgets to check gets a qualifier rather
    // than silence, which is the safe direction.
    unblockedBy: (capability.state || {}).unblocked_by || null,
    devices: deviceNames((capability.state || {}).devices),
    staleAfter: windowFor(capability, staleAfterSeconds),
    actions: actionsFrom(capability),
    primaryAction: primaryAction(capability),
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
