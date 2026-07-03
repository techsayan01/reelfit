import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, money } from "../api.js";
import { useAuth } from "../AuthContext.jsx";

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [films, setFilms] = useState(null);
  const [subsData, setSubsData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api("/api/films").then((d) => setFilms(d.films)).catch((e) => setError(e.message));
    api("/api/submissions").then(setSubsData).catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  const scoreFilm = async (film) => {
    if (!window.confirm(
      `Run a fit check for “${film.title}”? This uses 1 scoring credit and scores against every listed festival.`
    )) return;
    try {
      await api(`/api/films/${film.id}/score`, { method: "POST" });
      await refresh();
      navigate(`/films/${film.id}/scores`);
    } catch (err) {
      if (err.status === 402) navigate("/credits?needed=1");
      else setError(err.message);
    }
  };

  const revokeRelay = async (sub) => {
    if (!window.confirm(
      `Stop ${sub.festival_name} from contacting you? They will lose access to your relay address immediately.`
    )) return;
    await api(`/api/submissions/${sub.id}/revoke-relay`, { method: "POST" });
    load();
  };

  const subs = subsData?.submissions ?? [];
  const notes = subsData?.notifications ?? [];
  const totalFees = subs.reduce((sum, s) => sum + s.fee_paid_cents, 0);

  return (
    <>
      <h1>My films</h1>
      {error && <p className="form-error">{error}</p>}

      <div className="two-col">
        <div>
          <div className="card">
            <h2>Film library</h2>
            <p className="muted">Upload once, submit to many.</p>
            {films === null && <p className="center-note">Loading…</p>}
            {films && films.length === 0 && <p>No films yet — add your first one.</p>}
            <div className="list-divided">
              {films?.map((film) => (
                <div key={film.id}>
                  <h3 style={{ margin: "0 0 4px" }}>{film.title}</h3>
                  <p className="muted" style={{ margin: "0 0 10px" }}>
                    {film.genre} · {film.runtime_minutes} min · {film.year}
                  </p>
                  <div className="btn-row" style={{ marginTop: 0 }}>
                    <Link className="btn btn-secondary" to={`/films/${film.id}/scores`}>
                      See where it fits
                    </Link>
                    <button className="btn btn-quiet" onClick={() => scoreFilm(film)}>
                      Re-score (1 credit)
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="btn-row">
              <Link className="btn btn-primary" to="/films/new">Add a film</Link>
            </div>
          </div>

          <div className="card">
            <h2>Submissions</h2>
            {subs.length === 0 && (
              <p>No submissions yet. Score a film to see which festivals fit best.</p>
            )}
            {subs.length > 0 && (
              <>
                <table className="stack">
                  <thead>
                    <tr><th>Film</th><th>Festival</th><th>Status</th><th>Fee</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    {subs.map((s) => (
                      <tr key={s.id}>
                        <td data-label="Film">{s.film_title}</td>
                        <td data-label="Festival">{s.festival_name}</td>
                        <td data-label="Status">
                          <span className={`tag ${s.status === "selected" ? "tag-selected" : "tag-status"}`}>
                            {s.status.replace("_", " ")}
                          </span>
                        </td>
                        <td data-label="Fee">{money(s.fee_paid_cents)}</td>
                        <td data-label="Actions">
                          {s.status === "selected" && (
                            <a href={`/api/submissions/${s.id}/certificate.svg`}>Laurel</a>
                          )}{" "}
                          {!s.reviewed && (
                            <Link to={`/reviews/new?submission=${s.id}`}>Review festival</Link>
                          )}{" "}
                          {s.relay_revoked ? (
                            <span className="muted">contact revoked</span>
                          ) : (
                            <button className="btn btn-quiet" onClick={() => revokeRelay(s)}>
                              Revoke contact
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="muted" style={{ marginTop: 12 }}>
                  Total in submission fees: {money(totalFees)}
                </p>
              </>
            )}
          </div>
        </div>

        <div>
          <div className="card">
            <h2>Notifications</h2>
            {notes.length === 0 && <p className="muted">Nothing yet.</p>}
            <div className="list-divided">
              {notes.map((n) => (
                <p key={n.id}>
                  {n.read ? n.subject : <strong>{n.subject}</strong>}
                  <br />
                  <span className="muted">{new Date(n.created_at).toLocaleDateString()}</span>
                </p>
              ))}
            </div>
          </div>
          <div className="card">
            <h2>Scoring credits</h2>
            <p>
              You have <strong>{user.credit_balance}</strong> credit
              {user.credit_balance !== 1 ? "s" : ""}. One credit scores a film
              against <em>every</em> listed festival.
            </p>
            <Link className="btn btn-secondary" to="/credits">Get more credits</Link>
          </div>
        </div>
      </div>
    </>
  );
}
