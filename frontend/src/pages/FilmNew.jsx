import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const GENRES = [
  "drama", "comedy", "documentary", "horror",
  "thriller", "animation", "experimental", "music video",
];

export default function FilmNew() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.target);
    try {
      await api("/api/films", {
        method: "POST",
        body: {
          title: form.get("title"),
          genre: form.get("genre"),
          runtime_minutes: Number(form.get("runtime_minutes")),
          year: Number(form.get("year")),
          country: form.get("country") || "",
          logline: form.get("logline") || "",
        },
      });
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <>
      <h1>Add a film</h1>
      <p className="muted">Add it once — you can then score it and submit it anywhere.</p>
      {error && <p className="form-error">{error}</p>}
      <div className="card form-narrow">
        <form onSubmit={onSubmit}>
          <label htmlFor="title">Title</label>
          <input id="title" name="title" required />

          <label htmlFor="genre">Genre</label>
          <select id="genre" name="genre" required>
            {GENRES.map((g) => (
              <option key={g} value={g}>{g[0].toUpperCase() + g.slice(1)}</option>
            ))}
          </select>

          <label htmlFor="runtime_minutes">Runtime (minutes)</label>
          <input id="runtime_minutes" name="runtime_minutes" type="number" min={1} max={600} required />

          <label htmlFor="year">Year completed</label>
          <input id="year" name="year" type="number" min={1990} max={2030} required />

          <label htmlFor="country">Country of production</label>
          <input id="country" name="country" />

          <label htmlFor="logline">Logline (one sentence about your film)</label>
          <textarea id="logline" name="logline" />

          <div className="btn-row">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Adding…" : "Add film"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
