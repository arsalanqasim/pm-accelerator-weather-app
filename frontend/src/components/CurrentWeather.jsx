// The big "right now" card: temperature, condition icon and the
// supporting details (feels like, humidity, wind) for one location.
export default function CurrentWeather({ location, current }) {
  if (!current) return null;
  return (
    <section className="card current-weather">
      <h2>
        {location.name}
        {location.country ? `, ${location.country}` : ""}
      </h2>
      <div className="current-main">
        <span className="current-icon">{current.icon}</span>
        <span className="current-temp">{Math.round(current.temperature)}°C</span>
      </div>
      <p className="condition">{current.condition}</p>
      <div className="current-details">
        <div>
          <span>Feels like</span>
          <strong>{Math.round(current.feels_like)}°C</strong>
        </div>
        <div>
          <span>Humidity</span>
          <strong>{current.humidity}%</strong>
        </div>
        <div>
          <span>Wind</span>
          <strong>{current.wind_speed} km/h</strong>
        </div>
      </div>
      <p className="observed">
        Observed {current.observed_at?.replace("T", " ")} ({current.timezone})
      </p>
    </section>
  );
}
