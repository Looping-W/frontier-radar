from typing import Protocol

from frontier_radar.schemas.health import HealthStatus


class HealthRepository(Protocol):
    def check_connection(self) -> tuple[bool, str | None]: ...


class HealthService:
    """Build the health result exposed by the CLI."""

    def __init__(self, repository: HealthRepository) -> None:
        self._repository = repository

    def check(self) -> HealthStatus:
        is_available, detail = self._repository.check_connection()
        return HealthStatus(
            database="ok" if is_available else "unavailable",
            detail=detail,
        )
