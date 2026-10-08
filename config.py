"""Central config. Reads from environment (.env in local dev)."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Slack ---
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

# --- Vertex AI / Gemini ---
# Auth uses Application Default Credentials (gcloud auth application-default login).
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "i-digmops")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Latency knobs.
# Thinking budget: 0 disables Gemini 2.5's internal "thinking" (fastest; fine
# for grounded lookups). Set e.g. 1024 for a little reasoning, -1 for dynamic.
GEMINI_THINKING_BUDGET = int(os.environ.get("GEMINI_THINKING_BUDGET", "0"))
# Hard cap on reply length; the prompts ask for a compact format anyway.
GEMINI_MAX_OUTPUT_TOKENS = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "4096"))
# Vertex context caching: upload the grounding material (prior specs,
# OneTrust page) once and reference it by ID, so each request only sends the
# spec under review instead of re-sending every prior spec. Falls back to
# inline grounding automatically if caching fails.
GEMINI_USE_CONTEXT_CACHE = os.environ.get("GEMINI_USE_CONTEXT_CACHE", "1") not in ("0", "false", "False")
GEMINI_CACHE_TTL_SECONDS = int(os.environ.get("GEMINI_CACHE_TTL_SECONDS", str(6 * 3600)))

# --- Reference material ---
# Prior specs live in a Google Drive folder, read directly via the Drive API
# (no Drive-for-desktop sync needed). Set GDRIVE_FOLDER_ID (from the folder's
# URL: .../folders/<GDRIVE_FOLDER_ID>) or leave it blank to look the folder up
# by name. Requires ADC with the drive.readonly scope — see gdrive.py.
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")
GDRIVE_FOLDER_NAME = os.environ.get("GDRIVE_FOLDER_NAME", "P+ MON Active Specs")

# Path to a service-account JSON key used ONLY for Drive (Vertex AI keeps
# using your own ADC). The specs folder must be shared with the service
# account's client_email. Leave blank to fall back to ADC for Drive too.
GDRIVE_SERVICE_ACCOUNT_KEY = os.environ.get("GDRIVE_SERVICE_ACCOUNT_KEY", "")

# Fallback: a local folder of prior specs, used only if Drive isn't
# configured/reachable. Supported: .pdf, .docx, .txt, .md
REFERENCES_DIR = os.environ.get("REFERENCES_DIR", "references")

# --- Confluence (privacy rules page) ---
# The bot needs its OWN Atlassian API token (not the Claude connector).
# Generate at: https://id.atlassian.com/manage-profile/security/api-tokens
# BASE_URL should include /wiki, e.g. https://yourcompany.atlassian.net/wiki
# PAGE_ID is the numeric id in the page URL: .../pages/<PAGE_ID>/Title
CONFLUENCE_BASE_URL = os.environ.get("CONFLUENCE_BASE_URL", "")
CONFLUENCE_EMAIL = os.environ.get("CONFLUENCE_EMAIL", "")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "")
CONFLUENCE_PAGE_ID = os.environ.get("CONFLUENCE_PAGE_ID", "")

# --- Storage ---
DB_PATH = os.environ.get("DB_PATH", "specs.db")