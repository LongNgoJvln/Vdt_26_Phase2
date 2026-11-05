"""
core/feature_flags.py

Centralized feature-flag system for deployment-level feature gating.

Reads from environment variables (``.env``) — NOT from the database — because
these are deployment-level configuration decisions.  Feature flags control
whether entire backend routes are registered / frontend panels are shown.

To change feature flags at runtime, use Admin > System > Feature Flags.

Convenience shortcuts:
    ``OFFLINE_MODE=true``  disables ALL internet-dependent features at once.
    ``OFFLINE_MODE=false`` (or unset) lets individual flags take over.

Usage:
    from core.feature_flags import features

    if features.email:
        app.include_router(email_router)

    if features.is_enabled("web_search"):
        # same as features.web_search

    features.to_dict()
    # {"email": false, "web_search": false, "calendar": true, ...}
"""

import os
import logging

from core.app_profile import profile

logger = logging.getLogger(__name__)

# ── Environment variable prefix ────────────────────────────────────────
_PREFIX = "ODYSSEUS_FEATURE_"

# ── Feature definitions ────────────────────────────────────────────────
# (key, env_suffix, default, description)
_FEATURES = [
    # ── Internet-dependent (disabled when OFFLINE_MODE=true) ────────
    ("email",       "EMAIL",       False, "IMAP/SMTP email integration"),
    ("web_search",  "WEB_SEARCH",  False, "SearXNG / external web search"),
    ("research",    "RESEARCH",    False, "Deep Research (multi-step web synthesis)"),
    ("gallery",     "GALLERY",     False, "Generated image library"),
    ("compare",     "COMPARE",     False, "Multi-model side-by-side comparison"),
    ("cookbook",    "COOKBOOK",    False, "Model download/serve (HuggingFace)"),
    ("webhooks",    "WEBHOOKS",    False, "Outgoing webhook notifications"),
    ("companion",   "COMPANION",   False, "LAN companion pairing (QR codes)"),

    # ── Core productivity (always enabled by default) ────────────────
    ("calendar",    "CALENDAR",    True,  "Calendar (CalDAV sync)"),
    ("notes",       "NOTES",       True,  "Notes / Todos / Reminders"),
    ("tasks",       "TASKS",       True,  "Scheduled background tasks"),
    ("memory",      "MEMORY",      True,  "Persistent memory + vector search"),
    ("skills",      "SKILLS",      True,  "Agent skill definitions"),
    ("documents",   "DOCUMENTS",   True,  "Multi-tab document editor"),
    ("shell",       "SHELL",       True,  "Shell command execution"),
    ("presets",     "PRESETS",     True,  "Chat configuration presets"),
    ("settings",    "SETTINGS",    True,  "Application settings panel"),
    ("search_chats","SEARCH_CHATS",True,  "Chat message search (Ctrl+K)"),

    # ── Optional / debugging ─────────────────────────────────────────
    ("diagnostics", "DIAGNOSTICS", False, "Diagnostics and debug endpoints"),
    ("tts",         "TTS",         True,  "Text-to-speech"),
    ("stt",         "STT",         True,  "Speech-to-text"),
]

# Features that OFFLINE_MODE=true disables automatically
_OFFLINE_DISABLED = frozenset({
    "email", "web_search", "research", "gallery", "compare",
    "cookbook", "webhooks", "companion",
})

# Minimal deployment mode features (env var controlled — individual flags can
# still override when DEPLOY_MODE=minimal is set)
_MINIMAL_DEFAULTS = frozenset({"research", "documents", "settings"})


# ── Infrastructure flags ──────────────────────────────────────────────
# These are NOT user-facing features — they control storage topology and
# multi-tenant safety. Always default OFF so existing deployments keep
# behaving identically until an operator opts in. Names use the `ODYSSEUS_*`
# prefix directly (no `FEATURE_`) to distinguish from the feature surface.
_INFRA_PREFIX = "ODYSSEUS_"
_INFRA_FLAGS = [
    # (key, env_suffix, default, description)
    ("multitenant_postgres", "MULTITENANT_POSTGRES", False,
     "Use Postgres + Alembic as the primary DB (else SQLite legacy path)"),
    ("scheduled_emails_in_db", "SCHEDULED_EMAILS_IN_DB", False,
     "Persist scheduled email tables in Postgres (else shadow SQLite db)"),
    ("scheduled_emails_dual_write", "SCHEDULED_EMAILS_DUAL_WRITE", False,
     "Write scheduled email rows to both SQLite and Postgres during cutover"),
    ("uploads_in_db", "UPLOADS_IN_DB", False,
     "Persist upload index in the Uploads table (else uploads.json)"),
    ("uploads_dual_write", "UPLOADS_DUAL_WRITE", False,
     "Write upload records to both JSON and DB during cutover"),
    ("vault_in_minio", "VAULT_IN_MINIO", False,
     "Persist vault per-owner encrypted in MinIO (else single vault.json)"),
    ("vault_dual_write", "VAULT_DUAL_WRITE", False,
     "Write vault to both JSON and MinIO during cutover"),
    ("sessions_in_db", "SESSIONS_IN_DB", False,
     "Persist auth sessions in DB (else sessions.json)"),
    ("sessions_dual_write", "SESSIONS_DUAL_WRITE", False,
     "Write auth sessions to both JSON and DB during cutover"),
    ("memory_in_db", "MEMORY_IN_DB", False,
     "Persist memories in the Memory table (else memory.json)"),
    ("memory_dual_write", "MEMORY_DUAL_WRITE", False,
     "Write memories to both JSON and DB during cutover"),
    ("research_in_minio", "RESEARCH_IN_MINIO", False,
     "Persist deep-research results per-owner in MinIO (else flat data/deep_research/)"),
    ("research_dual_write", "RESEARCH_DUAL_WRITE", False,
     "Write deep-research results to both JSON and MinIO during cutover"),
    ("user_settings_in_db", "USER_SETTINGS_IN_DB", False,
     "Persist per-user setting overrides in user_settings table (else user_prefs.json)"),
    ("user_settings_dual_write", "USER_SETTINGS_DUAL_WRITE", False,
     "Write per-user setting overrides to both JSON and DB during cutover"),
]


class FeatureFlags:
    """Immutable snapshot of deployment-level feature flags.

    Each flag is a boolean attribute::

        >>> features.email
        True
        >>> features.is_enabled("web_search")
        True
    """

    def __init__(self):
        self._data: dict[str, bool] = {}
        self._offline_mode = os.getenv("OFFLINE_MODE", "").lower() in ("1", "true", "yes")
        self._deploy_mode = os.getenv("ODYSSEUS_DEPLOY_MODE", "").lower()

        if self._offline_mode:
            logger.info("OFFLINE_MODE=true — internet-dependent features are disabled")

        if self._deploy_mode == "minimal":
            logger.info("ODYSSEUS_DEPLOY_MODE=minimal — only research, documents, and settings are enabled by default")
        elif self._deploy_mode == "enterprise":
            logger.info("ODYSSEUS_DEPLOY_MODE=enterprise — all features enabled by default (current behaviour)")

        for key, suffix, default, _desc in _FEATURES:
            env_val = os.getenv(f"{_PREFIX}{suffix}")
            if key in profile.disabled_ui_features():
                # APP_PROFILE is the product boundary. Old feature env vars
                # cannot resurrect routes/tools that this build excludes.
                enabled = False
            elif env_val is not None:
                # Explicit per-feature env var takes priority over everything
                enabled = env_val.lower() in ("1", "true", "yes")
            elif self._offline_mode and key in _OFFLINE_DISABLED:
                # OFFLINE_MODE overrides default for internet features
                enabled = False
            elif self._deploy_mode == "minimal" and key not in _MINIMAL_DEFAULTS:
                # Minimal mode: everything disabled except research, documents, settings
                enabled = False
            elif self._deploy_mode == "enterprise" and key not in _MINIMAL_DEFAULTS:
                # Enterprise mode: everything enabled by default
                enabled = True
            else:
                enabled = default

            self._data[key] = enabled
            # Expose as attribute (immutable via __setattr__)
            object.__setattr__(self, key, enabled)

        # Infra flags — independent of OFFLINE_MODE and DEPLOY_MODE.
        # Stored in a separate namespace so feature_flag consumers (UI
        # panels, route gating) don't see them mixed in.
        self._infra: dict[str, bool] = {}
        for key, suffix, default, _desc in _INFRA_FLAGS:
            env_var = f"{_INFRA_PREFIX}{suffix}"
            env_val = os.getenv(env_var)
            enabled = (env_val.lower() in ("1", "true", "yes")) if env_val is not None else default
            self._infra[key] = enabled

        _infra_on = [k for k, v in self._infra.items() if v]
        if _infra_on:
            logger.info("Infra flags ON (%d): %s", len(_infra_on), ", ".join(sorted(_infra_on)))

        # Log disabled features for operational visibility
        _disabled = [k for k, v in self._data.items() if not v]
        if _disabled:
            logger.info(
                "Disabled features (%d): %s",
                len(_disabled),
                ", ".join(sorted(_disabled)),
            )
        else:
            logger.info("All features enabled")

    def __setattr__(self, name, value):
        """Prevent mutation after initialization."""
        if name in ("_data", "_infra", "_offline_mode", "_deploy_mode"):
            super().__setattr__(name, value)
            return
        raise AttributeError(
            f"FeatureFlags is immutable after creation. "
            f"Cannot set '{name}'. Use environment variables."
        )

    def is_enabled(self, name: str) -> bool:
        """Check if a named feature is enabled.

        Unknown feature names default to ``True`` (safe fallback).
        """
        return self._data.get(name, True)

    def infra_enabled(self, name: str) -> bool:
        """Check an infra flag (storage topology / multi-tenant safety).

        Unknown names default to ``False`` (safer for migration work —
        flags must be explicitly turned on).
        """
        return self._infra.get(name, False)

    def infra_to_dict(self) -> dict[str, bool]:
        """Return infra flags as a JSON-serializable dict."""
        return dict(self._infra)

    def to_dict(self) -> dict[str, bool]:
        """Return all feature flags as a JSON-serializable dict."""
        return dict(self._data)

    def disabled_set(self) -> set[str]:
        """Return the set of disabled feature keys."""
        return {k for k, v in self._data.items() if not v}

    @property
    def mode(self) -> str:
        """Return the active deployment/product mode."""
        return profile.name if profile.is_network_change else self._deploy_mode


# ── Singleton (import-time, shared across the process) ─────────────────
features = FeatureFlags()
