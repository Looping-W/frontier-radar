from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """MySQL connection settings loaded from the local environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mysql_host: str = Field(validation_alias="MYSQL_HOST")
    mysql_port: int = Field(validation_alias="MYSQL_PORT")
    mysql_database: str = Field(validation_alias="MYSQL_DATABASE")
    mysql_user: str = Field(validation_alias="MYSQL_USER")
    mysql_password: str = Field(validation_alias="MYSQL_PASSWORD")

    @property
    def database_url(self) -> str:
        return URL.create(
            drivername="mysql+pymysql",
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            username=self.mysql_user,
            password=self.mysql_password,
        ).render_as_string(hide_password=False)
