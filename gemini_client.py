"""Thin wrapper around the Vertex AI Gemini API."""
from google import genai
from google.genai import types

import config

_client = genai.Client(
    vertexai=True,
    project=config.GOOGLE_CLOUD_PROJECT,
    location=config.GOOGLE_CLOUD_LOCATION,
)


def _as_part(x):
    """Normalize a str or Part into a Part."""
    if isinstance(x, str):
        return types.Part.from_text(text=x)
    return x


def _generate(contents, system_instruction: str, temperature: float = 0.2):
    response = _client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        ),
    )
    return (response.text or "").strip() or "_(model returned no text)_"


def review(
    spec_part,
    grounding_header: str,
    grounding_parts: list,
    instruction: str,
    system_instruction: str,
    temperature: float = 0.2,
    subject_header: str = "SPEC UNDER REVIEW",
):
    """Assemble grounding material + the subject into one grounded request.

    `spec_part` and each `grounding_parts` item may be a str or a Part
    (e.g. a PDF sent as bytes).
    """
    contents = []

    if grounding_parts:
        contents.append(_as_part(f"=== {grounding_header} ==="))
        contents.extend(_as_part(p) for p in grounding_parts)
    else:
        contents.append(
            _as_part(
                f"=== {grounding_header} ===\n"
                "(none available — note this in your review)"
            )
        )

    contents.append(_as_part(f"=== {subject_header} ==="))
    contents.append(_as_part(spec_part))
    contents.append(_as_part(instruction))

    return _generate(contents, system_instruction, temperature)