# Python 3.x - dOTA APP
# Install dependencies: pip install flask

import json
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "dota_gsi.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gsi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_gsi_payload(payload):
    conn = sqlite3.connect(DB_PATH)
    created_at = datetime.now(timezone.utc).isoformat()
    payload_json = json.dumps(payload, ensure_ascii=False)
    cur = conn.execute(
        "INSERT INTO gsi_data (created_at, payload) VALUES (?, ?)",
        (created_at, payload_json),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


@app.route("/", methods=["POST"])
def gsi():
    game_state = request.get_json(silent=True)
    if game_state is None:
        return jsonify({"status": "error", "message": "Expected JSON body"}), 400

    row_id = save_gsi_payload(game_state)
    return jsonify({"status": "ok", "saved_id": row_id})


@app.route("/data", methods=["GET"])
def list_data():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, created_at, payload FROM gsi_data ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()

    html_rows = []
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


if __name__ == "__main__":
    init_db()
    app.run(port=3000)
