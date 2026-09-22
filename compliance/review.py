"""Orchestrates the two grounded checks.

Each check is independent — it gets only its own grounding material:
  • spec_check   → prior specs from REFERENCES_DIR (variable names & values)
  • vendor_check → OneTrust 3rd Party Vendors page from Confluence
                   (category + adult-profile + kids-content rules per vendor)
"""
from google.genai import types

import gemini_client
import references_loader
from compliance.prompts import (
    SPEC_CHECK_INSTRUCTION,
    SPEC_CHECK_SYSTEM_PROMPT,
    VENDOR_CHECK_INSTRUCTION,
    VENDOR_CHECK_SYSTEM_PROMPT,
)


def pdf_part(pdf_bytes: bytes):
    """Wrap raw PDF bytes so Gemini reads the document natively."""
    return types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")


def spec_check(spec_part):
    """Check the spec's variables against prior specs (names, values, reuse)."""
    refs = references_loader.load_reference_specs()
    return gemini_client.review(
        spec_part=spec_part,
        grounding_header="PRIOR SPECS (source of truth for variable names and values)",
        grounding_parts=refs,
        instruction=SPEC_CHECK_INSTRUCTION,
        system_instruction=SPEC_CHECK_SYSTEM_PROMPT,
    )


def vendor_check(vendors_text: str):
    """Look up the requested vendors' OneTrust category and profile rules."""
    page = references_loader.load_onetrust_vendors()
    return gemini_client.review(
        spec_part=vendors_text,
        grounding_header=(
            "ONETRUST 3RD-PARTY VENDORS (authoritative, from Confluence; HTML)"
        ),
        grounding_parts=[page] if page else [],
        instruction=VENDOR_CHECK_INSTRUCTION,
        system_instruction=VENDOR_CHECK_SYSTEM_PROMPT,
        subject_header="VENDORS REQUESTED",
    )
