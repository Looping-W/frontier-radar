from frontier_radar.services.health import HealthService


class UnavailableRepository:
    def check_connection(self):
        return False, "connection refused"


def test_health_service_reports_database_unavailable():
    """Catches a health result that hides a failed database connection."""
    status = HealthService(UnavailableRepository()).check()

    assert status.application == "ok"
    assert status.database == "unavailable"
    assert status.detail == "connection refused"
