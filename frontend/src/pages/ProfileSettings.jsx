import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../AuthContext.jsx";

const TEXT_FIELDS = [
  ["display_name", "Name", "input"],
  ["title", "Title / role", "input", "e.g. Writer/Director"],
  ["tagline", "Tagline", "input", "A short line about your work"],
  ["bio", "Bio", "textarea"],
  ["location", "Based in", "input", "e.g. Singapore"],
  ["hometown", "Hometown", "input"],
  ["education", "Education", "textarea", "e.g. Victorian College of the Arts, 1996–2001"],
  ["headshot_url", "Headshot image URL", "input", "https://…"],
  ["cover_url", "Cover image URL", "input", "https://…"],
];

const LINK_FIELDS = [
  ["website_url", "Website", "https://…"],
  ["instagram", "Instagram", "@handle or URL"],
  ["facebook", "Facebook", "handle or URL"],
  ["twitter", "X / Twitter", "@handle or URL"],
  ["linkedin", "LinkedIn", "handle or URL"],
  ["imdb_url", "IMDb page", "https://www.imdb.com/name/…"],
];

export default function ProfileSettings() {
  const { refresh } = useAuth();
  const [form, setForm] = useState(null);
  const [handle, setHandle] = useState("");
  const [msg, setMsg] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api("/api/me/profile").then((d) => {
      setForm(d);
      setHandle(d.handle || "");
    }).catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  const set = (key) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
  };

  const flash = (text) => { setMsg(text); setError(null); setTimeout(() => setMsg(null), 2500); };

  const saveDetails = async (e) => {
    e.preventDefault();
    try {
      const body = {};
      [...TEXT_FIELDS.map((f) => f[0]), ...LINK_FIELDS.map((f) => f[0]), "public_email"]
        .forEach((k) => { body[k] = form[k] ?? ""; });
      body.public_email = !!form.public_email;
      const updated = await api("/api/me/profile", { method: "PATCH", body });
      setForm((f) => ({ ...f, ...updated }));
      await refresh();
      flash("Profile saved.");
    } catch (err) { setError(err.message); }
  };

  const saveHandle = async (e) => {
    e.preventDefault();
    try {
      await api("/api/me/profile/handle", { method: "PUT", body: { handle } });
      setForm((f) => ({ ...f, handle }));
      flash("Handle saved.");
    } catch (err) { setError(err.message); }
  };

  const togglePublish = async () => {
    try {
      const updated = await api("/api/me/profile/publish", {
        method: "PUT", body: { is_public: !form.is_public },
      });
      setForm((f) => ({ ...f, ...updated }));
      flash(updated.is_public ? "Profile is now public." : "Profile hidden.");
    } catch (err) { setError(err.message); }
  };

  if (error && !form) return <p className="form-error">{error}</p>;
  if (!form) return <p className="center-note">Loading…</p>;

  return (
    <>
      <h1>My public profile</h1>
      <p className="muted">
        A shareable page festivals and audiences can find you at. Your awards
        list is drawn automatically from your real submissions.
      </p>
      {msg && <p className="form-success">{msg}</p>}
      {error && <p className="form-error">{error}</p>}

      <div className="card">
        <h2>Publishing</h2>
        <form onSubmit={saveHandle} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label htmlFor="handle">Public handle</label>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span className="muted">/f/</span>
              <input id="handle" value={handle}
                     onChange={(e) => setHandle(e.target.value)}
                     placeholder="your-name" style={{ flex: 1 }} />
            </div>
          </div>
          <button className="btn btn-secondary" type="submit">Save handle</button>
        </form>
        <div className="btn-row">
          <button
            className={`btn ${form.is_public ? "btn-quiet" : "btn-primary"}`}
            onClick={togglePublish}
            disabled={!form.handle}
          >
            {form.is_public ? "Unpublish" : "Publish profile"}
          </button>
          {form.is_public && form.handle && (
            <Link className="btn btn-secondary" to={`/f/${form.handle}`}>View public page</Link>
          )}
        </div>
        {!form.handle && (
          <p className="muted">Choose a handle before publishing.</p>
        )}
      </div>

      <form className="card" onSubmit={saveDetails}>
        <h2>Details</h2>
        {TEXT_FIELDS.map(([key, label, tag, ph]) => (
          <div key={key}>
            <label htmlFor={key}>{label}</label>
            {tag === "textarea" ? (
              <textarea id={key} value={form[key] ?? ""} onChange={set(key)} placeholder={ph} />
            ) : (
              <input id={key} value={form[key] ?? ""} onChange={set(key)} placeholder={ph} />
            )}
          </div>
        ))}

        <h2 style={{ marginTop: 24 }}>Contact &amp; links</h2>
        {LINK_FIELDS.map(([key, label, ph]) => (
          <div key={key}>
            <label htmlFor={key}>{label}</label>
            <input id={key} value={form[key] ?? ""} onChange={set(key)} placeholder={ph} />
          </div>
        ))}
        <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400, marginTop: 10 }}>
          <input type="checkbox" checked={!!form.public_email} onChange={set("public_email")}
                 style={{ width: "auto", minHeight: "auto" }} />
          Show my account email on the public page
        </label>

        <div className="btn-row">
          <button className="btn btn-primary" type="submit">Save profile</button>
        </div>
      </form>
    </>
  );
}
