from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError


class DatabaseHealthRepository:
    """Run a minimal query to verify a configured database connection."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check_connection(self) -> tuple[bool, str | None]:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            return False, str(error)
        return True, None
