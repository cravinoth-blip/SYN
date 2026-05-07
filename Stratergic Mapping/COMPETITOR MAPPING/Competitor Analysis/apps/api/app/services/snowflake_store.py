from __future__ import annotations

from typing import Any

from app.core.config import get_settings


settings = get_settings()


class SnowflakeWorkspaceStore:
    """Thin Snowflake boundary.

    The MVP keeps local JSON persistence available for development. This class captures the
    intended integration point with the existing STRATEGIC_WORKSPACE table so route/service
    code does not grow Snowflake-specific details.
    """

    def enabled(self) -> bool:
        return bool(settings.snowflake_account and settings.snowflake_user)

    def upsert_workspace_json(self, project_id: str, workspace_json: dict[str, Any]) -> None:
        if not self.enabled():
            return
        # Implementation intentionally deferred until the exact STRATEGIC_WORKSPACE contract
        # is inspected. Keep this as the only write boundary for workspace JSON.
        _ = (project_id, workspace_json)

    def record_generation_passes(self, project_id: str, run_json: dict[str, Any]) -> None:
        if not self.enabled():
            return
        _ = (project_id, run_json)


snowflake_store = SnowflakeWorkspaceStore()
