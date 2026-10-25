"""Database models.

A ``WeatherRecord`` is one saved "weather query": a user asked for the
historical temperature of a place over a date range, the backend fetched
the data from the Open-Meteo archive API, and the summary is stored here
so it can be listed, edited, exported and deleted later (the CRUD part
of the assessment).
"""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text

from .database import Base


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)

    # What the user typed, e.g. "islamabad" ...
    location_query = Column(String(200), nullable=False)
    # ... and what the geocoding API resolved it to, e.g. "Islamabad, Pakistan".
    resolved_name = Column(String(200), nullable=False)
    country = Column(String(120), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # The requested historical date range.
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Temperature summary computed from the archive data for that range.
    avg_temp = Column(Float, nullable=True)  # mean of daily mean temperatures
    min_temp = Column(Float, nullable=True)  # lowest daily minimum
    max_temp = Column(Float, nullable=True)  # highest daily maximum

    # Optional free-text note the user can edit later.
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
