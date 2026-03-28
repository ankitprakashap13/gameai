# Python 3.x — backward-compatible entry: GSI logger only (same as before)
# Full coach app: python main.py

from pathlib import Path

from src.config_loader import load_config
from src.db.store import Database
from src.gsi.server import create_gsi_app

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    cfg = load_config(root)
    db_path = root / cfg.get("paths", {}).get("db", "dota_gsi.db")
    host = cfg.get("gsi", {}).get("host", "127.0.0.1")
    port = int(cfg.get("gsi", {}).get("port", 3000))
    db = Database(db_path)
    app = create_gsi_app(db, on_gsi_payload=lambda p: db.save_legacy_payload(p))
    app.run(host=host, port=port)
