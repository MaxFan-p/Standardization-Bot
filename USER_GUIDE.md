# Standardization Bot — Team User Guide

The Standardization Bot is a Slack bot that gives you a fast, automated
first-pass review of tracking specs before implementation. It does two
independent checks:

1. **Spec doc check** — compares a spec's variables and values against our
   library of previously approved specs and flags anything new or
   inconsistent, so naming stays standardized across P+ implementations.
2. **Vendor privacy lookup** — looks up vendors on the
   [OneTrust 3rd Party Vendors](https://paramount.atlassian.net/wiki/spaces/CDMMO/pages/65778526/OneTrust+3rd+Party+Vendors)
   Confluence page and returns each vendor's OneTrust category and
   profile/content rules.

> ⚠️ This is a proof-of-concept triage aid. It does **not** replace review by
> the Privacy team or a human spec reviewer — treat its output as a first
> pass, not a sign-off.

---

## 1. Check a spec

**Easiest way:** open a DM with the bot and upload your spec as a **PDF** or
**.docx** file. The bot replies in the DM with its findings.

**Or paste text** with the slash command (works in any channel where the bot
is installed):

```
/review-spec Set userType to "guest" and fire trackPageView when the paywall loads...
```

### What you get back

- **Verdict** — one line: *Consistent* or *Needs changes*, and why.
- **Value check** — for each variable with a value:
  - ✅ **previously used** — the exact value appears in prior specs (cited).
  - 🆕 **new** — the value has never been used before. If prior specs use a
    similar value (different casing, wording, format), the bot suggests
    aligning with it.
- **Suggested values** — for variables left blank, marked TBD, or
  inconsistent with prior specs: the value prior specs support, and where it
  comes from.

### Tips

- The bot reads tables in .docx files, so specs with variable tables work well.
- Only PDF and .docx are supported — other file types are rejected. For a
  native Google Doc, download it as .docx first (File → Download → Microsoft
  Word) or paste the relevant text into `/review-spec`.

## 2. Look up vendor privacy rules

DM the bot a plain list of the vendors you're implementing tracking for:

```
Conviva, Branch, Adobe Analytics
```

Or use the slash command:

```
/vendor-check Conviva, Kochava
```

For **each vendor** you get, straight from the OneTrust Confluence page:

- **OneTrust category** (e.g. Category 2 – Analytics)
- **Adult profile — Web** rules (consent/CMP behavior, flags, load conditions)
- **Adult profile — Native/OTT apps** rules
- **Kids profile / kids content** rules (all platforms)

Vendor names are matched loosely — "Adobe" will return every matching Adobe
row. If a vendor isn't on the page, the bot says exactly that and flags it
for Privacy-team review. It never guesses a category.

## 3. Other commands

| Where | What | Result |
|---|---|---|
| DM | Upload a PDF/.docx | Spec doc check |
| DM | Type a vendor list | Vendor privacy lookup |
| Any channel | `/review-spec <spec text>` | Spec doc check on pasted text |
| Any channel | `/vendor-check <vendors>` | Vendor privacy lookup |
| Any channel | `/spec-log` | List of recent reviews (who, when, what) |
| Any channel | `@privacy-specs-bot` | Help text |

---

## Good to know

- **Where the "prior specs" come from:** the *P+ MON Active Specs* folder on
  the Tracking Specs shared drive. If the bot says it has no prior specs
  available, the reference library isn't loading — tell the bot's maintainer
  (currently Max Fan).
- **New specs aren't picked up automatically.** Reference material is loaded
  once when the bot starts. If a spec was recently added to the folder, ask
  the maintainer to restart the bot.
- **Every review is logged** (who ran it, when, and the finding) — that's
  what `/spec-log` shows.
- **The bot only answers in DMs and where it's invited.** If a slash command
  doesn't work in a channel, the bot may not be added there — DM it instead.
- **If the bot doesn't respond at all**, it's probably not running — contact
  the maintainer.

## For developers / maintainers

Setup, configuration, and architecture live in the project
[README](README.md). Quick reference:

- Run the Slack bot: `source .venv/bin/activate && python app.py`
- The same checks are exposed over HTTP by `server.py` (port 8080) for
  non-Slack integrations (e.g. the Google Docs sidebar via ngrok).
- Prompts and output format: `compliance/prompts.py`
- Model/project/folder settings: `.env` / `config.py`
