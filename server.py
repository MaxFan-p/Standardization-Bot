# server.py — web endpoint wrapper around the review engine (compliance/review.py)
from flask import Flask, request, jsonify

import references_loader
from compliance import review

app = Flask(__name__)


@app.route("/review", methods=["POST"])
def review_endpoint():
    """Check a spec's variables/values against prior specs."""
    data = request.get_json(silent=True) or {}
    spec_text = (data.get("text") or "").strip()
    if not spec_text:
        return jsonify({"error": "Send JSON like {\"text\": \"<spec text>\"}"}), 400
    findings = review.spec_check(spec_text)
    return jsonify({"findings": findings})


@app.route("/vendor-check", methods=["POST"])
def vendor_check_endpoint():
    """Look up vendors' OneTrust category and profile rules."""
    data = request.get_json(silent=True) or {}
    vendors_text = (data.get("text") or "").strip()
    if not vendors_text:
        return jsonify({"error": "Send JSON like {\"text\": \"Conviva, Branch\"}"}), 400
    findings = review.vendor_check(vendors_text)
    return jsonify({"findings": findings})


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    # Load all reference specs up front so no HTTP request ever waits on (or
    # double-triggers) the multi-minute Drive fetch.
    print("Loading reference specs (once, at startup)…")
    n = len(references_loader.load_reference_specs())
    print(f"{n} reference specs loaded. Serving.")
    # host="0.0.0.0" so a tunnel (e.g. ngrok) can reach it; port 8080 is
    # arbitrary. The debug reloader is off: it doubles memory and drops
    # in-flight requests on restart (seen as ngrok 502/503 errors).
    app.run(host="0.0.0.0", port=8080)
