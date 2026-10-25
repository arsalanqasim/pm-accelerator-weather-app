// Small client for the FastAPI backend.
//
// Every function throws an Error with a human-friendly message when
// something goes wrong (network down, unknown city, invalid input),
// so components can simply try/catch and show `error.message`.

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error(
      "Could not reach the weather server. Is the backend running on port 8000?"
    );
  }

  if (!response.ok) {
    let message = `Something went wrong (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation errors arrive as a list of objects.
        message = body.detail.map((e) => e.msg).join(" ");
      }
    } catch {
      // Keep the generic message if the body was not JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) return null; // e.g. successful DELETE
  return response.json();
}

// Build "?q=..." or "?lat=...&lon=..." from a params object.
function weatherQuery({ q, lat, lon }) {
  if (q) return `q=${encodeURIComponent(q)}`;
  return `lat=${lat}&lon=${lon}`;
}

export function getCurrentWeather(params) {
  return request(`/api/weather/current?${weatherQuery(params)}`);
}

export function getForecast(params) {
  return request(`/api/weather/forecast?${weatherQuery(params)}`);
}

export function getLocationInfo(q) {
  return request(`/api/location/info?q=${encodeURIComponent(q)}`);
}

export function listRecords() {
  return request("/api/records");
}

export function createRecord(record) {
  return request("/api/records", {
    method: "POST",
    body: JSON.stringify(record),
  });
}

export function updateRecord(id, changes) {
  return request(`/api/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(changes),
  });
}

export function deleteRecord(id) {
  return request(`/api/records/${id}`, { method: "DELETE" });
}

// Exports are plain downloads, so the browser can navigate straight to
// the URL instead of going through fetch.
export function exportUrl(format) {
  return `${API_BASE}/api/records/export?format=${format}`;
}
