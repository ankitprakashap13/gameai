# Dota 2 AI Coach

Real-time coaching companion for Dota 2. Reads your game state, watches your screen, and gives you actionable tips via a transparent overlay -- all while you play.

**How it works:** Game State Integration (GSI) feeds live match data, OpenCV reads your minimap/items/cooldowns from the screen, and an LLM turns it all into short coaching tips displayed on top of your game.

---

## Quick Start (Windows)

### 1. Install Python

Download Python 3.10+ from [python.org/downloads](https://www.python.org/downloads/).

> **Important:** During install, check the box that says **"Add python.exe to PATH"**.
>
> After install, open a **new** Command Prompt or PowerShell and verify:
> ```
> python --version
> ```

### 2. Download the app

```
git clone <repo-url> gameai
cd gameai
```

Or download the ZIP from the repo page, extract it, and open a terminal in the folder.

### 3. Install dependencies

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

This takes 1-3 minutes and downloads about 250 MB (OpenCV, PyQt6, etc).

### 4. Set up your LLM (pick one)

Copy the example env file:

```
copy .env.example .env
```

Then open `.env` in Notepad and configure **one** of these:

**Option A -- OpenAI (easiest, ~$0.01 per game)**
```
COACH_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...paste-your-key...
```
Get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

**Option B -- Anthropic**
```
COACH_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...paste-your-key...
```

**Option C -- Ollama (free, runs on your PC, no key needed)**
1. Install from [ollama.com](https://ollama.com)
2. Open a terminal and run: `ollama pull llama3.2`
3. In `.env` set:
```
COACH_LLM_PROVIDER=ollama
```

### 5. Install the Dota 2 GSI config

This tells Dota to send live game data to the coach app.

```
python scripts/setup_gsi.py
```

The script auto-detects your Dota 2 install and copies the config file. If auto-detection fails, it will ask you to paste your Dota path.

> **Manual alternative:** copy `assets\config\gamestate_integration_coach.cfg` into:
> ```
> C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\dota\cfg\gamestate_integration\
> ```
> Create the `gamestate_integration` folder if it doesn't exist.

### 6. Download vision templates

```
python scripts/download_assets.py
```

Downloads hero and item icons from Steam's CDN for screen matching (~2 min).

### 7. Set Dota 2 to Borderless Windowed

In Dota 2: **Settings > Video > Display Mode > Borderless Window**

This is required -- exclusive fullscreen blocks both the overlay and screen capture.

### 8. Run

```
python main.py
```

The app runs startup checks and tells you if anything is missing. Once running, start a Dota 2 match and coaching tips will appear in the top-right corner of your screen.

---

## Quick Start (Mac)

### 1. Install Python

Mac comes with an older Python. Install 3.10+ via Homebrew (recommended) or from python.org:

```bash
# Option A: Homebrew (if you have it)
brew install python@3.13

# Option B: download from python.org/downloads
```

Verify:
```bash
python3 --version
```

### 2. Download the app

```bash
git clone <repo-url> gameai
cd gameai
```

### 3. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Set up your LLM (pick one)

```bash
cp .env.example .env
open -e .env    # opens in TextEdit
```

Edit `.env` and configure one provider (see the Windows section above for details on each option). The simplest free option:

```
COACH_LLM_PROVIDER=ollama
```

Then install Ollama: download from [ollama.com](https://ollama.com), and run:
```bash
ollama pull llama3.2
```

### 5. Install the Dota 2 GSI config

```bash
python scripts/setup_gsi.py
```

The script checks the standard Mac Steam path (`~/Library/Application Support/Steam/...`). If auto-detect fails, paste your Dota cfg path when prompted.

> **Manual alternative:** copy the GSI config into:
> ```
> ~/Library/Application Support/Steam/steamapps/common/dota 2 beta/game/dota/cfg/gamestate_integration/
> ```

### 6. Download vision templates

```bash
python scripts/download_assets.py
```

### 7. Set Dota 2 to Borderless Windowed

In Dota 2: **Settings > Video > Display Mode > Borderless Window**

### 8. Run

```bash
python main.py
```

> **Mac permissions note:** The first launch may trigger macOS permission prompts:
> - **Screen Recording** -- required for `mss` screen capture. Go to **System Settings > Privacy & Security > Screen Recording** and enable your Terminal app.
> - Without this, the vision pipeline will capture blank frames. GSI and the LLM coach still work fine without it.

---

## Quick Start (Linux)

Same as the Mac steps above. The GSI setup script checks `~/.steam/steam` and `~/.local/share/Steam`. Use `source .venv/bin/activate` and `cp .env.example .env`. No special permissions needed -- X11/Wayland screen capture works out of the box with `mss`.

---

## Standalone Executable (no Python needed)

For distributing to users who don't want to install Python:

```
python scripts/build_exe.py
```

This uses PyInstaller to create `dist/DotaCoach/DotaCoach.exe`. Zip and share the folder. Users still need to:
1. Create a `.env` file with their LLM key (or use Ollama)
2. Run `scripts/setup_gsi.py` (bundled inside)
3. Set Dota to borderless windowed

---

## Configuration

The app reads settings from `config.yaml` (defaults) with optional overrides in `config.local.yaml` or `.env`.

| Setting | Default | What it does |
|---------|---------|--------------|
| `capture.fps` | `2.0` | Screen captures per second (higher = more CPU) |
| `llm.provider` | `openai` | LLM backend: `openai`, `anthropic`, or `ollama` |
| `llm.throttle_seconds` | `10.0` | Minimum seconds between coaching tips |
| `overlay.position` | `top_right` | Tip location: `top_right` or `right_center` |
| `overlay.tip_duration_seconds` | `8.0` | How long each tip stays on screen |

---

## Architecture

```
GSI (JSON/HTTP) ──> Flask server ──> State Aggregator ──> LLM Coach ──> Overlay
Screen capture  ──> Vision Pipeline ──────┘                              (PyQt6)
                    (OpenCV detectors)
```

- `src/gsi/` -- Flask GSI receiver, typed parser
- `src/vision/` -- `mss` capture (~2 FPS), template matching detectors (minimap, items, health/mana, cooldowns)
- `src/state/` -- Aggregator merges GSI + vision; match lifecycle auto-detects game start/end
- `src/llm/` -- Pluggable providers (OpenAI, Anthropic, Ollama), throttled prompts, tip deduplication
- `src/overlay/` -- Always-on-top coaching sidebar with chat, message history, and in-app settings
- `src/db/` -- SQLite (WAL mode) with tables for matches, events, vision snapshots, and coaching tips

---

## Tests

```
pip install pytest
python -m pytest tests/ -v
```

---

## Performance

The app is designed to run alongside Dota 2 with minimal impact:

- Screen capture: ~2% CPU at 2 FPS
- Vision processing: ~3% CPU (template matching, no GPU)
- LLM calls: network-bound, one call every ~10 seconds
- Overlay: negligible (repaints only on new tips)
- **Total: ~5% CPU, ~200 MB RAM**

---

## Troubleshooting

**"No OPENAI_API_KEY found"** -- Create a `.env` file (copy from `.env.example`) and add your key. Or switch to Ollama for free local LLM.

**"Could not find Dota 2 install"** -- Run `python scripts/setup_gsi.py` and paste your Dota cfg path when prompted.

**"Vision templates missing"** -- Run `python scripts/download_assets.py` to fetch hero/item icons.

**Tips not appearing** -- Make sure Dota is in Borderless Windowed mode. Check that `python main.py` is running and Dota's GSI config is installed.

**Overlay covers game UI** -- Drag the title bar to reposition the window, or use the gear icon to adjust width.

**Mac: screen capture is blank** -- Go to **System Settings > Privacy & Security > Screen Recording** and enable your Terminal (or Python). Restart the app after granting permission.

**Mac: `python` command not found** -- Use `python3` instead, or run `brew install python@3.13`.
