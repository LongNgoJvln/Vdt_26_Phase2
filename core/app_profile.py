"""Deployment profile for the Network Change monolith.

The upstream UI contains a broad personal-assistant surface.  Deleting those
modules immediately would make upgrades and rollback needlessly risky, so the
Network Change build uses an explicit allow-list at the composition boundary:
routes are not registered and tools are not offered to the model unless they
belong to this product profile.

Set ``APP_PROFILE=legacy`` to temporarily expose the old surface while
investigating a regression.  This compatibility switch is intentionally not a
second architecture; both profiles still use the same monolith and agent loop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


NETWORK_CHANGE_PROFILE = "network_change"


@dataclass(frozen=True)
class AppProfile:
    name: str
    product_name: str

    @property
    def is_network_change(self) -> bool:
        return self.name == NETWORK_CHANGE_PROFILE

    def route_enabled(self, route_group: str) -> bool:
        """Return whether a legacy route group belongs in this deployment."""
        if not self.is_network_change:
            return True
        return route_group in {
            "auth", "uploads", "sessions", "chat", "history", "documents",
            "memory", "skills", "personal", "embeddings", "models", "prefs", "presets",
            "mcp", "api_tokens", "backup", "cleanup", "knowledge",
            "tool_registry", "network_validation",
        }

    def blocked_builtin_tools(self) -> set[str]:
        """Tools hidden and rejected by the Network Change profile.

        ``create_session`` remains available because it is useful to the lead
        loop.  ``send_to_session`` and ``pipeline`` are legacy cross-session /
        multi-model orchestration, not requirements of the single-agent design.
        """
        if not self.is_network_change:
            return set()
        return {
            "bash", "python", "write_file",
            "web_search", "web_fetch", "trigger_research", "manage_research",
            "chat_with_model", "send_to_session", "pipeline", "ask_teacher",
            "generate_image", "edit_image", "compare_models",
            "manage_tasks", "manage_calendar", "manage_notes",
            "list_email_accounts", "send_email", "list_emails", "read_email",
            "reply_to_email", "bulk_email", "archive_email", "delete_email",
            "mark_email_read", "resolve_contact", "manage_contact",
            "manage_webhooks", "app_api",
            "download_model", "serve_model", "list_served_models",
            "stop_served_model", "list_downloads", "cancel_download",
            "search_hf_models", "list_cached_models", "list_serve_presets",
            "serve_preset", "adopt_served_model", "list_cookbook_servers",
        }

    def disabled_ui_features(self) -> set[str]:
        """Feature switches that cannot override the product route boundary."""
        if not self.is_network_change:
            return set()
        return {
            "email", "web_search", "research", "gallery", "compare",
            "cookbook", "webhooks", "companion", "calendar", "notes",
            "tasks", "shell", "diagnostics", "tts", "stt",
        }


def _normalise_profile(value: str | None) -> str:
    value = (value or NETWORK_CHANGE_PROFILE).strip().lower().replace("-", "_")
    if value in {"legacy", "enterprise", "odysseus"}:
        return "legacy"
    return NETWORK_CHANGE_PROFILE


profile = AppProfile(
    name=_normalise_profile(os.getenv("APP_PROFILE")),
    product_name="Network Change",
)
