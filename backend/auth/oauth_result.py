"""Shared helper to finish an OAuth popup flow.

Returns a tiny HTML page that notifies the opener window (the SPA) via
``postMessage`` and then closes itself — so the app refreshes only its
connectors list instead of doing a full-page reload. If the page was opened
directly (no opener), it falls back to a normal redirect to ``/app``.
"""
import json

from flask import Response


def oauth_popup_response(
    frontend_url: str,
    status: str,            # "success" | "error"
    connector: str,         # "google_drive" | "dropbox" | ...
    connector_id: str = None,
    reason: str = None,
) -> Response:
    payload = {
        "type": "connector_oauth",
        "status": status,
        "connector": connector,
        "id": connector_id,
        "reason": reason,
    }

    if status == "success":
        fallback = f"{frontend_url}/app?connector_connected={connector}&id={connector_id}"
    else:
        fallback = f"{frontend_url}/app?connector_error={connector}&reason={reason or 'error'}"

    # json.dumps doubles as safe JS-literal + string escaping for embedding.
    page = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Authorization complete</title></head>
<body style="font-family:system-ui,sans-serif;padding:2rem;text-align:center;color:#374151">
<p>Authorization complete. You can close this window.</p>
<script>
(function() {{
  var payload = {json.dumps(payload)};
  var fallback = {json.dumps(fallback)};
  var targetOrigin = {json.dumps(frontend_url)};
  try {{
    if (window.opener && !window.opener.closed) {{
      window.opener.postMessage(payload, targetOrigin);
      window.close();
      return;
    }}
  }} catch (e) {{ /* fall through to redirect */ }}
  window.location.replace(fallback);
}})();
</script>
</body>
</html>"""

    return Response(page, mimetype="text/html")
