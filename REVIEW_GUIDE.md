# Review Guide — how this app works, file by file

A plain-language walkthrough for reviewing (and demoing) the weather app.

## The big picture

```
Browser (React, port 5173)
   │  fetch() calls, JSON in / JSON out
   ▼
FastAPI backend (port 8000)
   ├── Open-Meteo geocoding API   → name → coordinates
   ├── Open-Meteo forecast API    → current weather + 5-day forecast
   ├── Open-Meteo archive API     → historical temperatures
   ├── Wikipedia REST API         → place summaries
   └── SQLite database            → saved "weather query" records
```

The frontend never talks to Open-Meteo directly; it only talks to the
backend. That keeps API details in one place (`services.py`) and lets the
backend validate input and shape clean responses.

## End-to-end: what happens when you search "Islamabad"

1. `SearchBar` calls `App.loadWeather({ q: "Islamabad" })`.
2. `api.js` sends `GET /api/weather/current?q=Islamabad` and
   `GET /api/weather/forecast?q=Islamabad` in parallel.
3. In the backend, `resolve_place()` calls
   `services.geocode_location("Islamabad")`, which asks the Open-Meteo
   geocoding API and takes the best (first) match — that's the "fuzzy"
   behaviour: partial names or small typos still resolve, and the UI
   shows the resolved name so the user can see what was matched.
4. `services.fetch_current_weather()` / `fetch_forecast()` call the
   forecast API with those coordinates. Raw WMO weather codes (0, 1, 61…)
   are translated to a label + emoji by the `WEATHER_CODES` table.
5. React renders `CurrentWeather` and `Forecast`. Because a text search
   was used, `GET /api/location/info` is also called and `LocationInfo`
   shows the Wikipedia summary, the OpenStreetMap embed and a YouTube
   search link.
6. If anything fails — unknown place (404), weather service down (502) —
   the API returns `{"detail": "..."}` and the UI shows that sentence in
   a red banner instead of breaking.

## Backend files

- **`app/main.py`** — the FastAPI application. Defines every endpoint,
  the CORS settings (so the Vite dev server on port 5173 may call it),
  and the CRUD logic. Note the `/api/records/export` route is registered
  *before* `/api/records/{id}` so "export" is never mistaken for an id.
  `resolve_place()` is the shared helper for "query text OR coordinates".
- **`app/database.py`** — SQLAlchemy engine for a single SQLite file,
  a session factory, and the `get_db` dependency that gives each request
  its own session and closes it afterwards.
- **`app/models.py`** — one table, `weather_records`. A record stores the
  query text, the resolved place (name, country, lat/lon), the date
  range, the computed avg/min/max temperatures, an optional note, and
  timestamps.
- **`app/schemas.py`** — Pydantic models for requests/responses.
  `validate_date_range()` holds the business rules shared by create and
  update: end ≥ start, end not in the future, range ≤ 92 days.
- **`app/services.py`** — every outbound HTTP call. Keeping them here
  means endpoints stay short and tests can fake this one module.
  `_get_json()` centralises error handling: any network/HTTP problem
  becomes an `UpstreamError`, which `main.py` turns into a 502.
  `fetch_archive_temperatures()` condenses the archive API's daily
  series into avg/min/max and skips null days (the archive lags a few
  days behind real time, so very recent days can be null).
- **`app/exporters.py`** — one function per format (JSON, CSV, XML,
  Markdown, PDF via fpdf2), all fed by the same `record_to_dict()`, plus
  an `EXPORTERS` dict the endpoint looks up by name.
- **`tests/`** — pytest + FastAPI's TestClient. `conftest.py` points
  `DATABASE_URL` at a temporary file *before* importing the app and
  monkeypatches every `services` function, so the suite runs offline in
  under a second. Tests cover CRUD, the three date-validation failures,
  unknown locations, weather endpoints and all export formats.

## Frontend files

- **`src/api.js`** — the only file that knows the backend's URL. Wraps
  `fetch`, converts error responses (including FastAPI's list-shaped
  validation errors) into a single readable `Error.message`, and exports
  one small function per endpoint.
- **`src/App.jsx`** — page layout and the search flow's state
  (`current`, `forecast`, `info`, `loading`, `error`). Loads Islamabad by
  default so the page is never empty, and handles the geolocation flow,
  including the "permission denied" message.
- **`src/components/SearchBar.jsx`** — controlled input + submit, plus
  the "📍 Use my location" button.
- **`src/components/CurrentWeather.jsx`** — presentational: big icon and
  temperature, condition label, feels-like / humidity / wind.
- **`src/components/Forecast.jsx`** — presentational: turns the 5 daily
  entries into a responsive grid of cards.
- **`src/components/LocationInfo.jsx`** — Wikipedia summary (with
  thumbnail), the OSM `<iframe>` map, and the YouTube link.
- **`src/components/RecordsPanel.jsx`** — the CRUD UI. It manages its own
  state: the create form, the record list, inline editing (dates + note)
  and delete, plus the export links. Editing dates re-runs the backend
  update, which refetches archive temperatures so the stored numbers
  always match the stored range.
- **`src/index.css`** — all styling in one plain-CSS file: cards, the
  forecast grid (`auto-fit, minmax`), and a mobile media query.

## Eight questions an interviewer might ask

1. **Why does the frontend call your backend instead of Open-Meteo
   directly?**
   One place for validation, error handling and response shaping; the
   API key situation (none needed here) and CORS stay server-side; and
   the saved-records features need a server anyway.

2. **How does fuzzy location matching work?**
   The geocoding API ranks matches itself; I take the top result and
   always display the resolved name, so a vague query still works but
   the user can see what it matched. No match → a 404 with a clear
   message.

3. **How are the record temperatures computed?**
   On create (and when dates change), the backend calls the archive API
   for daily mean/min/max over the range, then stores the average of the
   daily means, the lowest minimum and the highest maximum. Null days
   (archive lag) are skipped.

4. **Why validate dates on the backend if the form has date pickers?**
   The API is public to anything that calls it, not just my form.
   Pydantic validators enforce the rules (end ≥ start, not future,
   ≤ 92 days) regardless of the client — and the tests prove it.

5. **How do the exports work?**
   One `record_to_dict()` feeds five small exporter functions; the
   endpoint looks the format up in a dict and returns a download
   response with the right media type and filename. Adding a format =
   one function + one dict entry.

6. **How did you test without hitting real APIs?**
   All HTTP lives in `services.py`, and the tests monkeypatch those
   functions with fakes, plus a throwaway SQLite database. The suite
   runs offline in under a second — 24 tests.

7. **What happens when Open-Meteo is down?**
   `_get_json()` raises `UpstreamError`, endpoints return 502 with a
   readable message, and the frontend shows it in a banner. Wikipedia is
   treated as optional — if it fails, the info panel just omits the
   summary (its API also needs a descriptive User-Agent, or it replies
   403 — handled in `fetch_wikipedia_summary`).

8. **How would you scale or improve this?**
   Add caching for geocoding results, move to Postgres with Alembic
   migrations, add user accounts so records are per-user, containerise
   with Docker, and put the API behind a reverse proxy. The structure
   (endpoints / services / models) already separates those concerns.

## Demo video script (1–2 minutes)

1. **(0:00)** "Hi, I'm Arsalan Qasim. This is my weather app for the PM
   Accelerator AI Engineer assessment — React on the front, FastAPI and
   SQLite on the back, all data live from Open-Meteo."
2. **(0:15)** Search "Islamabad" → "Current weather, the 5-day forecast,
   and below, extra info about the place from Wikipedia, a live map, and
   a YouTube link."
3. **(0:35)** Click "Use my location" → "Same thing, but from browser
   GPS coordinates instead of a name."
4. **(0:50)** Search a nonsense place → "Errors are handled gracefully —
   a clear message, no crash."
5. **(1:00)** In Saved Weather Queries, create a record (place + past
   date range) → "The backend fetches historical temperatures from the
   archive API and stores the average, min and max. I can edit the dates
   — watch the numbers update — or delete it."
6. **(1:30)** Click the PDF/CSV export → "All records export in five
   formats." Show the Swagger docs at localhost:8000/docs briefly.
7. **(1:45)** "The backend has 24 automated tests with the external APIs
   mocked, so they run offline. Code and run instructions are in the
   README. Thanks for watching!"
