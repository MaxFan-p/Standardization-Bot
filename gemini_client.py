"""Thin wrapper around the Vertex AI Gemini API.

Two latency optimizations live here:
  • Context caching — grounding material (prior specs, OneTrust page) is
    uploaded to Vertex once per process and referenced by cache ID, so each
    request sends only the subject (the spec under review). Falls back to
    sending everything inline if the cache can't be created or has expired.
  • Thinking budget — disabled by default (config.GEMINI_THINKING_BUDGET).
"""
import datetime as dt
import logging
import threading
import time

from google import genai
from google.genai import types

import config

log = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=config.GOOGLE_CLOUD_PROJECT,
    location=config.GOOGLE_CLOUD_LOCATION,
)

# cache_key -> {"name": str, "expires": float} or {"retry_after": float}
_caches: dict = {}
_cache_lock = threading.Lock()
_CACHE_RETRY_BACKOFF = 15 * 60  # seconds to wait before retrying a failed create
_CACHE_EXPIRY_SLACK = 120       # recreate this many seconds before Vertex expires it


def _as_part(x):
    """Normalize a str or Part into a Part."""
    if isinstance(x, str):
        return types.Part.from_text(text=x)
    return x


def _gen_config(system_instruction=None, cached_content=None, temperature=0.2):
    kwargs = dict(
        temperature=temperature,
        max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
        thinking_config=types.ThinkingConfig(
            thinking_budget=config.GEMINI_THINKING_BUDGET
        ),
    )
    # Vertex rejects a system_instruction alongside cached_content — the
    # cache already carries it.
    if cached_content:
        kwargs["cached_content"] = cached_content
    else:
        kwargs["system_instruction"] = system_instruction
    return types.GenerateContentConfig(**kwargs)


def _generate(contents, system_instruction, temperature=0.2, cached_content=None):
    response = _client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=contents,
        config=_gen_config(system_instruction, cached_content, temperature),
    )
    return (response.text or "").strip() or "_(model returned no text)_"


# --- Context cache -----------------------------------------------------------

def _get_or_create_cache(key: str, grounding_contents: list, system_instruction: str):
    """Return a live cached-content name for `key`, or None if unavailable."""
    if not config.GEMINI_USE_CONTEXT_CACHE:
        return None

    now = time.time()
    with _cache_lock:
        entry = _caches.get(key)
        if entry:
            if "name" in entry and entry["expires"] - _CACHE_EXPIRY_SLACK > now:
                return entry["name"]
            if "retry_after" in entry and entry["retry_after"] > now:
                return None

        try:
            t0 = time.time()
            cache = _client.caches.create(
                model=config.GEMINI_MODEL,
                config=types.CreateCachedContentConfig(
                    display_name=key,
                    contents=[types.Content(role="user", parts=grounding_contents)],
                    system_instruction=system_instruction,
                    ttl=f"{config.GEMINI_CACHE_TTL_SECONDS}s",
                ),
            )
            expires = (
                cache.expire_time.timestamp()
                if cache.expire_time
                else now + config.GEMINI_CACHE_TTL_SECONDS
            )
            _caches[key] = {"name": cache.name, "expires": expires}
            log.info(
                "Created context cache %r (%s) in %.1fs; expires %s",
                key, cache.name, time.time() - t0,
                dt.datetime.fromtimestamp(expires).isoformat(timespec="minutes"),
            )
            return cache.name
        except Exception:  # noqa: BLE001
            log.exception(
                "Context cache %r unavailable; sending grounding inline for %d min",
                key, _CACHE_RETRY_BACKOFF // 60,
            )
            _caches[key] = {"retry_after": now + _CACHE_RETRY_BACKOFF}
            return None


def _invalidate_cache(key: str):
    with _cache_lock:
        _caches.pop(key, None)


# --- Public API --------------------------------------------------------------

def _grounding_contents(grounding_header: str, grounding_parts: list) -> list:
    grounding = [_as_part(f"=== {grounding_header} ===")]
    grounding.extend(_as_part(p) for p in grounding_parts)
    return grounding


def warm_cache(cache_key: str, grounding_header: str, grounding_parts: list, system_instruction: str):
    """Pre-create the context cache for `cache_key` (no-op if caching is off)."""
    if grounding_parts:
        _get_or_create_cache(
            cache_key, _grounding_contents(grounding_header, grounding_parts), system_instruction
        )


def review(
    spec_part,
    grounding_header: str,
    grounding_parts: list,
    instruction: str,
    system_instruction: str,
    temperature: float = 0.2,
    subject_header: str = "SPEC UNDER REVIEW",
    cache_key: str | None = None,
):
    """Assemble grounding material + the subject into one grounded request.

    `spec_part` and each `grounding_parts` item may be a str or a Part
    (e.g. a PDF sent as bytes). If `cache_key` is given and caching is
    enabled, the grounding material is served from a Vertex context cache.
    """
    subject = [
        _as_part(f"=== {subject_header} ==="),
        _as_part(spec_part),
        _as_part(instruction),
    ]

    if grounding_parts:
        grounding = _grounding_contents(grounding_header, grounding_parts)
    else:
        grounding = [
            _as_part(
                f"=== {grounding_header} ===\n"
                "(none available — note this in your review)"
            )
        ]
        cache_key = None  # nothing worth caching

    if cache_key:
        name = _get_or_create_cache(cache_key, grounding, system_instruction)
        if name:
            try:
                return _generate(subject, system_instruction, temperature, cached_content=name)
            except Exception:  # noqa: BLE001
                log.exception(
                    "Cached generate failed for %r; retrying inline", cache_key
                )
                _invalidate_cache(cache_key)

    return _generate(grounding + subject, system_instruction, temperature)
