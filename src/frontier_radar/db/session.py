from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from frontier_radar.core.settings import Settings


def create_engine_and_session_factory(
    settings: Settings,
) -> tuple[Engine, sessionmaker[Session]]:
    """Create the shared MySQL Engine and Session factory."""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    return engine, session_factory
