"""Read reference specs straight from Google Drive (no Drive-for-desktop sync).

Auth, in order of preference:
  1. A service-account JSON key (GDRIVE_SERVICE_ACCOUNT_KEY in .env). The
     specs folder must be shared with the service account's client_email.
  2. Application Default Credentials — only works if your ADC was created
     with the drive.readonly scope, which Workspace policy may block.
"""
import logging
import threading

import google.auth
import google.auth.transport.requests
import requests
from google.oauth2 import service_account

import config

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_API = "https://www.googleapis.com/drive/v3"
# Shared-drive items are invisible to the API without these.
_SHARED_DRIVE_PARAMS = {
    "supportsAllDrives": "true",
    "includeItemsFromAllDrives": "true",
}

FOLDER_MIME = "application/vnd.google-apps.folder"
GDOC_MIME = "application/vnd.google-apps.document"

_credentials = None
_credentials_lock = threading.Lock()


def _auth_header():
    global _credentials
    with _credentials_lock:
        if _credentials is None:
            if config.GDRIVE_SERVICE_ACCOUNT_KEY:
                _credentials = service_account.Credentials.from_service_account_file(
                    config.GDRIVE_SERVICE_ACCOUNT_KEY, scopes=_SCOPES
                )
            else:
                _credentials, _ = google.auth.default(scopes=_SCOPES)
        if not _credentials.valid:
            _credentials.refresh(google.auth.transport.requests.Request())
        return {"Authorization": f"Bearer {_credentials.token}"}


def _get(path: str, **params):
    resp = requests.get(
        f"{_API}/{path}", params=params, headers=_auth_header(), timeout=60
    )
    resp.raise_for_status()
    return resp


def find_folder_id(name: str) -> str | None:
    """Find a folder by exact name (searches shared drives too)."""
    q = f"name = '{name}' and mimeType = '{FOLDER_MIME}' and trashed = false"
    resp = _get(
        "files",
        q=q,
        corpora="allDrives",
        fields="files(id, name, driveId)",
        **_SHARED_DRIVE_PARAMS,
    )
    files = resp.json().get("files", [])
    if not files:
        return None
    if len(files) > 1:
        log.warning("Multiple folders named %r; using the first.", name)
    return files[0]["id"]


def list_children(folder_id: str) -> list[dict]:
    """List a folder's files/subfolders: [{id, name, mimeType}, ...]."""
    items, page_token = [], None
    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id, name, mimeType)",
            "pageSize": 1000,
            **_SHARED_DRIVE_PARAMS,
        }
        if page_token:
            params["pageToken"] = page_token
        data = _get("files", **params).json()
        items.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            return items


def export_doc_text(doc_id: str) -> str:
    """Export a native Google Doc's content as plain text."""
    return _get(f"files/{doc_id}/export", mimeType="text/plain").text


def download(file_id: str) -> bytes:
    """Download a regular (non-native) file's bytes."""
    return _get(f"files/{file_id}", alt="media", supportsAllDrives="true").content
