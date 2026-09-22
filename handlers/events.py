"""Event handlers: mentions and DMs (file uploads → spec check, text → vendor lookup)."""
import storage
from compliance import review

HELP_TEXT = (
    "Hi! I do two things:\n"
    "• *Spec doc check* — DM me a *PDF* or *.docx* spec (or "
    "`/review-spec <paste text>`) and I'll check its variables against prior "
    "specs: do they exist, do the values match, what values to use.\n"
    "• *Vendor privacy lookup* — DM me the vendors you're tracking for (e.g. "
    "`Conviva, Branch, Adobe Analytics`) and I'll return each one's OneTrust "
    "category, adult-profile rules (Web + Native/OTT apps), and kids-content "
    "rules for all platforms, from the OneTrust 3rd Party Vendors page.\n"
    "• `/spec-log` — recent activity"
)


def register(app):
    @app.event("app_mention")
    def handle_mention(event, say):
        say(HELP_TEXT)

    @app.event("message")
    def handle_message(event, say, logger):
        if event.get("channel_type") != "im" or event.get("bot_id"):
            return

        files = event.get("files") or []
        if files:
            for f in files:
                _spec_check_file(f, event, say, logger)
            return

        text = (event.get("text") or "").strip()
        if not text:
            say(HELP_TEXT)
            return
        run_vendor_check(text, event.get("user", ""), event.get("channel", ""), say, logger)

    def _spec_check_file(f, event, say, logger):
        name = f.get("name", "document")
        filetype = (f.get("filetype") or "").lower()
        url = f.get("url_private_download") or f.get("url_private")

        import extract

        try:
            data = extract.download_slack_file(url)

            if filetype == "pdf":
                spec_part = review.pdf_part(data)
                logged_text = f"[PDF upload: {name}]"
            elif filetype == "docx":
                text = extract.extract_docx_text(data)
                if not text.strip():
                    say(f":warning: Couldn't extract any text from *{name}*.")
                    return
                spec_part = text
                logged_text = text
            else:
                say(
                    f":warning: *{name}* is a `.{filetype}` file — "
                    "I only review PDF and .docx specs."
                )
                return
        except Exception as e:  # noqa: BLE001
            logger.exception("File download/extract failed")
            say(f":warning: Couldn't read *{name}*: `{e}`")
            return

        run_spec_check(
            spec_part, name, logged_text, event.get("user", ""), event.get("channel", ""), say, logger
        )


def run_spec_check(spec_part, name, logged_text, user_id, channel_id, say, logger):
    """Run the spec doc check (variables vs prior specs) and post the result."""
    say(f":mag: Running *spec doc check* on *{name}* (variables vs prior specs)…")
    try:
        findings = review.spec_check(spec_part)
    except Exception as e:  # noqa: BLE001
        logger.exception("Spec doc check failed")
        say(f":warning: Spec doc check of *{name}* failed: `{e}`")
        return
    say(f"*Spec doc check — {name}*\n{findings}")
    storage.save_review(user_id, channel_id, logged_text, findings)


def run_vendor_check(vendors_text, user_id, channel_id, say, logger):
    """Look up the requested vendors on the OneTrust page and post the result."""
    say(
        ":lock: Looking up *OneTrust rules* for: "
        f"_{vendors_text[:200]}_ …"
    )
    try:
        findings = review.vendor_check(vendors_text)
    except Exception as e:  # noqa: BLE001
        logger.exception("Vendor lookup failed")
        say(f":warning: Vendor lookup failed: `{e}`")
        return
    say(findings)
    storage.save_review(user_id, channel_id, f"[vendor lookup] {vendors_text}", findings)
