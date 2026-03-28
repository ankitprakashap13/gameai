"""Flask GSI HTTP receiver."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from flask import Flask, jsonify, request

from src.db.store import Database

log = logging.getLogger(__name__)


def create_gsi_app(
    db: Database,
    on_gsi_payload: Callable[[dict[str, Any]], None] | None = None,
) -> Flask:
    """
    Create Flask app for POST / (GSI) and GET /data (HTML table).
    If on_gsi_payload is set, it is called with the raw JSON dict on every tick.
    """
    app = Flask(__name__)

    @app.route("/", methods=["POST"])
    def gsi() -> Any:
        game_state = request.get_json(silent=True)
        if game_state is None:
            return jsonify({"status": "error", "message": "Expected JSON body"}), 400

        if on_gsi_payload is not None:
            try:
                on_gsi_payload(game_state)
            except Exception:
                log.exception("on_gsi_payload failed")
        return jsonify({"status": "ok"})

    @app.route("/data", methods=["GET"])
    def list_data() -> str:
        rows = db.fetch_latest_payloads(limit=100)
        html_rows: list[str] = []
        for row_id, created_at, payload in rows:
            pretty_payload = json.dumps(json.loads(payload), indent=2)
            html_rows.append(
                "<tr>"
                f"<td>{row_id}</td>"
                f"<td>{created_at}</td>"
                f"<td><pre>{pretty_payload}</pre></td>"
                "</tr>"
            )

        html = (
            "<html><head><title>Dota 2 GSI Data</title>"
            "<style>body{font-family:Arial,sans-serif;padding:20px;}"
            "table{border-collapse:collapse;width:100%;}"
            "th,td{border:1px solid #ddd;padding:8px;vertical-align:top;}"
            "th{background:#f6f6f6;}pre{margin:0;white-space:pre-wrap;}</style>"
            "</head><body>"
            "<h1>Dota 2 GSI Data (latest 100)</h1>"
            "<p>POST JSON to <code>/</code> and refresh this page to see new data.</p>"
            "<table><thead><tr><th>ID</th><th>Saved At (UTC)</th><th>Payload</th></tr></thead>"
            f"<tbody>{''.join(html_rows) if html_rows else '<tr><td colspan=3>No data yet.</td></tr>'}</tbody>"
            "</table></body></html>"
        )
        return html

    return app
