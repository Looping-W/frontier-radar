from typing import Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Application and database health reported by the CLI."""

    application: Literal["ok"] = "ok"
    database: Literal["ok", "unavailable"]
    detail: str | None = None
