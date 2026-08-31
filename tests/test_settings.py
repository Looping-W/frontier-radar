from frontier_radar.core.settings import Settings
from frontier_radar.db.session import create_engine_and_session_factory


def test_settings_builds_mysql_connection_url(monkeypatch):
    """Catches a URL that points to the wrong database or connection endpoint."""
    monkeypatch.setenv("MYSQL_HOST", "db.local")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_DATABASE", "frontier_radar")
    monkeypatch.setenv("MYSQL_USER", "radar")
    monkeypatch.setenv("MYSQL_PASSWORD", "secret")

    settings = Settings()

    assert settings.database_url == (
        "mysql+pymysql://radar:secret@db.local:3307/frontier_radar"
    )


def test_session_factory_uses_configured_mysql_database(monkeypatch):
    """Catches an Engine that ignores the configured MySQL connection details."""
    monkeypatch.setenv("MYSQL_HOST", "db.local")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_DATABASE", "frontier_radar")
    monkeypatch.setenv("MYSQL_USER", "radar")
    monkeypatch.setenv("MYSQL_PASSWORD", "secret")

    engine, session_factory = create_engine_and_session_factory(Settings())

    assert engine.url.drivername == "mysql+pymysql"
    assert engine.url.database == "frontier_radar"
    assert session_factory.kw["autoflush"] is False
    assert session_factory.kw["expire_on_commit"] is False
    engine.dispose()
