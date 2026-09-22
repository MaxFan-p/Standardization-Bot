"""Loads reference material once per process.

Two independent sources, one per check:
  • prior specs (Google Drive folder, read via the Drive API;
    falls back to local REFERENCES_DIR)        → spec doc check
  • OneTrust vendor list (Confluence)          → privacy check

Cached in memory — restart the bot to pick up new reference files or an
updated Confluence page.
"""
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from google.genai import types

import config
import confluence
import extract
import gdrive

log = logging.getLogger(__name__)

_cache: dict = {}
_specs_lock = threading.Lock()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
FETCH_WORKERS = 8


def load_onetrust_vendors():
    """Return the OneTrust 3rd Party Vendors page HTML (or None)."""
    if "onetrust_vendors" not in _cache:
        _cache["onetrust_vendors"] = confluence.fetch_onetrust_vendors()
    return _cache["onetrust_vendors"]


def load_reference_specs():
    """Return a list of Gemini parts, one per reference spec.

    Thread-safe and single-flight: concurrent callers block until the first
    load finishes, then all share the cached result.
    """
    if "specs" in _cache:
        return _cache["specs"]

    with _specs_lock:
        if "specs" in _cache:
            return _cache["specs"]

        try:
            parts = _load_from_drive()
        except Exception:  # noqa: BLE001
            log.exception("Drive load failed; falling back to local REFERENCES_DIR.")
            parts = _load_from_local_dir()

        _cache["specs"] = parts
    return parts


# --- Google Drive (primary) --------------------------------------------------

def _load_from_drive() -> list:
    folder_id = config.GDRIVE_FOLDER_ID
    if not folder_id:
        folder_id = gdrive.find_folder_id(config.GDRIVE_FOLDER_NAME)
        if not folder_id:
            raise RuntimeError(
                f"Drive folder {config.GDRIVE_FOLDER_NAME!r} not found"
            )

    files: list = []
    _collect_drive_files(folder_id, files)

    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        parts = list(pool.map(_fetch_drive_part, files))
    parts = [p for p in parts if p is not None]
    log.info(
        "Loaded %d/%d reference specs from Google Drive.", len(parts), len(files)
    )
    return parts


def _collect_drive_files(folder_id: str, files: list):
    """Recursively gather non-folder items (folders listed serially — cheap)."""
    for item in sorted(gdrive.list_children(folder_id), key=lambda i: i["name"]):
        if item["mimeType"] == gdrive.FOLDER_MIME:
            _collect_drive_files(item["id"], files)
        else:
            files.append(item)


def _fetch_drive_part(item: dict):
    """Fetch one Drive item and wrap it as a Gemini part (None on failure)."""
    name, mime = item["name"], item["mimeType"]
    try:
        if mime == gdrive.GDOC_MIME:
            text = gdrive.export_doc_text(item["id"])
            return types.Part.from_text(text=f"[{name}]\n{text}")
        if mime == "application/pdf":
            return types.Part.from_bytes(
                data=gdrive.download(item["id"]), mime_type="application/pdf"
            )
        if mime == DOCX_MIME:
            text = extract.extract_docx_text(gdrive.download(item["id"]))
            return types.Part.from_text(text=f"[{name}]\n{text}")
        if mime in ("text/plain", "text/markdown"):
            text = gdrive.download(item["id"]).decode("utf-8", "ignore")
            return types.Part.from_text(text=f"[{name}]\n{text}")
        log.info("Skipping unsupported Drive item: %s (%s)", name, mime)
    except Exception:  # noqa: BLE001
        log.exception("Failed to load Drive item %s", name)
    return None


# --- Local folder (fallback) -------------------------------------------------

def _load_from_local_dir() -> list:
    parts: list = []
    d = config.REFERENCES_DIR
    if not os.path.isdir(d):
        log.warning("References dir '%s' not found; no prior specs loaded.", d)
        return parts

    for root, dirnames, filenames in os.walk(d):
        dirnames[:] = sorted(n for n in dirnames if not n.startswith("."))
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            path = os.path.join(root, name)
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                if ext == "pdf":
                    parts.append(
                        types.Part.from_bytes(data=data, mime_type="application/pdf")
                    )
                elif ext == "docx":
                    text = extract.extract_docx_text(data)
                    parts.append(types.Part.from_text(text=f"[{name}]\n{text}"))
                elif ext in ("txt", "md"):
                    parts.append(
                        types.Part.from_text(
                            text=f"[{name}]\n{data.decode('utf-8', 'ignore')}"
                        )
                    )
                else:
                    log.warning("Skipping unsupported reference file: %s", name)
            except Exception:  # noqa: BLE001
                log.exception("Failed to load reference file %s", name)
    return parts
