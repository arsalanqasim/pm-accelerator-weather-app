"""Pytest fixtures.

Two important tricks live here:

1. DATABASE_URL is pointed at a throwaway SQLite file *before* the app
   package is imported, so tests never touch the real database.
2. Every external API call in app.services is replaced with a fake
   (monkeypatched), so the tests run offline and deterministically --
   no real requests to Open-Meteo or Wikipedia.
"""

import os
import tempfile

# Must happen before `app.database` is imported anywhere.
os.environ["DATABASE_URL"] = (
    "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test_weather.db")
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import services  # noqa: E402
from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import WeatherRecord  # noqa: E402

Base.metadata.create_all(bind=engine)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

FAKE_PLACE = {
    "name": "Islamabad",
    "country": "Pakistan",
    "admin1": "Islamabad",
    "latitude": 33.6938,
    "longitude": 73.0652,
}


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Replace all outbound API calls with predictable fakes."""

    def fake_geocode(query):
        if "nowhere" in query.lower():
            raise services.LocationNotFound(
                f"Location '{query}' could not be found"
            )
        return dict(FAKE_PLACE)

    def fake_archive(latitude, longitude, start_date, end_date):
        # avg_temp depends on the number of days so tests can prove that
        # updating a record's dates really refetched the temperatures.
        days = (end_date - start_date).days + 1
        return {
            "avg_temp": 20.0 + days,
            "min_temp": 11.0,
            "max_temp": 31.0,
            "days_with_data": days,
        }

    def fake_current(latitude, longitude):
        return {
            "temperature": 24.5,
            "feels_like": 25.0,
            "humidity": 40,
            "wind_speed": 12.0,
            "wind_direction": 90,
            "weather_code": 1,
            "condition": "Mainly clear",
            "icon": "🌤️",
            "observed_at": "2026-10-25T12:00",
            "timezone": "Asia/Karachi",
        }

    def fake_forecast(latitude, longitude, days=5):
        return [
            {
                "date": f"2026-10-{25 + i}",
                "temp_max": 30.0 - i,
                "temp_min": 18.0 - i,
                "precipitation_probability": 10,
                "weather_code": 2,
                "condition": "Partly cloudy",
                "icon": "⛅",
            }
            for i in range(days)
        ]

    def fake_wikipedia(title):
        return {
            "title": "Islamabad",
            "extract": "Islamabad is the capital city of Pakistan.",
            "url": "https://en.wikipedia.org/wiki/Islamabad",
            "thumbnail": None,
        }

    monkeypatch.setattr(services, "geocode_location", fake_geocode)
    monkeypatch.setattr(services, "fetch_archive_temperatures", fake_archive)
    monkeypatch.setattr(services, "fetch_current_weather", fake_current)
    monkeypatch.setattr(services, "fetch_forecast", fake_forecast)
    monkeypatch.setattr(services, "fetch_wikipedia_summary", fake_wikipedia)


@pytest.fixture(autouse=True)
def clean_db():
    """Start every test with an empty records table."""
    db = TestingSession()
    db.query(WeatherRecord).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def make_record(client, **overrides):
    """Helper: create one record through the API and return its JSON."""
    payload = {
        "location": "Islamabad",
        "start_date": "2024-01-01",
        "end_date": "2024-01-10",
        "note": "Winter trip research",
    }
    payload.update(overrides)
    response = client.post("/api/records", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
