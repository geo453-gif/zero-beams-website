# Frost Beams Website + Vouch Bot

This repository includes:
- a static Frost Beams website (`index.html`, `css/style.css`)
- a terminal-run Discord vouch bot (`bot.py`) with slash commands + SQLite storage

## Files
- `index.html` — static landing page/dashboard UI
- `css/style.css` — website styles
- `bot.py` — Discord bot (slash commands)
- `requirements.txt` — Python dependencies
- `.env.example` — environment variable template

## Linux Quickstart (Ubuntu/Debian)

### 0) Install Python tooling
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 1) Go to your project folder
> Do **not** use `/workspace/zero-beams-website` on your own PC unless that path actually exists.

```bash
cd ~/zero-beams-website
```

### 2) Create + activate virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Create your `.env`
```bash
cp .env.example .env
nano .env
```

Set:
- `DISCORD_TOKEN` = your bot token
- `GUILD_ID` = your server ID
- `ADMIN_ROLE_NAME` = role allowed to moderate vouches
- `VOUCH_DB_PATH` = SQLite DB file (default `vouches.db`)

### 5) Run the bot
```bash
python3 bot.py
```

### 6) (Optional) Run website locally
Open a second terminal in the same folder:
```bash
python3 -m http.server 4173
```
Open: `http://localhost:4173`

---

## Git Commands (Linux)

### Clone the repo
```bash
git clone <your-repo-url>.git
cd zero-beams-website
```

### Check current changes
```bash
git status
git diff
```

### Save your changes
```bash
git add .
git commit -m "your message"
```

### Push to GitHub
```bash
git push origin <your-branch>
```

### First-time Git setup (if needed)
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Update local branch from remote
```bash
git pull --rebase origin <your-branch>
```

---

## Slash Commands

### Member commands
- `/vouch <member> <reason>` — submit a vouch
- `/myvouches` — show your approved vouches
- `/vouchboard` — show top members by approved vouches
- `/helpvouch` — list available commands

### Admin/mod commands
- `/setvouchchannel <channel>` — set notification channel
- `/pendingvouches` — list pending vouches
- `/approvevouch <vouch_id> [note]` — approve a vouch
- `/rejectvouch <vouch_id> <note>` — reject a vouch

## Linux Troubleshooting
- `cd: No such file or directory`: run `pwd && ls` and `cd` into the folder that actually contains `README.md`/`bot.py`.
- `No module named discord`: activate venv (`source .venv/bin/activate`) then run `pip install -r requirements.txt`.
- Commands not appearing in Discord: ensure `GUILD_ID` is correct and bot has `applications.commands` + proper permissions.
- `fatal: not a git repository`: run `cd` into the project folder containing `.git` and run `git status` again.
- Token leaked: reset immediately in Discord Developer Portal.
