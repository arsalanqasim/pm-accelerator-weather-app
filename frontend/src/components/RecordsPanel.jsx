import { useCallback, useEffect, useState } from "react";
import {
  createRecord,
  deleteRecord,
  exportUrl,
  listRecords,
  updateRecord,
} from "../api.js";

// Saved Weather Queries: the CRUD part of the app.
//
// A record stores the temperature summary of one place over a past
// date range (fetched by the backend from the Open-Meteo archive API).
// This panel lets the user create records, edit their note/date range,
// delete them, and export the whole collection in several formats.
export default function RecordsPanel() {
  const [records, setRecords] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    location: "",
    start_date: "",
    end_date: "",
    note: "",
  });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ start_date: "", end_date: "", note: "" });

  const refresh = useCallback(async () => {
    try {
      setRecords(await listRecords());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    try {
      await createRecord({
        location: form.location,
        start_date: form.start_date,
        end_date: form.end_date,
        note: form.note || null,
      });
      setForm({ location: "", start_date: "", end_date: "", note: "" });
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEditing(record) {
    setEditingId(record.id);
    setEditForm({
      start_date: record.start_date,
      end_date: record.end_date,
      note: record.note || "",
    });
  }

  async function handleSaveEdit(id) {
    setError("");
    try {
      await updateRecord(id, {
        start_date: editForm.start_date,
        end_date: editForm.end_date,
        note: editForm.note || null,
      });
      setEditingId(null);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    setError("");
    try {
      await deleteRecord(id);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="card records">
      <h3>Saved Weather Queries</h3>
      <p className="hint">
        Save the historical temperature of a place over a date range
        (the backend fetches it from the Open-Meteo archive).
      </p>

      <form className="record-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="Location (e.g. Islamabad)"
          value={form.location}
          onChange={(e) => setForm({ ...form, location: e.target.value })}
          required
        />
        <label>
          From
          <input
            type="date"
            value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            required
          />
        </label>
        <label>
          To
          <input
            type="date"
            value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            required
          />
        </label>
        <input
          type="text"
          placeholder="Note (optional)"
          value={form.note}
          onChange={(e) => setForm({ ...form, note: e.target.value })}
        />
        <button type="submit">Save query</button>
      </form>

      {error && <p className="error">{error}</p>}

      <div className="export-row">
        <span>Export all records:</span>
        {["json", "csv", "xml", "markdown", "pdf"].map((format) => (
          <a key={format} href={exportUrl(format)} download>
            {format.toUpperCase()}
          </a>
        ))}
      </div>

      {records.length === 0 ? (
        <p className="hint">No saved queries yet — add your first one above.</p>
      ) : (
        <ul className="record-list">
          {records.map((record) => (
            <li key={record.id} className="record-item">
              <div className="record-main">
                <strong>{record.resolved_name}</strong>
                <span className="record-dates">
                  {record.start_date} → {record.end_date}
                </span>
                <span className="record-temps">
                  Avg {record.avg_temp}°C · Min {record.min_temp}°C · Max{" "}
                  {record.max_temp}°C
                </span>
                {record.note && <span className="record-note">“{record.note}”</span>}
              </div>

              {editingId === record.id ? (
                <div className="record-edit">
                  <label>
                    From
                    <input
                      type="date"
                      value={editForm.start_date}
                      onChange={(e) =>
                        setEditForm({ ...editForm, start_date: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    To
                    <input
                      type="date"
                      value={editForm.end_date}
                      onChange={(e) =>
                        setEditForm({ ...editForm, end_date: e.target.value })
                      }
                    />
                  </label>
                  <input
                    type="text"
                    placeholder="Note"
                    value={editForm.note}
                    onChange={(e) =>
                      setEditForm({ ...editForm, note: e.target.value })
                    }
                  />
                  <button onClick={() => handleSaveEdit(record.id)}>Save</button>
                  <button className="secondary" onClick={() => setEditingId(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="record-actions">
                  <button className="secondary" onClick={() => startEditing(record)}>
                    Edit
                  </button>
                  <button className="danger" onClick={() => handleDelete(record.id)}>
                    Delete
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
