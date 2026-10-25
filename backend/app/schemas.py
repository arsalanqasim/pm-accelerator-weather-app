"""Pydantic schemas: the shapes of data going in and out of the API.

Schemas are kept separate from the SQLAlchemy models on purpose:
models describe how data is stored, schemas describe what the API
accepts and returns.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# The archive endpoint is used for ranges of at most 92 days (~3 months),
# which keeps requests light and responses meaningful.
MAX_RANGE_DAYS = 92


def validate_date_range(start: date, end: date) -> None:
    """Shared validation for a historical date range.

    Raises ValueError (which FastAPI turns into a 422 response) when:
    - the end date is before the start date
    - the end date is in the future (there is no weather history for it yet)
    - the range is longer than MAX_RANGE_DAYS
    """
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    if end > date.today():
        raise ValueError("end_date cannot be in the future")
    if (end - start).days > MAX_RANGE_DAYS:
        raise ValueError(f"date range cannot exceed {MAX_RANGE_DAYS} days")


class RecordCreate(BaseModel):
    """Body of POST /api/records."""

    location: str = Field(..., min_length=1, max_length=200,
                          description="City, town, zip code or landmark name")
    start_date: date
    end_date: date
    note: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def check_dates(self):
        validate_date_range(self.start_date, self.end_date)
        return self


class RecordUpdate(BaseModel):
    """Body of PUT /api/records/{id}. Every field is optional;

    only the fields the client sends are changed."""

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=1000)


class RecordOut(BaseModel):
    """A weather record as returned by the API."""

    id: int
    location_query: str
    resolved_name: str
    country: Optional[str] = None
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    avg_temp: Optional[float] = None
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Read attributes straight from the SQLAlchemy object.
    model_config = {"from_attributes": True}
