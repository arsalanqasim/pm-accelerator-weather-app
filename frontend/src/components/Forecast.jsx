// The 5-day forecast as a responsive grid of day cards.
export default function Forecast({ days }) {
  if (!days || days.length === 0) return null;

  // Turn "2026-10-25" into a short weekday label like "Sat 25 Oct".
  function formatDay(isoDate) {
    const date = new Date(`${isoDate}T12:00:00`);
    return date.toLocaleDateString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  }

  return (
    <section className="card">
      <h3>5-Day Forecast</h3>
      <div className="forecast-grid">
        {days.map((day) => (
          <div className="forecast-day" key={day.date}>
            <div className="forecast-date">{formatDay(day.date)}</div>
            <div className="forecast-icon">{day.icon}</div>
            <div className="forecast-condition">{day.condition}</div>
            <div className="forecast-temps">
              <strong>{Math.round(day.temp_max)}°</strong>
              <span> / {Math.round(day.temp_min)}°</span>
            </div>
            {day.precipitation_probability != null && (
              <div className="forecast-rain">
                💧 {day.precipitation_probability}%
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
