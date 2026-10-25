import { useState } from "react";

// The search box: a text input for a place name plus a
// "use my location" button that asks the browser for coordinates.
export default function SearchBar({ onSearch, onUseMyLocation, loading }) {
  const [value, setValue] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const query = value.trim();
    if (query) onSearch(query);
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search a city, town, zip code or landmark…"
        aria-label="Location"
      />
      <button type="submit" disabled={loading}>
        Search
      </button>
      <button
        type="button"
        className="secondary"
        onClick={onUseMyLocation}
        disabled={loading}
      >
        📍 Use my location
      </button>
    </form>
  );
}
