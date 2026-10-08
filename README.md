# Standardization Bot (POC)

A Slack bot that runs two independent first-pass checks on tracking specs,
powered by Gemini on Vertex AI. Reviews are tracked in a local database, and
both checks are also exposed as HTTP endpoints via a small Flask server —
which is how the bot runs inside Google Docs as a sidebar (see
[Google Docs integration](#5-google-docs-integration)).

1. **Spec doc check** — DM a PDF/.docx spec (or `/review-spec <text>`). Checks
   the spec's variables against prior specs read from a Google Drive folder
   (default: *P+ MON Active Specs*): does each variable already exist, do its
   values match established usage, and what values should blank/TBD variables
   take.
2. **Vendor privacy lookup** — DM the vendors you're tracking for (or
   `/vendor-check Conviva, Branch, ...`). For each vendor, returns from the
   [OneTrust 3rd Party Vendors](https://paramount.atlassian.net/wiki/spaces/CDMMO/pages/65778526/OneTrust+3rd+Party+Vendors)
   Confluence page: the OneTrust category, adult-profile rules for Web and
   Native/OTT apps, and kids profile / kids content rules for all platforms.

> POC / triage aid only — not a substitute for legal or privacy-team review.

## How it works

```
Slack DM: file or /review-spec ──────▶ spec_check ───▶ prior specs (Google Drive,
Slack DM: text or /vendor-check ─────▶ vendor_check ─▶ OneTrust page (Confluence)   fallback: references/)
Google Doc sidebar ─▶ ngrok ─▶ HTTP ─┘      │
                                 gemini_client.py ─▶ Vertex AI (Gemini)
                                            │
                                     storage.py (SQLite)
```

Each check is independent and grounded only in its own source material.
Reference material is cached in memory — restart the bot to pick up new Drive
files or an updated Confluence page.

**Latency.** The first review after startup uploads the grounding material to
a [Vertex context cache](https://cloud.google.com/vertex-ai/generative-ai/docs/context-cache/context-cache-overview)
(takes roughly as long as one old-style review). Every review after that sends
only the spec under review and references the cache by ID, so Gemini doesn't
re-read every prior spec each time. The cache expires after
`GEMINI_CACHE_TTL_SECONDS` (default 6h) and is recreated on the next request;
if caching is unavailable the bot silently falls back to inline grounding.
Gemini's internal "thinking" is off by default (`GEMINI_THINKING_BUDGET=0`),
which is the other big time saver for this kind of lookup task.

## Prerequisites

- Python 3.10+
- Google Cloud Application Default Credentials **with the Drive read scope**
  (the default `gcloud auth application-default login` only grants
  `cloud-platform`, which isn't enough to read the specs folder):

  ```bash
  gcloud auth application-default login \
      --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.readonly
  ```
- A Slack workspace where you can create an app
- (For the vendor lookup) an Atlassian API token — generate one at
  https://id.atlassian.com/manage-profile/security/api-tokens

## 1. Create the Slack app

1. Go to https://api.slack.com/apps → **Create New App** → **From scratch**.
2. Enable **Socket Mode** (*Settings* → *Socket Mode*) — no public URL needed.
3. Under *OAuth & Permissions*, add the bot scopes: `chat:write`, `commands`,
   `files:read`, `app_mentions:read`, `im:history`.
4. Under *Event Subscriptions*, subscribe to the bot events `app_mention` and
   `message.im`.
5. Under *Slash Commands*, create `/review-spec`, `/vendor-check`, and
   `/spec-log`.
6. **Install to Workspace**, then grab:
   - **Bot User OAuth Token** (`xoxb-…`) from *OAuth & Permissions* → `SLACK_BOT_TOKEN`
   - **App-Level Token** (`xapp-…`): *Basic Information* → *App-Level Tokens* →
     generate one with the `connections:write` scope → `SLACK_APP_TOKEN`

## 2. Configure

Create a `.env` in the project root (see `config.py` for every setting and
its default):

```bash
# Slack (required)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Vertex AI / Gemini (defaults shown)
GOOGLE_CLOUD_PROJECT=i-digmops
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash
# Latency: 0 disables Gemini 2.5 "thinking" (fastest); context caching uploads
# the prior specs to Vertex once so each review only sends the spec itself.
GEMINI_THINKING_BUDGET=0
GEMINI_USE_CONTEXT_CACHE=1
GEMINI_CACHE_TTL_SECONDS=21600

# Prior specs — Google Drive folder. Set the folder ID (from the folder URL:
# .../folders/<ID>) or leave blank to look it up by name.
GDRIVE_FOLDER_ID=
GDRIVE_FOLDER_NAME=P+ MON Active Specs

# Confluence (required for the vendor privacy lookup)
CONFLUENCE_BASE_URL=https://paramount.atlassian.net/wiki
CONFLUENCE_EMAIL=you@paramount.com
CONFLUENCE_API_TOKEN=...
CONFLUENCE_PAGE_ID=65778526
```

If Drive isn't configured or reachable, the spec check falls back to a local
folder of prior specs (`REFERENCES_DIR`, default `references/` — supports
.pdf, .docx, .txt, .md). If Confluence isn't configured, the vendor lookup is
skipped with a warning.

## 3. Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

You should see: `Privacy specs bot is running (Socket Mode).`

### Optional: HTTP endpoints

`server.py` wraps the same review engine in a Flask app (no Slack needed):

```bash
python server.py   # listens on 0.0.0.0:8080

curl -X POST localhost:8080/review \
     -H 'Content-Type: application/json' \
     -d '{"text": "Set userType to... and fire trackPageView when..."}'

curl -X POST localhost:8080/vendor-check \
     -H 'Content-Type: application/json' \
     -d '{"text": "Conviva, Branch"}'
```

`GET /health` returns `ok`. It binds to `0.0.0.0` so a tunnel (e.g. ngrok)
can reach it.

## 4. Try it in Slack

- DM the bot a PDF or .docx spec — spec doc check
- DM the bot `Conviva, Branch, Adobe Analytics` — vendor privacy lookup
- `/review-spec Set userType to... and fire trackPageView when...`
- `/vendor-check Conviva, Kochava`
- `/spec-log` — list recent reviews
- `@privacy-specs-bot` — help text

> **Note:** slash commands only work once registered in your Slack app
> settings (step 5 above). DM'd files and text work without any of that setup.

## 5. Google Docs integration

The same checks run inside a Google Doc via an Apps Script sidebar that
POSTs the doc's text to the Flask endpoints. Three pieces:

1. **The Flask server** — `python server.py` (see above).
2. **A tunnel**, since Apps Script runs on Google's servers and can't reach
   `localhost`:

   ```bash
   ngrok http 8080
   ```

   Note the public URL it prints (e.g. `https://<something>.ngrok-free.dev`).
   On the free plan this URL **changes every time ngrok restarts** — update
   the Apps Script constant (below) when it does.
3. **The Apps Script** — in the spec doc (or a template copies inherit
   from): *Extensions → Apps Script*, then:

   ```javascript
   const REVIEW_URL = 'https://<your-ngrok-url>/review';

   function onOpen() {
     DocumentApp.getUi()
       .createMenu('Spec check')
       .addItem('Review this spec', 'reviewSpec')
       .addToUi();
   }

   function reviewSpec() {
     const text = DocumentApp.getActiveDocument().getBody().getText();
     const resp = UrlFetchApp.fetch(REVIEW_URL, {
       method: 'post',
       contentType: 'application/json',
       payload: JSON.stringify({ text: text }),
       muteHttpExceptions: true,
     });
     const findings = JSON.parse(resp.getContentText()).findings ||
       resp.getContentText();
     const html = HtmlService
       .createHtmlOutput('<pre style="white-space:pre-wrap">' + findings + '</pre>')
       .setTitle('Spec check');
     DocumentApp.getUi().showSidebar(html);
   }
   ```

   First run prompts for authorization (external URL fetch + doc access).
   After that, reviewers get a **Spec check** menu in the doc and results in
   a sidebar — no Slack needed.

Troubleshooting:

- **502 from the ngrok URL** — ngrok is up but `server.py` isn't running (or
  wasn't started from the venv). Restart it: `source .venv/bin/activate &&
  python server.py`.
- **"Address already in use"** — an old `server.py` is still running; kill it
  first (`pkill -f server.py`).
- **Script error about the URL** — the ngrok URL rotated; update `REVIEW_URL`.

## Where to customize

- **`compliance/prompts.py`** — one prompt per check (`SPEC_CHECK_*` and
  `VENDOR_CHECK_*`) plus output format. This is the highest-leverage file; tune
  each to how your team actually reviews.
- **`config.py` / `.env`** — model, region, project, Drive folder, Confluence
  page. Bump `GEMINI_MODEL` when you want a stronger model (e.g.
  `gemini-2.5-pro`).
- **`storage.py`** — swap SQLite for Airtable / Postgres / a Google Sheet for a
  shared, queryable tracker. Keep the function signatures and handlers won't change.

## Possible next steps

- Post reviews as threaded replies in a dedicated #spec-review channel
- Add a reviewer sign-off / status field to the tracker
- Refresh cached Drive/Confluence reference material without a restart
