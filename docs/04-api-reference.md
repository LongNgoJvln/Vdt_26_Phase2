# VHT Network Automation — API Reference

Complete endpoint catalog organized by feature area. All endpoints under `/api/` unless noted.

---

## Authentication (`/api/auth/*`)

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/setup` | Create initial admin account (first run only) | None |
| POST | `/signup` | Create new user account (if registration enabled) | None |
| POST | `/login` | Authenticate, set session cookie | None |
| POST | `/logout` | Revoke current session | Cookie |
| GET | `/status` | Current auth status + privileges | Cookie |
| POST | `/change-password` | Change current user's password | Cookie |
| POST | `/2fa/setup` | Generate TOTP secret + QR code | Cookie |
| POST | `/2fa/confirm` | Confirm TOTP setup (returns backup codes) | Cookie |
| POST | `/2fa/disable` | Disable 2FA | Cookie |
| GET | `/2fa/status` | Check 2FA status | Cookie |
| GET | `/users` | List all users | Admin |
| POST | `/users` | Create user (admin only) | Admin |
| PUT | `/users/{username}/privileges` | Update user privileges | Admin |
| PUT | `/users/{username}/rename` | Rename user + update all owner references | Admin |
| PUT | `/open-signup` | Enable/disable open registration | Admin |
| POST | `/signup-toggle` | Toggle registration (deprecated) | Admin |
| DELETE | `/users` | Delete user (admin only) | Admin |
| GET | `/features` | Get feature flag state | Public |
| POST | `/features` | Update feature toggles | Admin |
| GET | `/settings` | Get app settings (scrubbed for non-admin) | Cookie |
| POST | `/settings` | Update app settings | Admin |
| GET | `/integrations` | List integrations (keys masked) | Admin |
| GET | `/integrations/presets` | List available integration presets | Public |
| POST | `/integrations` | Create integration | Admin |
| PUT | `/integrations/{id}` | Update integration | Admin |
| DELETE | `/integrations/{id}` | Delete integration | Admin |
| POST | `/integrations/{id}/test` | Test integration connectivity | Admin |

### Login Request Body

```json
{
  "username": "admin",
  "password": "secret",
  "remember": true
}
```

Response sets `vhtna_session` cookie. If 2FA is enabled, returns `{"2fa_required": true}` and the client must follow up with the TOTP code.

### Setup Request (First Run)

```json
{
  "username": "admin",
  "password": "secure_password"
}
```

Only accepted when no users exist in the database. Creates an admin account.

---

## Chat

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/chat` | Non-streaming chat (JSON body) | Cookie |
| POST | `/chat_stream` | Streaming chat via SSE | Cookie |

### chat_stream Request

The streaming endpoint accepts both form-data and JSON:

**Form-data fields:**
- `message`: string (required) — user message text
- `session`: string (required) — session ID to continue
- `attachments`: list of attachment IDs (optional)
- `use_web`: boolean — enable web search
- `use_research`: boolean — enable deep research
- `time_filter`: string — date range for search
- `preset_id`: string — chat preset to apply
- `mode`: `chat` or `agent` — chat mode vs agentic tool use
- `allow_bash`: boolean — allow bash tool
- `allow_web_search`: boolean — allow web search tool
- `use_rag`: boolean — enable RAG document retrieval
- `incognito`: boolean — privacy mode (no memory/skills)
- `compare_mode`: boolean — model comparison mode
- `active_doc_id`: string — document being edited

### SSE Event Types

The chat stream emits these server-sent events. Each event line has the format `data: <json>\n\n`:

| Event | Data Shape | Purpose |
|---|---|---|
| `delta` | `{"stream":"stdout","data":"..."}` | Token chunk |
| `tool_start` | `{"tool":"name","args":{...}}` | Tool call beginning |
| `tool_output` | `{"tool":"name","output":"..."}` | Tool result |
| `agent_step` | `{"step":n,"thought":"..."}` | Agent reasoning step |
| `doc_update` | `{"doc_id":"...","content":"..."}` | Document content update |
| `web_sources` | `[{"title":"...","url":"..."}]` | Web search source list |
| `research_progress` | `{"stage":"...","progress":0.0-1.0}` | Research stage update |
| `research_done` | `{"title":"...","summary":"..."}` | Research completed |
| `metrics` | `{"tokens":n,"time":n,"model":"..."}` | Token usage, latency |
| `model_info` | `{"model":"...","endpoint":"..."}` | Model identification |
| `compacted` | `{}` | Context was compacted |
| `[DONE]` | — | Stream complete |

---

## Sessions (`/api/session*`)

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/sessions` | List active sessions (owner-scoped) | Cookie |
| POST | `/session` | Create new session | Cookie |
| PATCH | `/session/{sid}` | Rename, change folder, swap model/endpoint | Cookie |
| POST | `/session/{sid}/delete` | Delete session (POST for sendBeacon) | Cookie |
| DELETE | `/session/{sid}` | Delete session | Cookie |
| POST | `/sessions/bulk-delete` | Delete multiple sessions | Cookie |
| DELETE | `/sessions/all` | Delete all sessions | Admin |
| POST | `/session/{sid}/archive` | Archive session | Cookie |
| POST | `/session/{sid}/unarchive` | Restore archived session | Cookie |
| GET | `/sessions/archived` | List archived sessions | Cookie |
| POST | `/session/{sid}/inject_messages` | Bulk-inject messages into history | Cookie |
| POST | `/session/{sid}/important` | Star/unstar session (prevents auto-cleanup) | Cookie |
| POST | `/session/{sid}/compact` | AI-summarize older messages | Cookie |
| POST | `/sessions/auto-sort` | AI-categorize sessions into folders | Cookie |
| POST | `/sessions/save` | Force-save sessions to disk | Cookie |
| POST | `/session/openai` | Create session with OpenAI default | Cookie |

### Session Object

```json
{
  "id": "abc123",
  "owner": "admin",
  "name": "Network config review",
  "model": "gpt-4",
  "endpoint_url": "https://api.openai.com/v1",
  "mode": "chat",
  "message_count": 12,
  "is_important": false,
  "archived": false,
  "folder": "Work",
  "created_at": "2026-07-22T10:00:00",
  "updated_at": "2026-07-22T14:30:00"
}
```

### Session Filters

`GET /api/sessions` supports query parameters:
- `folder` — filter by folder name
- `archived` — boolean, filter archived status
- `sort` — `updated`, `created`, `name`

---

## Session Messages

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/history/{sid}` | Get session message history | Cookie |
| GET | `/session/{sid}/export` | Export as markdown (default), txt, json, or html | Cookie |

Export formats via `fmt` query param: `md` (default), `txt`, `json`, `html`.

### Message Object

```json
{
  "id": 1,
  "session_id": "abc123",
  "role": "user",
  "content": "What's the config for VLAN 100?",
  "metadata": {
    "model": "gpt-4",
    "endpoint": "openai",
    "tokens": 42
  },
  "timestamp": "2026-07-22T14:30:00"
}
```

---

## Documents

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/document` | Create new document | Cookie |
| PUT | `/document/{doc_id}` | Update document content (new version) | Cookie |
| PATCH | `/document/{doc_id}` | Update metadata only (title, language) | Cookie |
| DELETE | `/document/{doc_id}` | Soft-delete document | Cookie |
| GET | `/document/{doc_id}` | Get document by ID | Cookie |
| GET | `/document/{doc_id}/versions` | List version history | Cookie |
| GET | `/document/{doc_id}/version/{num}` | Get specific version | Cookie |
| POST | `/document/{doc_id}/restore/{num}` | Restore old version | Cookie |
| POST | `/document/{doc_id}/archive` | Soft-archive/restore | Cookie |

### Document Library

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/documents/library` | List all documents (searchable, pageable) | Cookie |
| POST | `/documents/import-pdf` | Upload PDF, create document | Cookie |
| POST | `/documents/export-zip` | Bulk download as ZIP | Cookie |
| POST | `/documents/tidy` | Clean up empty/junk documents | Cookie |
| POST | `/documents/ai-tidy` | AI-powered junk detection | Cookie |
| GET | `/documents/{session_id}` | List documents for a session | Cookie |

### PDF Features

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/document/{id}/extract-pdf-text` | Re-extract text from PDF (OCR) | Cookie |
| POST | `/document/{id}/export-pdf/preview` | Preview form field values | Cookie |
| POST | `/document/{id}/export-pdf/download` | Download filled PDF | Cookie |
| GET | `/document/{id}/render-pages` | Per-page metadata (dimensions + fields) | Cookie |
| GET | `/document/{id}/page/{n}.png` | Render single page as PNG | Cookie |
| POST | `/document/{id}/ai-fill-annotations` | AI locate fillable areas on flat PDF | Cookie |

### Document Version History

Documents maintain a full version history. Each version stores:
- Content snapshot
- Summary of changes
- Source (AI-generated, manual edit, import)
- Timestamp

### Document Object

```json
{
  "id": "doc_abc",
  "session_id": "abc123",
  "owner": "admin",
  "title": "VLAN Configuration Guide",
  "language": "markdown",
  "current_content": "# VLAN Configuration\n...",
  "version_count": 3,
  "is_active": true,
  "archived": false,
  "created_at": "2026-07-20T08:00:00",
  "updated_at": "2026-07-22T12:00:00"
}
```

---

## Memory

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/memory` | Get all memory entries | Cookie |
| POST | `/memory/add` | Add new memory entry | Cookie |
| POST | `/memory/search` | Search memories with filters | Cookie |
| GET | `/memory/timeline` | Memories in chronological order | Cookie |
| GET | `/memory/by-session/{sid}` | Memories for a session | Cookie |
| POST | `/memory/extract` | AI-extract memories from a session | Cookie |
| POST | `/memory/audit` | AI deduplicate/consolidate memories | Cookie |
| POST | `/memory/import` | Import memories from uploaded file | Cookie |
| POST | `/memory/debug` | Debug relevance for a query | Cookie |
| POST | `/memory/{id}/pin` | Pin/unpin memory (always included in context) | Cookie |
| GET | `/memory/{id}` | Get specific memory | Cookie |
| PUT | `/memory/{id}` | Update memory text/category | Cookie |
| DELETE | `/memory/{id}` | Delete memory | Cookie |

### Memory Object

```json
{
  "id": "mem_abc",
  "owner": "admin",
  "content": "User prefers Cisco IOS for switch configs",
  "category": "preference",
  "importance": 0.8,
  "pinned": true,
  "created_at": "2026-07-21T09:00:00",
  "updated_at": "2026-07-22T10:00:00"
}
```

Categories include: `preference`, `fact`, `task`, `context`, `personal`, `work`.

---

## Deep Research

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/research/start` | Launch research job from panel | Cookie |
| GET | `/research/active` | List active (running) tasks | Cookie |
| GET | `/research/status/{sid}` | Get research status | Cookie |
| GET | `/research/stream/{sid}` | SSE progress stream | Cookie |
| POST | `/research/cancel/{sid}` | Cancel running research | Cookie |
| POST | `/research/result/{sid}` | Get result (clears cache) | Cookie |
| POST | `/research/result-peek/{sid}` | Get result without clearing | Cookie |
| GET | `/research/report/{sid}` | Visual HTML report | Cookie |
| GET | `/research/detail/{sid}` | Full JSON (for library preview) | Cookie |
| GET | `/research/library` | List all completed research | Cookie |
| POST | `/research/{sid}/archive` | Archive/unarchive research | Cookie |
| POST | `/research/{sid}/hide-image` | Hide image in visual report | Cookie |
| POST | `/research/{sid}/unhide-images` | Clear hidden images | Cookie |
| POST | `/research/spinoff/{sid}` | Create chat seeded with research | Cookie |
| DELETE | `/research/{sid}` | Delete research result | Cookie |

### Research Start Request

```json
{
  "session_id": "abc123",
  "query": "Best practices for OSPF configuration on Cisco Nexus switches",
  "max_topics": 5,
  "depth": "standard"
}
```

### Research Status

```json
{
  "status": "running",
  "progress": 0.45,
  "stage": "web_research",
  "current_topic": "OSPF area design",
  "topics_completed": 2,
  "topics_total": 5
}
```

---

## Models & Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/models` | List available models (owner-scoped) | Cookie |
| GET | `/providers` | List all providers | Admin |
| GET | `/discover` | Scan network for model servers | Admin |
| GET | `/ping` | Ping all endpoints (status + latency) | Admin |
| GET | `/probe` | Probe individual models (SSE stream) | Admin |
| POST | `/probe-selected` | Probe specific models (compare pre-check) | Admin |
| GET | `/model-endpoints/probe-local` | Reachability check for local endpoints | Admin |

### Model Endpoint CRUD

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/model-endpoints` | List all endpoints | Admin |
| POST | `/model-endpoints` | Create endpoint | Admin |
| PUT | `/model-endpoints/{id}` | Update endpoint | Admin |
| DELETE | `/model-endpoints/{id}` | Delete endpoint | Admin |

### Endpoint Object

```json
{
  "id": "ep_abc",
  "name": "OpenAI GPT-4",
  "base_url": "https://api.openai.com/v1",
  "model_type": "openai",
  "cached_models": "[\"gpt-4\",\"gpt-4-turbo\",\"gpt-3.5-turbo\"]",
  "hidden_models": "[\"gpt-3.5-turbo\"]",
  "is_enabled": true,
  "created_at": "2026-07-01T00:00:00"
}
```

API keys are encrypted at rest using Fernet encryption and are never returned in API responses.

---

## MCP Servers

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/mcp/servers` | List MCP servers (with status) | Admin |
| GET | `/mcp/servers/{id}` | Get server details | Admin |
| POST | `/mcp/servers` | Add server + connect | Admin |
| PATCH | `/mcp/servers/{id}` | Update server params | Admin |
| DELETE | `/mcp/servers/{id}` | Delete server + disconnect | Admin |
| POST | `/mcp/servers/{id}/reconnect` | Reconnect server | Admin |
| GET | `/mcp/tools` | List all MCP tools | Admin |
| GET | `/mcp/servers/{id}/tools` | List tools for a server | Admin |
| PATCH | `/mcp/servers/{id}/tools` | Bulk update disabled tools | Admin |
| POST | `/mcp/servers/{id}/config` | Update config via JSON body | Admin |
| DELETE | `/mcp/servers/{id}/config/env` | Clear server env vars | Admin |

### MCP Server Types

| Type | Command | Description |
|---|---|---|
| `stdio` | `python server.py` | Process launched as subprocess, communicates via stdio |
| `sse` | — | Server-sent events over HTTP |
| `http` | — | HTTP-based MCP server |

### MCP Server Object

```json
{
  "id": "mcp_abc",
  "name": "Playwright Browser",
  "type": "npm",
  "command": "npx",
  "args": ["-y", "@playwright/mcp@latest"],
  "disabled_tools": ["browser_navigate"],
  "status": "connected",
  "connected_at": "2026-07-22T14:00:00"
}
```

### MCP OAuth

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/mcp/oauth/authorize/{id}` | Show OAuth page | Admin |
| GET | `/mcp/oauth/callback` | Handle Google OAuth callback | Admin |
| POST | `/mcp/oauth/exchange/{id}` | Manual code exchange | Admin |

---

## Tasks & Scheduling

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/tasks` | List scheduled tasks | Admin |
| POST | `/tasks` | Create scheduled task | Admin |
| PUT | `/tasks/{id}` | Update task | Admin |
| DELETE | `/tasks/{id}` | Delete task | Admin |
| POST | `/tasks/{id}/run` | Run task now | Admin |
| GET | `/tasks/runs` | List task run history | Admin |

### Task Object

```json
{
  "id": "task_abc",
  "name": "Daily network health check",
  "cron": "0 8 * * *",
  "action": "bash",
  "params": "./scripts/health-check.sh",
  "enabled": true,
  "last_run": "2026-07-22T08:00:00",
  "next_run": "2026-07-23T08:00:00"
}
```

Tasks support cron expressions via `croniter`. Actions include: `bash`, `python`, `webhook`, `chat`, `research`.

---

## Webhooks

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/webhooks` | List webhooks | Admin |
| POST | `/webhooks` | Create webhook | Admin |
| PUT | `/webhooks/{id}` | Update webhook | Admin |
| DELETE | `/webhooks/{id}` | Delete webhook | Admin |
| POST | `/webhooks/{id}/test` | Send test webhook | Admin |

### Webhook Object

```json
{
  "id": "wh_abc",
  "url": "https://hooks.example.com/alert",
  "events": ["session.created", "message.sent"],
  "enabled": true,
  "secret": "whsec_***",
  "created_at": "2026-07-15T10:00:00"
}
```

Webhook payloads include HMAC-SHA256 signature in the `X-VHTNA-Signature` header.

---

## API Tokens

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api-tokens` | List API tokens | Cookie |
| POST | `/api-tokens` | Create API token | Cookie |
| DELETE | `/api-tokens/{token_id}` | Revoke API token | Cookie |

Tokens are prefixed with `vhtna_` and are returned in full only at creation time (not stored in plaintext). Use as `Authorization: Bearer vhtna_<hex>`.

---

## Calendar

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/calendar/accounts` | List CalDAV accounts | Cookie |
| POST | `/calendar/accounts` | Create CalDAV account | Cookie |
| GET | `/calendar/calendars` | List calendars | Cookie |
| GET | `/calendar/events` | List events | Cookie |
| POST | `/calendar/events` | Create event | Cookie |
| PUT | `/calendar/events/{id}` | Update event | Cookie |
| DELETE | `/calendar/events/{id}` | Delete event | Cookie |

### Calendar Event Object

```json
{
  "id": "evt_abc",
  "calendar_id": "cal_xyz",
  "summary": "Network maintenance window",
  "description": "Planned downtime for core switch firmware upgrade",
  "start": "2026-07-25T02:00:00",
  "end": "2026-07-25T04:00:00",
  "location": "Data Center A"
}
```

---

## Notes

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/notes` | List all notes | Cookie |
| POST | `/notes` | Create note | Cookie |
| GET | `/notes/{id}` | Get note | Cookie |
| PUT | `/notes/{id}` | Update note | Cookie |
| DELETE | `/notes/{id}` | Delete note | Cookie |

### Note Object

```json
{
  "id": "note_abc",
  "owner": "admin",
  "title": "Switch upgrade checklist",
  "content": "1. Backup config\n2. Notify team\n3. Schedule maintenance window",
  "checked": false,
  "created_at": "2026-07-20T15:00:00",
  "updated_at": "2026-07-22T09:00:00"
}
```

---

## Email

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/email/accounts` | List IMAP/SMTP accounts | Cookie |
| POST | `/email/accounts` | Create email account | Cookie |
| GET | `/email/inbox` | List inbox messages | Cookie |
| GET | `/email/messages/{id}` | Get message | Cookie |
| POST | `/email/send` | Send email | Cookie |

### Email Account Object

```json
{
  "id": "mail_abc",
  "owner": "admin",
  "imap_host": "imap.example.com",
  "imap_port": 993,
  "smtp_host": "smtp.example.com",
  "smtp_port": 587,
  "username": "admin@example.com",
  "use_tls": true
}
```

Passwords are encrypted at rest using Fernet encryption.

---

## Gallery

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/gallery/images` | List images | Cookie |
| GET | `/gallery/albums` | List albums | Cookie |
| POST | `/gallery/albums` | Create album | Cookie |
| PUT | `/gallery/albums/{id}` | Update album | Cookie |
| DELETE | `/gallery/albums/{id}` | Delete album | Cookie |

---

## Uploads

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/upload` | Upload file | Cookie |
| GET | `/uploads/{id}` | Download uploaded file | Cookie |

Supports multipart form upload. Files stored in `data/uploads/`.

---

## Compare (Model Comparison)

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/compare/start` | Start compare session (multiple models) | Cookie |
| GET | `/compare/{id}` | Get compare results | Cookie |
| DELETE | `/compare/{id}` | Delete compare session | Cookie |

---

## Skills

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/skills` | List all skills | Cookie |
| POST | `/skills` | Create skill | Cookie |
| PUT | `/skills/{id}` | Update skill | Cookie |
| DELETE | `/skills/{id}` | Delete skill | Cookie |

Skills are reusable prompt templates with optional tool configurations, injected into agent context.

---

## Presets

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/presets` | List chat presets | Cookie |
| POST | `/presets` | Create preset | Cookie |
| PUT | `/presets/{id}` | Update preset | Cookie |
| DELETE | `/presets/{id}` | Delete preset | Cookie |

---

## Shell

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/shell/stream` | Shell command (streaming output) | Agent only |

Used exclusively by the agent's bash tool. Not exposed to the browser UI. Cross-site request protection via `Sec-Fetch-Site` header check.

---

## Speech

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/stt` | Speech-to-text | Cookie |
| POST | `/tts` | Text-to-speech | Cookie |

### TTS Request

```json
{
  "text": "Hello, this is a test message.",
  "voice": "af_heart",
  "speed": 1.0
}
```

STT accepts audio file uploads (`multipart/form-data`). Returns JSON with transcribed text.

---

## Diagnostics

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/diagnostics` | System health and diagnostics | Admin |
| POST | `/diagnostics/log-tail` | Tail application logs | Admin |

Diagnostics returns system info: disk usage, memory, uptime, service status, database size, and ChromaDB health.

---

## Cookbook (Local Model Serving)

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/cookbook/models` | List cookable models | Admin |
| POST | `/cookbook/setup` | Download and serve a model | Admin |
| POST | `/cookbook/stop` | Stop model server | Admin |
| GET | `/cookbook/status` | Check model server status | Admin |

The cookbook downloads and serves local models (vLLM, llama.cpp, etc.) directly on the server.

---

## Hardware Fit

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/hwfit/recommend` | Get model recommendations for hardware | Cookie |

Accepts GPU/VRAM/RAM specs, returns compatible model recommendations.

---

## Embeddings

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/embeddings` | Generate embeddings (for vector search) | Internal |

---

## Backup

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/backup/export` | Export all data as ZIP | Admin |
| POST | `/backup/import` | Import backed-up data | Admin |

---

## Cleanup

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/cleanup/orphans` | Clean orphaned data | Admin |
| POST | `/cleanup/uploads` | Clean stale uploads | Admin |

---

## Preferences

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/prefs` | Get user preferences | Cookie |
| PUT | `/prefs` | Update user preferences | Cookie |

Preferences are stored per-user and include UI theme, sidebar state, notification settings, and language.

---

## Personal

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/personal/info` | Get personal profile info | Cookie |
| PUT | `/personal/info` | Update profile | Cookie |

---

## Signature

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/signature/capture` | Capture signature image | Cookie |
| GET | `/signature/{id}` | Get signature | Cookie |
| DELETE | `/signature/{id}` | Delete signature | Cookie |

Signature data (PNG) is encrypted at rest.

---

## Contacts

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/contacts` | List contacts | Cookie |
| POST | `/contacts` | Create contact | Cookie |
| PUT | `/contacts/{id}` | Update contact | Cookie |
| DELETE | `/contacts/{id}` | Delete contact | Cookie |

---

## Editor Drafts

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/editor-drafts` | List editor drafts | Cookie |
| POST | `/editor-drafts` | Save draft | Cookie |
| DELETE | `/editor-drafts/{id}` | Delete draft | Cookie |

---

## History

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/history/search` | Search across all chat history | Cookie |

---

## Vault

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/vault` | List vault items | Cookie |
| POST | `/vault` | Create vault item (encrypted) | Cookie |
| PUT | `/vault/{id}` | Update vault item | Cookie |
| DELETE | `/vault/{id}` | Delete vault item | Cookie |

Vault items are encrypted at rest using Fernet encryption.

---

## Assistant

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/assistant/action` | Execute assistant action | Cookie |

---

## Emoji

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/emoji/list` | List custom emojis | Cookie |
| POST | `/emoji/upload` | Upload custom emoji | Cookie |

---

## Font

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/font/list` | List available fonts | Cookie |
| POST | `/font/upload` | Upload custom font | Cookie |

---

## Search

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/search` | Search across all features | Cookie |

Cross-feature search: sessions, documents, notes, memories, contacts, and email.

---

## Admin Wipe

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/admin/wipe/{table}` | Wipe all data in a table | Admin |

Accepts a table name parameter. Requires explicit confirmation.

---

## Static Files

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/` | Serve SPA (index.html) | Cookie (redirect to /login if auth) |
| GET | `/{page}` | Serve HTML pages (Calendar, Notes, etc.) | Cookie |
| GET | `/*` | Static assets (CSS, JS, images) | None |

### Page Routes

These HTML pages are served with CSP nonce injection:

| Route | File | Description |
|---|---|---|
| `/` | `static/index.html` | Main SPA |
| `/login` | `static/login.html` | Login page |
| `/landing` | `static/landing.html` | Marketing landing page |
| `/docs` | `docs/index.html` | Project documentation page |
| `/mcp/oauth/authorize/{id}` | `static/mcp-oauth.html` | MCP OAuth authorization |
