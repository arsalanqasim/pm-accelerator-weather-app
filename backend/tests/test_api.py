"""API tests for the weather app backend.

All external HTTP calls are mocked in conftest.py, so this suite runs
fully offline. Coverage: health, current weather/forecast, record CRUD,
date validation, unknown locations, and exports.
"""

import pytest

from .conftest import make_record


# ---------------------------------------------------------------------------
# Health and live weather endpoints
# ---------------------------------------------------------------------------

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_current_weather_by_query(client):
    response = client.get("/api/weather/current", params={"q": "Islamabad"})
    assert response.status_code == 200
    body = response.json()
    assert body["location"]["name"] == "Islamabad"
    assert body["current"]["temperature"] == 24.5
    assert body["current"]["condition"] == "Mainly clear"


def test_current_weather_by_coordinates(client):
    response = client.get(
        "/api/weather/current", params={"lat": 33.69, "lon": 73.06}
    )
    assert response.status_code == 200
    assert response.json()["current"]["temperature"] == 24.5


def test_current_weather_needs_query_or_coordinates(client):
    response = client.get("/api/weather/current")
    assert response.status_code == 400


def test_current_weather_unknown_location(client):
    response = client.get("/api/weather/current", params={"q": "nowhere-city"})
    assert response.status_code == 404
    assert "could not be found" in response.json()["detail"]


def test_forecast_returns_five_days(client):
    response = client.get("/api/weather/forecast", params={"q": "Islamabad"})
    assert response.status_code == 200
    assert len(response.json()["forecast"]) == 5


def test_location_info_includes_wikipedia_map_and_youtube(client):
    response = client.get("/api/location/info", params={"q": "Islamabad"})
    assert response.status_code == 200
    body = response.json()
    assert body["wikipedia"]["extract"].startswith("Islamabad is the capital")
    assert "openstreetmap.org" in body["map_embed_url"]
    assert "youtube.com/results" in body["youtube_search_url"]


# ---------------------------------------------------------------------------
# Records: create / read / update / delete
# ---------------------------------------------------------------------------

def test_create_record(client):
    record = make_record(client)
    assert record["location_query"] == "Islamabad"
    assert record["resolved_name"] == "Islamabad, Pakistan"
    # Fake archive: 10 days -> avg 20 + 10 = 30.0
    assert record["avg_temp"] == 30.0
    assert record["min_temp"] == 11.0
    assert record["max_temp"] == 31.0
    assert record["note"] == "Winter trip research"


def test_list_and_read_record(client):
    created = make_record(client)
    listing = client.get("/api/records")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    single = client.get(f"/api/records/{created['id']}")
    assert single.status_code == 200
    assert single.json()["id"] == created["id"]


def test_read_missing_record_returns_404(client):
    response = client.get("/api/records/9999")
    assert response.status_code == 404


def test_update_note_only(client):
    created = make_record(client)
    response = client.put(
        f"/api/records/{created['id']}", json={"note": "Updated note"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["note"] == "Updated note"
    # Dates untouched, temperatures untouched.
    assert body["avg_temp"] == created["avg_temp"]


def test_update_dates_refetches_temperatures(client):
    created = make_record(client)
    response = client.put(
        f"/api/records/{created['id']}",
        json={"start_date": "2024-01-01", "end_date": "2024-01-05"},
    )
    assert response.status_code == 200
    body = response.json()
    # 5 days now -> fake archive avg becomes 20 + 5 = 25.0
    assert body["avg_temp"] == 25.0
    assert body["end_date"] == "2024-01-05"


def test_delete_record(client):
    created = make_record(client)
    response = client.delete(f"/api/records/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/records/{created['id']}").status_code == 404


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_create_rejects_end_before_start(client):
    response = client.post(
        "/api/records",
        json={
            "location": "Islamabad",
            "start_date": "2024-01-10",
            "end_date": "2024-01-01",
        },
    )
    assert response.status_code == 422


def test_create_rejects_future_end_date(client):
    response = client.post(
        "/api/records",
        json={
            "location": "Islamabad",
            "start_date": "2999-01-01",
            "end_date": "2999-01-10",
        },
    )
    assert response.status_code == 422


def test_create_rejects_range_over_92_days(client):
    response = client.post(
        "/api/records",
        json={
            "location": "Islamabad",
            "start_date": "2024-01-01",
            "end_date": "2024-06-01",
        },
    )
    assert response.status_code == 422


def test_create_rejects_unknown_location(client):
    response = client.post(
        "/api/records",
        json={
            "location": "nowhere-town",
            "start_date": "2024-01-01",
            "end_date": "2024-01-10",
        },
    )
    assert response.status_code == 404


def test_update_rejects_invalid_merged_range(client):
    created = make_record(client)
    # Moving only the start date past the existing end date must fail.
    response = client.put(
        f"/api/records/{created['id']}", json={"start_date": "2024-02-01"}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def test_export_json(client):
    make_record(client)
    response = client.get("/api/records/export", params={"format": "json"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["resolved_name"] == "Islamabad, Pakistan"


def test_export_csv(client):
    make_record(client)
    response = client.get("/api/records/export", params={"format": "csv"})
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("id,location_query,resolved_name")
    assert "Islamabad, Pakistan" in lines[1]


def test_export_markdown(client):
    make_record(client)
    response = client.get("/api/records/export", params={"format": "markdown"})
    assert response.status_code == 200
    assert "# Weather Records" in response.text
    assert "Islamabad, Pakistan" in response.text


def test_export_xml(client):
    make_record(client)
    response = client.get("/api/records/export", params={"format": "xml"})
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<resolved_name>Islamabad, Pakistan</resolved_name>" in response.text


def test_export_pdf(client):
    make_record(client)
    response = client.get("/api/records/export", params={"format": "pdf"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_export_rejects_unknown_format(client):
    response = client.get("/api/records/export", params={"format": "yaml"})
    assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
