"""
vault_routes.py

Vaultwarden / Bitwarden CLI integration — config and unlock endpoints.
The BW_SESSION key persists through core.vault_store, which is
owner-scoped and (under the vault_in_minio feature flag) Fernet-encrypted
in MinIO. Legacy reads still hit data/vault.json when the flag is off.
"""

import logging
import os
import asyncio
from datetime import datetime
from core.time_utils import iso_utc, utcnow
from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.middleware import require_admin
from core.platform_compat import IS_WINDOWS, which_tool
from core.vault_store import load as vault_load, save as vault_save, \
    clear_session as vault_clear_session, delete as vault_delete
from src.auth_helpers import get_current_user

logger = logging.getLogger(__name__)


def _find_bw() -> str:
    """Locate the bw binary, checking PATH and common npm-global locations.

    On Windows the Bitwarden CLI shim is `bw.cmd`/`bw.exe`, resolved by
    which_tool via PATHEXT.
    """
    p = which_tool("bw")
    if p:
        return p
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        for candidate in (
            os.path.join(appdata, "npm", "bw.cmd"),
            os.path.join(appdata, "npm", "bw.exe"),
        ):
            if os.path.isfile(candidate):
                return candidate
        return "bw"
    home = os.path.expanduser("~")
    for candidate in (
        f"{home}/.npm-global/bin/bw",
        f"{home}/.nvm/versions/node/*/bin/bw",
        "/usr/local/bin/bw",
        "/opt/homebrew/bin/bw",
    ):
        if "*" in candidate:
            import glob
            for m in glob.glob(candidate):
                if os.path.isfile(m) and os.access(m, os.X_OK):
                    return m
        elif os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "bw"  # fall back to PATH lookup (will FileNotFoundError, handled below)


def _load_config(owner: str) -> dict:
    return vault_load(owner)


def _save_config(owner: str, cfg: dict) -> None:
    vault_save(owner, cfg)


async def _run_bw(args: list, session: str = None, input_text: str = None,
                  bw_password: str = None) -> tuple:
    env = {}
    env.update(os.environ)
    if session:
        env["BW_SESSION"] = session
    # Secrets must never be passed as argv — process arguments are world-readable
    # via `ps` / `/proc/<pid>/cmdline` to any local user. Keep --passwordenv
    # support for bw commands that need it; unlock/login callers should prefer
    # stdin so the master password is not left in the child environment either.
    if bw_password is not None:
        env["BW_PASSWORD"] = bw_password
    bw_path = _find_bw()
    try:
        proc = await asyncio.create_subprocess_exec(
            bw_path, *args,
            stdin=asyncio.subprocess.PIPE if input_text else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError:
        return "", "bw CLI not installed (install `nodejs-bitwarden-cli` or `bitwarden-cli`)", 127
    except Exception as e:
        return "", f"Failed to launch bw: {e}", 1
    try:
        stdout, stderr = await proc.communicate(input=input_text.encode() if input_text else None)
    except Exception as e:
        return "", f"bw subprocess error: {e}", 1
    return stdout.decode(errors="replace").strip(), stderr.decode(errors="replace").strip(), proc.returncode


class VaultConfig(BaseModel):
    server_url: str = ""
    email: str = ""


class VaultUnlockRequest(BaseModel):
    master_password: str


class VaultLoginRequest(BaseModel):
    email: str
    master_password: str


def setup_vault_routes():
    router = APIRouter(prefix="/api/vault", tags=["vault"])

    @router.get("/config")
    async def get_config(request: Request):
        """Return vault config (no sensitive fields)."""
        require_admin(request)
        owner = get_current_user(request) or ""
        cfg = _load_config(owner)
        return {
            "server_url": cfg.get("server_url", ""),
            "email": cfg.get("email", ""),
            "unlocked": bool(cfg.get("session")),
            "unlocked_at": cfg.get("unlocked_at", ""),
            "bw_installed": await _check_bw_installed(),
        }

    @router.post("/config")
    async def save_config(req: VaultConfig, request: Request):
        """Save vault URL + email. Runs 'bw config server' to point at Vaultwarden."""
        require_admin(request)
        owner = get_current_user(request) or ""
        cfg = _load_config(owner)
        cfg["server_url"] = req.server_url.strip().rstrip("/")
        cfg["email"] = req.email.strip()

        if cfg["server_url"]:
            _, stderr, rc = await _run_bw(["config", "server", cfg["server_url"]])
            if rc != 0:
                return {"ok": False, "error": f"bw config failed: {stderr[:300]}"}

        _save_config(owner, cfg)
        return {"ok": True}

    @router.post("/login")
    async def login(req: VaultLoginRequest, request: Request):
        """Log in to Vaultwarden (required once per account)."""
        require_admin(request)
        owner = get_current_user(request) or ""
        cfg = _load_config(owner)
        # Update email
        cfg["email"] = req.email
        _save_config(owner, cfg)

        stdout, stderr, rc = await _run_bw(
            ["login", req.email, "--raw"],
            input_text=req.master_password + "\n",
        )
        if rc != 0:
            # Already logged in is OK
            if "already logged in" in stderr.lower():
                return {"ok": True, "already": True}
            return {"ok": False, "error": f"Login failed: {stderr[:300]}"}
        # bw login --raw prints session key on success (when 2FA disabled)
        if stdout:
            cfg["session"] = stdout
            cfg["unlocked_at"] = iso_utc(utcnow())
            _save_config(owner, cfg)
        return {"ok": True}

    @router.post("/unlock")
    async def unlock(req: VaultUnlockRequest, request: Request):
        """Unlock the vault and save the session key."""
        require_admin(request)
        owner = get_current_user(request) or ""
        # Pass the master password on stdin, not argv. argv is visible through
        # `ps` / /proc/<pid>/cmdline; stdin also avoids leaving the secret in
        # the child process environment.
        stdout, stderr, rc = await _run_bw(
            ["unlock", "--raw"],
            input_text=req.master_password + "\n",
        )
        if rc != 0:
            return {"ok": False, "error": f"Unlock failed: {stderr[:300]}"}
        session = stdout.strip()
        if not session:
            return {"ok": False, "error": "bw returned empty session"}
        cfg = _load_config(owner)
        cfg["session"] = session
        cfg["unlocked_at"] = iso_utc(utcnow())
        _save_config(owner, cfg)
        return {"ok": True, "message": "Vault unlocked"}

    @router.post("/lock")
    async def lock(request: Request):
        """Lock the vault (clear session from config)."""
        require_admin(request)
        owner = get_current_user(request) or ""
        vault_clear_session(owner)
        # Also tell bw to lock
        await _run_bw(["lock"])
        return {"ok": True, "message": "Vault locked"}

    @router.post("/logout")
    async def logout(request: Request):
        """Log out of the Bitwarden CLI completely."""
        require_admin(request)
        owner = get_current_user(request) or ""
        await _run_bw(["logout"])
        vault_delete(owner)
        return {"ok": True}

    return router


async def _check_bw_installed() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            _find_bw(), "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False
