import { useCallback, useEffect, useState } from "react";
import { getCurrentWeather, getForecast, getLocationInfo } from "./api.js";
import CurrentWeather from "./components/CurrentWeather.jsx";
import Forecast from "./components/Forecast.jsx";
import LocationInfo from "./components/LocationInfo.jsx";
import RecordsPanel from "./components/RecordsPanel.jsx";
import SearchBar from "./components/SearchBar.jsx";

// Root component. It owns the "weather" state (current conditions,
// forecast, location info) and the loading/error flags shared by the
// search flow. Saved records live in their own panel component.
export default function App() {
  const [location, setLocation] = useState(null);
  const [current, setCurrent] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load weather for either { q } (a place name) or { lat, lon }.
  // When a place name was searched, extra location info is loaded too.
  const loadWeather = useCallback(async (params) => {
    setLoading(true);
    setError("");
    try {
      const [currentData, forecastData] = await Promise.all([
        getCurrentWeather(params),
        getForecast(params),
      ]);
      setLocation(currentData.location);
      setCurrent(currentData.current);
      setForecast(forecastData.forecast);
      setInfo(params.q ? await getLocationInfo(params.q) : null);
    } catch (err) {
      // Friendly error banner instead of a blank or crashed page.
      setError(err.message);
      setCurrent(null);
      setForecast([]);
      setInfo(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Show a default city on first load so the page is never empty.
  useEffect(() => {
    loadWeather({ q: "Islamabad" });
  }, [loadWeather]);

  function handleUseMyLocation() {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by this browser.");
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) =>
        loadWeather({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        }),
      () =>
        setError(
          "Could not get your location. Please allow location access or search by name instead."
        )
    );
  }

  return (
    <div className="app">
      <header>
        <h1>🌦️ Weather App</h1>
        <p className="byline">by Arsalan Qasim</p>
        <p className="tagline">
          Live weather, 5-day forecasts and saved historical weather
          queries — powered by the Open-Meteo APIs.
        </p>
      </header>

      <main>
        <SearchBar
          onSearch={(q) => loadWeather({ q })}
          onUseMyLocation={handleUseMyLocation}
          loading={loading}
        />

        {loading && <p className="loading">Loading weather…</p>}
        {error && <p className="error">{error}</p>}

        <CurrentWeather location={location ?? {}} current={current} />
        <Forecast days={forecast} />
        <LocationInfo info={info} />
        <RecordsPanel />
      </main>

      <footer>
        <h4>About PM Accelerator</h4>
        <p>
          PM Accelerator (Product Manager Accelerator) is a career
          accelerator program that helps aspiring product managers and
          builders gain real-world experience. Participants work in
          teams with mentorship to design, build and ship real AI
          products, and this weather app was built as the technical
          assessment for its AI Engineer Intern selection.
        </p>
        <p className="footer-note">
          Weather data: Open-Meteo (free, no API key). Place summaries:
          Wikipedia. Maps: OpenStreetMap. Built with React, FastAPI and
          SQLite.
        </p>
      </footer>
    </div>
  );
}
