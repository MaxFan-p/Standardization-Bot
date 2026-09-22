"""Slash command handlers."""
import logging

import storage
from handlers.events import run_spec_check, run_vendor_check

log = logging.getLogger(__name__)


def register(app):
    @app.command("/review-spec")
    def handle_review_spec(ack, respond, command):
        ack()

        spec_text = (command.get("text") or "").strip()
        if not spec_text:
            respond(
                "Paste the spec text after the command, or DM me a PDF/.docx file.\n"
                "e.g. `/review-spec Set userType to... and fire trackPageView when...`"
            )
            return

        run_spec_check(
            spec_text,
            "pasted spec",
            spec_text,
            command.get("user_id", ""),
            command.get("channel_id", ""),
            respond,
            log,
        )

    @app.command("/vendor-check")
    def handle_vendor_check(ack, respond, command):
        ack()

        vendors_text = (command.get("text") or "").strip()
        if not vendors_text:
            respond(
                "Name the vendors you're tracking for, e.g. "
                "`/vendor-check Conviva, Branch, Adobe Analytics`"
            )
            return

        run_vendor_check(
            vendors_text,
            command.get("user_id", ""),
            command.get("channel_id", ""),
            respond,
            log,
        )

    @app.command("/spec-log")
    def handle_spec_log(ack, respond, command):
        ack()
        rows = storage.list_reviews()
        if not rows:
            respond("No specs reviewed yet.")
            return
        lines = ["*Recent spec reviews:*"]
        for rid, created_at, user_id, snippet in rows:
            lines.append(f"• `#{rid}` {created_at[:10]} — <@{user_id}> — {snippet}…")
        respond("\n".join(lines))
