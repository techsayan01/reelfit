import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const GENRES = [
  "drama", "comedy", "documentary", "horror",
  "thriller", "animation", "experimental", "music video",
];

export default function FilmNew() {
  const navigate = useNavigate();
  const [kind, setKind] = useState("film");
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
          kind,
          genre: form.get("genre"),
          runtime_minutes:
            kind === "film" ? Number(form.get("runtime_minutes")) : null,
          year: Number(form.get("year")),
          country: form.get("country") || "",
          logline: form.get("logline") || "",
          synopsis: form.get("synopsis") || "",
          language: form.get("language") || "",
          credits: form.get("credits") || "",
          screener_url: form.get("screener_url") || "",
          trailer_url: form.get("trailer_url") || "",
          first_time_filmmaker: form.get("first_time_filmmaker") === "on",
          student_project: form.get("student_project") === "on",
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
      <h1>Add a project</h1>
      <p className="muted">Add it once — you can then score it and submit it anywhere.</p>
      {error && <p className="form-error">{error}</p>}
      <div className="card form-narrow">
        <form onSubmit={onSubmit}>
          <label htmlFor="kind">Project type</label>
          <select id="kind" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="film">Finished film</option>
            <option value="screenplay">Screenplay / script</option>
          </select>

          <label htmlFor="title">Title</label>
          <input id="title" name="title" required />

          <label htmlFor="genre">Genre</label>
          <select id="genre" name="genre" required>
            {GENRES.map((g) => (
              <option key={g} value={g}>{g[0].toUpperCase() + g.slice(1)}</option>
            ))}
          </select>

          {kind === "film" && (
            <>
              <label htmlFor="runtime_minutes">Runtime (minutes)</label>
              <input id="runtime_minutes" name="runtime_minutes" type="number" min={1} max={600} required />
            </>
          )}

          <label htmlFor="year">Year completed</label>
          <input id="year" name="year" type="number" min={1990} max={2030} required />

          <label htmlFor="country">Country of production</label>
          <input id="country" name="country" />

          <label htmlFor="logline">Logline (one sentence about your film)</label>
          <textarea id="logline" name="logline" style={{ minHeight: 60 }} />

          <label htmlFor="synopsis">Synopsis</label>
          <textarea id="synopsis" name="synopsis" placeholder="A short paragraph festivals will read when judging." />

          <label htmlFor="language">Language</label>
          <input id="language" name="language" placeholder="e.g. Bengali (English subtitles)" />

          {kind === "film" && (
            <>
              <label htmlFor="screener_url">Screener link (YouTube/Vimeo)</label>
              <input id="screener_url" name="screener_url" type="url" placeholder="https://…" />
              <p className="muted">Festivals watch your film through this link — use an unlisted upload.</p>

              <label htmlFor="trailer_url">Trailer link (optional)</label>
              <input id="trailer_url" name="trailer_url" type="url" placeholder="https://…" />
            </>
          )}

          <label htmlFor="credits">Credits (one per line: Name — Role)</label>
          <textarea id="credits" name="credits" placeholder={"Priya Sharma — Director\nArun Bose — Cinematographer"} />

          <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400 }}>
            <input name="first_time_filmmaker" type="checkbox" style={{ width: "auto", minHeight: "auto" }} />
            This is my first {kind === "film" ? "film" : "script"}
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400 }}>
            <input name="student_project" type="checkbox" style={{ width: "auto", minHeight: "auto" }} />
            Student project
          </label>

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
