// ====== CONFIG ======
const ENDPOINT_URL = "https://garter-thermos-delirious.ngrok-free.dev/review";

function onOpen() {
  DocumentApp.getUi()
    .createMenu("Spec Review")
    .addItem("Review selected text", "reviewSelection")
    .addItem("Review section at cursor", "reviewSectionAtCursor")
    .addItem("Review section under heading…", "reviewHeadingSection")
    .addItem("Review entire doc", "reviewWholeDoc")
    .addToUi();
}

// ---------- Menu actions ----------

function reviewWholeDoc() {
  const text = DocumentApp.getActiveDocument().getBody().getText();
  sendForReview(text, "This document appears to be empty.");
}

function reviewSelection() {
  const text = getSelectedText();
  sendForReview(
    text,
    "Nothing is highlighted. Select the text you want reviewed, then run this again."
  );
}

// Reviews the section the cursor is in: the nearest heading above the cursor,
// through to the next heading of the same or higher level.
function reviewSectionAtCursor() {
  const doc = DocumentApp.getActiveDocument();
  const ui = DocumentApp.getUi();
  const cursor = doc.getCursor();
  if (!cursor) {
    ui.alert("Click inside the section you want reviewed, then run this again.");
    return;
  }
  const body = doc.getBody();
  let el = cursor.getElement();
  while (el.getParent() && el.getParent().getType() !== DocumentApp.ElementType.BODY_SECTION) {
    el = el.getParent();
  }
  const pos = body.getChildIndex(el);
  const above = headingIndex().filter(function (h) { return h.index <= pos; });
  if (!above.length) {
    ui.alert("There is no heading above the cursor.");
    return;
  }
  reviewEntry(above[above.length - 1]);
}

// Reviews a section by heading name. Accepts a bare heading ("Switch Plan") or
// a path when the same heading appears under several platforms
// ("OTT > Switch Plan").
function reviewHeadingSection() {
  const ui = DocumentApp.getUi();
  const index = headingIndex();
  const hint = index.length
    ? "Headings in this doc:\n• " +
      index.slice(0, 20).map(function (h) { return h.path; }).join("\n• ") +
      (index.length > 20 ? "\n• …" : "") +
      '\n\nType a heading, or a path when the same heading appears under several platforms (e.g. "OTT > Switch Plan"):'
    : "Type the heading exactly as it appears in the doc:";

  const resp = ui.prompt("Review a section", hint, ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  const query = resp.getResponseText().trim();
  if (!query) return;

  const shown = query.length > 60 ? query.slice(0, 60) + "…" : query;
  const matches = findHeadings(index, query);
  if (!matches.length) {
    ui.alert('No heading matching "' + shown + '" was found (check spelling/case).');
    return;
  }
  if (matches.length > 1) {
    ui.alert(
      '"' + shown + '" matches more than one section. Use one of these paths:\n• ' +
      matches.map(function (h) { return h.path; }).join("\n• ")
    );
    return;
  }
  reviewEntry(matches[0]);
}

// Sends one indexed section for review, prefixed with its breadcrumb so the
// reviewer knows which platform/flow the payload belongs to.
function reviewEntry(entry) {
  const text = sectionTextAt(entry);
  sendForReview(
    text ? "Section: " + entry.path + "\n\n" + text : "",
    'The section under "' + entry.path + '" is empty.'
  );
}

// ---------- Text extraction ----------

// Pulls out whatever the user has highlighted.
function getSelectedText() {
  const selection = DocumentApp.getActiveDocument().getSelection();
  if (!selection) return "";

  const parts = [];
  selection.getRangeElements().forEach(function (rangeEl) {
    const el = rangeEl.getElement();
    if (!el.editAsText) return;
    const fullText = el.asText().getText();
    if (rangeEl.isPartial()) {
      parts.push(
        fullText.substring(rangeEl.getStartOffset(), rangeEl.getEndOffsetInclusive() + 1)
      );
    } else if (fullText.trim()) {
      parts.push(fullText);
    }
  });
  return parts.join("\n");
}

// Every heading in document order with its breadcrumb path, e.g.
// { index: 42, level: 2, text: "Switch Plan",
//   parts: ["OTT", "Switch Plan"], path: "OTT > Switch Plan" }
// `index` is the heading's position among the body's top-level children.
function headingIndex() {
  const body = DocumentApp.getActiveDocument().getBody();
  const out = [];
  const stack = [];
  for (let i = 0; i < body.getNumChildren(); i++) {
    const el = body.getChild(i);
    const type = el.getType();
    if (type !== DocumentApp.ElementType.PARAGRAPH && type !== DocumentApp.ElementType.LIST_ITEM) continue;
    const level = headingLevel(el.getHeading());
    if (level === null) continue;
    const text = el.getText().trim();
    if (!text) continue;
    while (stack.length && stack[stack.length - 1].level >= level) stack.pop();
    stack.push({ level: level, text: text });
    const parts = stack.map(function (h) { return h.text; });
    out.push({ index: i, level: level, text: text, parts: parts, path: parts.join(" > ") });
  }
  return out;
}

// Matches a bare heading ("Switch Plan") or a path suffix ("OTT > Switch Plan",
// "OTT / Switch Plan"), case-insensitively.
function findHeadings(index, query) {
  const want = query.toLowerCase().split(/\s*[>\/]\s*/).filter(Boolean);
  return index.filter(function (h) {
    const have = h.parts.map(function (p) { return p.toLowerCase(); });
    if (want.length > have.length) return false;
    const tail = have.slice(have.length - want.length);
    return want.every(function (w, k) { return tail[k] === w; });
  });
}

// Text of everything after the heading until the next heading of the same or
// higher level. Walks the body's top-level children so tables inside the
// section are included.
function sectionTextAt(entry) {
  const body = DocumentApp.getActiveDocument().getBody();
  const parts = [];
  for (let i = entry.index + 1; i < body.getNumChildren(); i++) {
    const el = body.getChild(i);
    const type = el.getType();
    if (type === DocumentApp.ElementType.PARAGRAPH || type === DocumentApp.ElementType.LIST_ITEM) {
      const level = headingLevel(el.getHeading());
      if (level !== null && level <= entry.level) break;
    }
    const t = el.getText ? el.getText() : "";
    if (t && t.trim()) parts.push(t);
  }
  return parts.join("\n");
}

// Maps ParagraphHeading to a number (0 = title, 1 = biggest heading).
// Returns null for normal text.
function headingLevel(heading) {
  const H = DocumentApp.ParagraphHeading;
  switch (heading) {
    case H.TITLE: return 0;
    case H.HEADING1: return 1;
    case H.HEADING2: return 2;
    case H.HEADING3: return 3;
    case H.HEADING4: return 4;
    case H.HEADING5: return 5;
    case H.HEADING6: return 6;
    default: return null;
  }
}

// ---------- Shared: send to the review endpoint + show sidebar ----------

function sendForReview(text, emptyMessage) {
  const ui = DocumentApp.getUi();
  if (!text || !text.trim()) {
    ui.alert(emptyMessage);
    return;
  }

  let findings;
  try {
    const response = UrlFetchApp.fetch(ENDPOINT_URL, {
      method: "post",
      contentType: "application/json",
      headers: { "ngrok-skip-browser-warning": "true" },
      payload: JSON.stringify({ text: text }),
      muteHttpExceptions: true,
    });
    const code = response.getResponseCode();
    const body = response.getContentText();
    findings =
      code === 200
        ? JSON.parse(body).findings || "(no findings returned)"
        : "Review service returned HTTP " + code + ":\n\n" + body;
  } catch (e) {
    findings = "Could not reach the review service:\n\n" + e;
  }

  showSidebar(findings);
}

function showSidebar(findings) {
  const template = HtmlService.createTemplateFromFile("Sidebar");
  template.findings = findings;
  DocumentApp.getUi().showSidebar(template.evaluate().setTitle("Spec Review"));
}
