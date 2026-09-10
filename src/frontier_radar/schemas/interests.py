from pydantic import BaseModel, ConfigDict, Field


class WeightedInterestInput(BaseModel):
    """Validated name and positive weight received at the CLI/service boundary."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=512)
    weight: int = Field(ge=1, le=5)


class InterestNameInput(BaseModel):
    """Validated display name used to find one existing saved interest term."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=512)


class InterestTerm(BaseModel):
    """A saved profile-owned topic or keyword returned to callers."""

    id: int
    name: str
    weight: int
