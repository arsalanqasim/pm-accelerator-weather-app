# Weather App — PM Accelerator AI Engineer Intern Assessment

**by Arsalan Qasim**

A full-stack weather application built for the PM Accelerator "AI Engineer
Intern" technical assessment. It covers **both** parts of the assessment:

- **Part 1 (Frontend):** a React app to search any place, see its current
  weather and 5-day forecast, and use browser geolocation.
- **Part 2 (Backend):** a FastAPI service with a database of saved
  historical weather queries (full CRUD), extra API integrations
  (Wikipedia, OpenStreetMap, YouTube) and data export in five formats.

All weather data is real and live, from the **Open-Meteo** APIs, which are
free and require no API key.

## Features

- 🔎 Search weather by city, town, zip code or landmark name
  (fuzzy: the best geocoding match is used and the resolved name shown)
- 📍 "Use my location" button — weather for your GPS coordinates
- 🌡️ Current conditions with icon, feels-like, humidity and wind
- 📅 5-day forecast grid with rain probability
- ℹ️ Location info panel: Wikipedia summary, embedded OpenStreetMap map,
  and a YouTube search link for videos of the place
- 💾 Saved weather queries: store the temperature summary of a place over
  a past date range, then list / edit / delete them (full CRUD)
- ⬇️ Export all saved queries as **JSON, CSV, XML, Markdown or PDF**
- ⚠️ Friendly error handling everywhere — an unknown city or a failed API
  call shows a clear message, never a blank page

## Tech stack

| Layer    | Technology |
|----------|------------|
| Frontend | React 18 + Vite (JavaScript), plain CSS |
| Backend  | Python, FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite |
| Data     | Open-Meteo geocoding / forecast / archive APIs, Wikipedia REST API, OpenStreetMap |
| Tests    | pytest (24 tests, external HTTP mocked — runs fully offline) |

## How to run

You need two terminals: one for the backend, one for the frontend.

### 1. Backend (port 8000)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive API docs (Swagger UI): http://localhost:8000/docs

Run the backend tests:

```bash
cd backend
python -m pytest tests/ -q
```

### 2. Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

> The frontend expects the backend at `http://localhost:8000`. To change
> it, set the `VITE_API_URL` environment variable before `npm run dev`.

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/weather/current?q=Islamabad` | Current weather by place name |
| GET | `/api/weather/current?lat=33.7&lon=73.1` | Current weather by coordinates |
| GET | `/api/weather/forecast?q=...` or `?lat&lon` | 5-day forecast |
| GET | `/api/location/info?q=Islamabad` | Wikipedia summary + map embed + YouTube link |
| POST | `/api/records` | Create a saved query `{location, start_date, end_date, note?}` |
| GET | `/api/records` | List all saved queries |
| GET | `/api/records/{id}` | Read one saved query |
| PUT | `/api/records/{id}` | Update note and/or dates (temperatures refetched if dates change) |
| DELETE | `/api/records/{id}` | Delete a saved query |
| GET | `/api/records/export?format=json\|csv\|xml\|markdown\|pdf` | Download all records |

Validation rules for records: dates must be valid, `start_date <= end_date`,
`end_date` must not be in the future, and the range must be ≤ 92 days.
Locations that cannot be resolved return a clear `404` error; upstream API
failures return `502`.

## Project structure

```
backend/
  app/
    main.py        FastAPI app: all HTTP endpoints
    database.py    SQLAlchemy engine/session setup (SQLite)
    models.py      WeatherRecord database model
    schemas.py     Pydantic request/response schemas + date validation
    services.py    Open-Meteo + Wikipedia calls, weather-code table
    exporters.py   JSON / CSV / XML / Markdown / PDF exporters
  tests/           pytest suite (external HTTP mocked)
  requirements.txt
frontend/
  src/
    App.jsx              root component + page layout
    api.js               small fetch client for the backend
    components/          SearchBar, CurrentWeather, Forecast,
                         LocationInfo, RecordsPanel
    index.css            all styling (plain CSS, responsive)
```

## Assessment coverage

| Requirement | Where it is implemented |
|---|---|
| Location search → current weather with icon | `SearchBar.jsx`, `CurrentWeather.jsx`; `GET /api/weather/current`; WMO code → label/icon table in `services.py` |
| Weather for the user's current location | Geolocation button in `SearchBar.jsx` → `?lat&lon` endpoints |
| 5-day forecast | `Forecast.jsx`; `GET /api/weather/forecast` (`forecast_days=5`) |
| Graceful error handling (unknown city, API failure) | Backend returns JSON errors (404/502/422); frontend shows a friendly banner (`App.jsx`, `api.js`) |
| Responsive design | `index.css` grid + media queries |
| Name + PM Accelerator description in the app | Header ("by Arsalan Qasim") and footer in `App.jsx` |
| CRUD over a database | `WeatherRecord` model; POST/GET/PUT/DELETE `/api/records`; `RecordsPanel.jsx` |
| Date-range temperature query stored in DB | POST `/api/records` uses the Open-Meteo archive API (`services.fetch_archive_temperatures`) |
| Input validation (dates, real location) | `schemas.py` validators; geocoding must resolve or 404 |
| Extra API integration | `GET /api/location/info`: Wikipedia summary, OpenStreetMap embed, YouTube search link |
| Data export (JSON/CSV/XML/PDF/Markdown) | `exporters.py`; `GET /api/records/export`; buttons in `RecordsPanel.jsx` |
| Tests | `backend/tests/` — 24 pytest tests with mocked HTTP |

## Demo video

_Demo video (~2 minutes, walkthrough of both parts):
https://drive.google.com/file/d/1IXAW40Og-hlGitEE2MyedghaZibBQ6U2/view?usp=drivesdk_
