import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../AuthContext.jsx";

export default function Register() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [kind, setKind] = useState("filmmaker");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.target);
    try {
      const data = await api("/api/auth/register", {
        method: "POST",
        body: {
          email: form.get("email"),
          password: form.get("password"),
          display_name: form.get("display_name"),
          kind,
          festival_name: form.get("festival_name") || "",
        },
      });
      setUser(data.user);
      navigate(kind === "organizer" ? "/festival/dashboard" : "/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1>Create your account</h1>
      {error && <p className="form-error">{error}</p>}
      <div className="card form-narrow">
        <form onSubmit={onSubmit}>
          <label htmlFor="kind">I am a…</label>
          <select id="kind" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="filmmaker">Filmmaker</option>
            <option value="organizer">Festival organizer</option>
          </select>

          {kind === "organizer" && (
            <>
              <label htmlFor="festival_name">Festival name</label>
              <input id="festival_name" name="festival_name" placeholder="e.g. Hillside Film Festival" />
              <p className="muted">You can add editions, categories and fees after signing up.</p>
            </>
          )}

          <label htmlFor="display_name">Your name</label>
          <input id="display_name" name="display_name" required />

          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" required autoComplete="email" />

          <label htmlFor="password">Password (8+ characters)</label>
          <input id="password" name="password" type="password" minLength={8} required autoComplete="new-password" />

          <div className="btn-row">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Creating…" : "Create account"}
            </button>
          </div>
          <p className="muted">Filmmakers start with one free fit-score check.</p>
        </form>
      </div>
    </>
  );
}
