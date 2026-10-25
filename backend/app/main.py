"""Weather App API — FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Endpoints
---------
Weather (Part 1 support):
    GET  /api/weather/current?q=Islamabad            current weather by place name
    GET  /api/weather/current?lat=33.7&lon=73.1      current weather by coordinates
    GET  /api/weather/forecast?q=... | ?lat&lon      5-day forecast
    GET  /api/location/info?q=Islamabad              Wikipedia summary + map + videos

Records (Part 2, CRUD over saved historical queries):
    POST   /api/records            create (fetches archive temperatures)
    GET    /api/records            list all
    GET    /api/records/{id}       read one
    PUT    /api/records/{id}       update note and/or dates (refetches if dates change)
    DELETE /api/records/{id}       delete
    GET    /api/records/export?format=json|csv|xml|markdown|pdf
"""

from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import exporters, schemas, services
from .database import Base, engine, get_db
from .models import WeatherRecord

# Create the SQLite tables on startup if they do not exist yet.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Weather App API", version="1.0.0")

# The Vite dev server runs on a different port, so browsers need CORS
# permission to call this API from the frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def resolve_place(q: Optional[str], lat: Optional[float], lon: Optional[float]):
    """Turn either a text query or a coordinate pair into a place dict.

    Raises HTTPException(400) when neither is given, HTTPException(404)
    when the text query matches no real place.
    """
    if q:
        try:
            return services.geocode_location(q)
        except services.LocationNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except services.UpstreamError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    if lat is not None and lon is not None:
        # Coordinates from the browser's geolocation have no place name,
        # so the location is labelled generically.
        return {
            "name": "Current location",
            "country": None,
            "latitude": lat,
            "longitude": lon,
        }
    raise HTTPException(
        status_code=400,
        detail="Provide either a location query (?q=...) or coordinates (?lat=...&lon=...).",
    )


def place_summary(place):
    """The location block included in weather responses."""
    return {
        "name": place["name"],
        "country": place.get("country"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Weather endpoints
# ---------------------------------------------------------------------------

@app.get("/api/weather/current")
def current_weather(
    q: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
):
    """Current weather for a place name or a coordinate pair."""
    place = resolve_place(q, lat, lon)
    try:
        weather = services.fetch_current_weather(place["latitude"], place["longitude"])
    except services.UpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"location": place_summary(place), "current": weather}


@app.get("/api/weather/forecast")
def forecast(
    q: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
):
    """5-day forecast for a place name or a coordinate pair."""
    place = resolve_place(q, lat, lon)
    try:
        days = services.fetch_forecast(place["latitude"], place["longitude"], days=5)
    except services.UpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"location": place_summary(place), "forecast": days}


@app.get("/api/location/info")
def location_info(q: str = Query(..., min_length=1)):
    """Extra context about a place: Wikipedia summary, map, video search."""
    place = resolve_place(q, None, None)
    return services.build_location_info(place)


# ---------------------------------------------------------------------------
# Records: CRUD over saved historical weather queries
# ---------------------------------------------------------------------------

@app.post("/api/records", response_model=schemas.RecordOut, status_code=201)
def create_record(payload: schemas.RecordCreate, db: Session = Depends(get_db)):
    """Create a record: resolve the place, fetch archive temperatures
    for the date range, and store the summary."""
    try:
        place = services.geocode_location(payload.location)
        temps = services.fetch_archive_temperatures(
            place["latitude"], place["longitude"],
            payload.start_date, payload.end_date,
        )
    except services.LocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except services.UpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    resolved = place["name"]
    if place.get("country"):
        resolved = f"{place['name']}, {place['country']}"

    record = WeatherRecord(
        location_query=payload.location,
        resolved_name=resolved,
        country=place.get("country"),
        latitude=place["latitude"],
        longitude=place["longitude"],
        start_date=payload.start_date,
        end_date=payload.end_date,
        avg_temp=temps["avg_temp"],
        min_temp=temps["min_temp"],
        max_temp=temps["max_temp"],
        note=payload.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# NOTE: this route must be registered before /api/records/{id} so that
# "export" is not mistaken for a record id.
@app.get("/api/records/export")
def export_records(
    format: str = Query("json", pattern="^(json|csv|xml|markdown|pdf)$"),
    db: Session = Depends(get_db),
):
    """Download all records as JSON, CSV, XML, Markdown or PDF."""
    records = db.query(WeatherRecord).order_by(WeatherRecord.id).all()
    content, media_type, filename = exporters.EXPORTERS[format](records)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/records", response_model=List[schemas.RecordOut])
def list_records(db: Session = Depends(get_db)):
    """List every saved record, newest first."""
    return (
        db.query(WeatherRecord)
        .order_by(WeatherRecord.created_at.desc())
        .all()
    )


def get_record_or_404(record_id: int, db: Session) -> WeatherRecord:
    record = db.get(WeatherRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return record


@app.get("/api/records/{record_id}", response_model=schemas.RecordOut)
def read_record(record_id: int, db: Session = Depends(get_db)):
    return get_record_or_404(record_id, db)


@app.put("/api/records/{record_id}", response_model=schemas.RecordOut)
def update_record(
    record_id: int,
    payload: schemas.RecordUpdate,
    db: Session = Depends(get_db),
):
    """Update the note and/or the date range of a record.

    When the dates change, the stored temperatures are refetched from
    the archive API so they always match the range. The merged
    (old + new) range is validated with the same rules as creation.
    """
    record = get_record_or_404(record_id, db)

    new_start = payload.start_date or record.start_date
    new_end = payload.end_date or record.end_date
    dates_changed = (new_start, new_end) != (record.start_date, record.end_date)

    if dates_changed:
        try:
            schemas.validate_date_range(new_start, new_end)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            temps = services.fetch_archive_temperatures(
                record.latitude, record.longitude, new_start, new_end
            )
        except services.UpstreamError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        record.start_date = new_start
        record.end_date = new_end
        record.avg_temp = temps["avg_temp"]
        record.min_temp = temps["min_temp"]
        record.max_temp = temps["max_temp"]

    # exclude_unset distinguishes "field not sent" from "sent as null",
    # so a client can also clear a note by sending note: null.
    if "note" in payload.model_fields_set:
        record.note = payload.note

    db.commit()
    db.refresh(record)
    return record


@app.delete("/api/records/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = get_record_or_404(record_id, db)
    db.delete(record)
    db.commit()
    return Response(status_code=204)
