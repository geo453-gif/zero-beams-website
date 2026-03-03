# Frost Beams Website + Vouch Bot

This repository now includes:
- a static Frost Beams website (`index.html`, `css/style.css`)
- a real terminal-run Discord vouch bot (`bot.py`) with slash commands and SQLite storage

## Files
- `index.html` — static landing page and dashboard mock UI
- `css/style.css` — website styles
- `bot.py` — Discord bot (slash commands)
- `requirements.txt` — Python dependencies for the bot
- `.env.example` — environment variables template

## Terminal Setup (Step by Step)

### 1) Open this project folder
```bash
cd /path/to/your/zero-beams-website
```

### 2) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Create your `.env` file
```bash
cp .env.example .env
```

Then edit `.env` and set:
- `DISCORD_TOKEN` = your bot token
- `GUILD_ID` = your server (guild) ID
- `ADMIN_ROLE_NAME` = role allowed to approve/reject
- `VOUCH_DB_PATH` = database filename

### 5) Run the bot in terminal
```bash
python3 bot.py
```

### 6) Run the website locally (optional)
```bash
python3 -m http.server 4173
```
Open: `http://localhost:4173`

## Slash Commands (a lot of commands)

### Member commands
- `/vouch <member> <reason>` — submit a vouch
- `/myvouches` — show your approved vouches
- `/vouchboard` — show top members by approved vouches
- `/helpvouch` — list available commands

### Admin/mod commands
- `/setvouchchannel <channel>` — where new vouch notifications are posted
- `/pendingvouches` — list pending vouches
- `/approvevouch <vouch_id> [note]` — approve a vouch
- `/rejectvouch <vouch_id> <note>` — reject a vouch

## Notes
- Keep your token private. If leaked, reset it in the Discord Developer Portal.
- Vouches are stored in SQLite (`vouches.db` by default).
- For fast command updates while testing, set your `GUILD_ID` in `.env`.
