# Dota 2 GSI Saver (Flask + SQLite)

This small Flask app receives Dota 2 Game State Integration (GSI) JSON, saves each payload to a local SQLite database, and provides a web page to view saved entries.

## What it does

- `POST /` accepts JSON payloads (your GSI data).
- Saves each payload to `dota_gsi.db`.
- `GET /data` shows the latest 100 saved payloads in a simple HTML table.

## Requirements

- Python 3.8+
- `pip`

## Setup

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask
```

## Run the app

```bash
python3 dotaapp.py
```

The app starts on port `3000` by default.

## Endpoints

### 1) Save GSI payload

- **Method:** `POST`
- **URL:** `http://localhost:3000/`
- **Content-Type:** `application/json`

Example:

```bash
curl -X POST http://localhost:3000/ \
  -H "Content-Type: application/json" \
  -d '{"hero":{"name":"npc_dota_hero_axe"},"map":{"game_time":123}}'
```

Success response:

```json
{
  "status": "ok",
  "saved_id": 1
}
```

### 2) View saved payloads

- **Method:** `GET`
- **URL:** `http://localhost:3000/data`

Open this URL in your browser to see saved records.

## Database details

- Database file: `dota_gsi.db`
- Table: `gsi_data`
  - `id` (auto increment)
  - `created_at` (UTC ISO timestamp)
  - `payload` (JSON string)

## Dota 2 GSI config tip

In Dota 2, GSI is configured via a `.cfg` file in the game integration folder. Point your URI to:

`http://127.0.0.1:3000/`

Once Dota sends updates, refresh `http://localhost:3000/data` to see newly saved payloads.
