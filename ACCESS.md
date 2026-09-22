# Standardization Bot — Getting Access

How to get set up with the bot, depending on what you need to do. Most
people only need Level 1 or 2. For how to *use* the bot once you have
access, see the [User Guide](USER_GUIDE.md).

**Contact for all access requests: Max Fan (max.fan@paramount.com).**

> The bot is a proof of concept and currently runs on the maintainer's
> machine — if it isn't responding, it probably isn't running. Ping Max.

---

## Level 1 — Use the bot in Slack

**Who this is for:** anyone reviewing or writing tracking specs.

What you need:

1. **Paramount Slack workspace account** — you almost certainly already
   have this.
2. **Find the bot:** search for `privacy-specs-bot` in Slack and open a DM.
   If you can't find it, ask Max to confirm the app is installed and running.

That's it — DM the bot a PDF/.docx spec or a vendor list. No sign-up,
tokens, or permissions needed.

To use the slash commands (`/review-spec`, `/vendor-check`, `/spec-log`) in
a **channel**, the bot has to be a member — invite it with
`/invite @privacy-specs-bot`, or just use DMs.

## Level 2 — Use the spec check inside Google Docs

**Who this is for:** spec authors who want the "Spec check" menu in their
spec doc.

What you need:

1. **Access to a spec doc (or the spec template) that has the script
   installed.** New docs copied from the template inherit it. If your doc
   doesn't have the *Spec check* menu, ask Max to add the script or share
   the template.
2. **One-time authorization:** the first time you run *Spec check → Review
   this spec*, Google shows an authorization prompt (the script reads the
   doc and calls an external review service). Accept it — this is per-user,
   per-script.
3. The review service must be up (it runs on the maintainer's machine). If
   you get an error or a 502 page, tell Max — nothing on your end is wrong.

## Level 3 — Run the bot on your own machine

**Who this is for:** developers running their own instance or making
changes.

Once you have a copy of the code, everything else is set up under **your
own accounts** — no shared tokens, and nothing to request from Max. Your
instance is fully independent (its own Slack bot, its own review log).

| Credential | What it's for | How to get your own |
|---|---|---|
| `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` | Your bot's Slack identity | Create your own Slack app at api.slack.com/apps and install it to the workspace — README §1 walks through it (Socket Mode, scopes, slash commands). Your tokens come from your app's settings pages. |
| Google Cloud ADC | Vertex AI (Gemini) calls | `gcloud auth application-default login` with your Paramount account. Set `GOOGLE_CLOUD_PROJECT` in `.env` to a GCP project where you have Vertex AI access (any project with the Vertex AI API enabled works). |
| `CONFLUENCE_API_TOKEN` | OneTrust vendor page lookup | Generate your own at id.atlassian.com/manage-profile/security/api-tokens — self-service, as long as your account can view the [OneTrust vendors page](https://paramount.atlassian.net/wiki/spaces/CDMMO/pages/65778526/OneTrust+3rd+Party+Vendors) |
| Prior specs (reference library) | Grounding for the spec check | The bot reads specs straight from the "P+ MON Active Specs" shared-drive folder via the Drive API, authenticated as a **service account**: create one in your GCP project (IAM & Admin → Service Accounts), download its JSON key, and set `GDRIVE_SERVICE_ACCOUNT_KEY` in `.env` to the key file's path. Then ask a manager of that shared drive to share the folder (Viewer) with the service account's `client_email` (it's in the JSON key). Leave `GDRIVE_FOLDER_NAME=P+ MON Active Specs`, or set `GDRIVE_FOLDER_ID` from the folder's URL. If Drive is unreachable, the bot falls back to a local `references/` folder of .docx/PDF files. |
| Corporate VPN CA bundle | Google/Drive API calls from the VPN | If you're on the corporate VPN, TLS interception breaks Google API calls (certificate errors). Build a combined CA bundle and point `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` in `.env` at it: `cat $(python -c 'import certifi;print(certifi.where())') <(security find-certificate -a -p /Library/Keychains/System.keychain) > ca-bundle.pem` |
| ngrok (optional) | Google Docs sidebar endpoint | Only if you're hosting the Docs integration — free account at ngrok.com/download |

Then follow the [README](README.md) end to end: create your `.env`,
`pip install -r requirements.txt`, and run `python app.py` (Slack) and/or
`python server.py` + ngrok (Google Docs).

> **First startup is slow on purpose.** `server.py` loads every reference
> spec from Google Drive before it starts serving — expect a few minutes of
> "Loading reference specs…" before you see "Serving." Later requests are
> fast (the specs are cached in memory; restart to pick up new ones).

> **Don't reuse someone else's Slack tokens.** If two machines run the bot
> with the same tokens, Slack splits events between them and each instance
> sees only some messages — it looks like the bot is randomly ignoring
> people. One Slack app per running instance.

---

## Quick reference

| I want to… | I need… | Ask |
|---|---|---|
| Check specs in Slack | Nothing — DM the bot | Max if bot is unresponsive |
| Spec check menu in my Google Doc | Doc/template with the script | Max |
| Run my own instance | The code + my own credentials (table above) | Nobody — all self-service |
