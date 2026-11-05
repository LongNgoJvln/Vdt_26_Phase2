# VHT Network Automation — Usage Guide

## Prerequisites

- Python 3.11+, or Docker
- Git

---

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/pewdiepie-archdaemon/odysseus.git
cd odysseus
cp .env.example .env
docker compose up -d --build
```

Open **http://localhost:7000**. Find the auto-generated admin password:

```bash
docker compose logs odysseus | grep -i password
```

### Native Linux / macOS

```bash
git clone https://github.com/pewdiepie-archdaemon/odysseus.git
cd odysseus
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

First-run admin password is printed in the terminal.

### macOS (GPU-aware)


```bash
./start-macos.sh
```

Launches at **http://127.0.0.1:7860** (port 7860 avoids AirPlay conflict on port 7000).

### Windows

```powershell
.\launch-windows.ps1
```

Or manually:

```powershell
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

For Cookbook background model downloads, also install [Git for Windows](https://git-scm.com/download/win) (provides `bash.exe`).

---

## First-Time Setup

1. **Log in** with the auto-generated admin password (printed in terminal or container logs)
2. **Add a model endpoint** in **Settings → Models**: Ollama (`http://localhost:11434/v1`), vLLM, OpenAI, OpenRouter, etc.
3. **Configure web search** (optional): Settings → Search — provide a SearXNG instance or API key
4. **Explore**: Chat, Agent, Documents, and all other features are available from the sidebar

---

## Deployment Modes

Set `ODYSSEUS_DEPLOY_MODE` in `.env`:

| Mode | Enabled Features |
|------|-----------------|
| `enterprise` (default) | All features |
| `minimal` | Chat, Documents, Research, Settings only |

Individual features can be overridden with `ODYSSEUS_FEATURE_<NAME>=true/false`.

---

## Key Commands

| Action | Command |
|--------|---------|
| Run dev server | `python -m uvicorn app:app --host 127.0.0.1 --port 7000 --reload` |
| Run tests | `pytest` |
| Run single test | `pytest tests/test_file.py -v` |
| Run tests by name | `pytest -k "test_keyword"` |
| Install deps | `pip install -r requirements.txt` |
| Run database setup | `python setup.py` |
| Check Docker GPU | `scripts/check-docker-gpu.sh` |

---

## Environment Variables (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_BIND` | `127.0.0.1` | Bind address |
| `APP_PORT` | `7000` | Web UI port |
| `AUTH_ENABLED` | `true` | Enable/disable authentication |
| `SECURE_COOKIES` | `false` | Set `true` when behind HTTPS proxy |
| `LOCALHOST_BYPASS` | `false` | Dev-only auth bypass for loopback |
| `DATABASE_URL` | `sqlite:///./data/app.db` | Database connection |
| `OPENAI_API_KEY` | — | Optional OpenAI API key |
| `OFFLINE_MODE` | `false` | Disable all internet-dependent features |
| `ODYSSEUS_DEPLOY_MODE` | `enterprise` | `enterprise` or `minimal` |

---

## Data

All user data lives in `data/` (gitignored):

| Path | Contents |
|------|----------|
| `data/app.db` | Sessions, messages, documents, settings |
| `data/auth.json` | User accounts |
| `data/memory.json` | Persistent memory |
| `data/settings.json` | App settings |
| `data/uploads/` | File uploads |
| `data/personal_docs/` | Personal document library |
| `data/chroma/` | Vector embeddings (ChromaDB) |
| `data/generated_images/` | AI-generated images |

---

## Docker GPU Support

For NVIDIA GPUs inside Docker:

```bash
# Diagnostic (read-only)
scripts/check-docker-gpu.sh

# Full setup
scripts/check-docker-gpu.sh --install-nvidia-toolkit --enable-nvidia-overlay
```

For AMD GPUs:

```bash
scripts/check-docker-amd-gpu.sh
```

Then add `COMPOSE_FILE=docker-compose.yml:docker/gpu.amd.yml` and `RENDER_GID=<your-render-gid>` to `.env`.

---

## Security Notes

- Keep `AUTH_ENABLED=true` for any network-accessible deployment
- Do not expose port directly to the public internet — use a reverse proxy with HTTPS
- Non-admin users don't get shell/Python/file access by default
- API tokens are bearer credentials — treat them like passwords