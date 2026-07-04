import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, money } from "../api.js";

const label = (s) => s.replaceAll("_", " ");

/** Convert a YouTube/Vimeo watch URL into an embeddable player URL. */
function embedUrl(url) {
  if (!url) return null;
  const yt = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
  if (yt) return `https://www.youtube.com/embed/${yt[1]}`;
  const vimeo = url.match(/vimeo\.com\/(\d+)/);
  if (vimeo) return `https://player.vimeo.com/video/${vimeo[1]}`;
  return null;
}

function SpecRow({ name, value }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <tr>
      <td data-label="Spec"><strong>{name}</strong></td>
      <td data-label="Value">{value}</td>
    </tr>
  );
}

function JudgesCard({ data, submissionId, onChanged, onError }) {
  const { judges = [], staff = [], can_update } = data;
  const assignedIds = new Set(judges.map((j) => j.user_id));
  const assignable = staff.filter(
    (s) => !assignedIds.has(s.user_id) && s.role !== "viewer"
  );

  const assign = async (e) => {
    const user_id = Number(e.target.value);
    if (!user_id) return;
    try {
      await api(`/api/festival/submissions/${submissionId}/assign`, {
        method: "POST",
        body: { user_id },
      });
      onChanged();
    } catch (err) {
      onError(err.message);
    }
  };

  const unassign = async (user_id) => {
    try {
      await api(`/api/festival/submissions/${submissionId}/unassign`, {
        method: "POST",
        body: { user_id },
      });
      onChanged();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Judges ({judges.length})</h2>
      {judges.length === 0 && <p className="muted">No judges assigned yet.</p>}
      <div className="list-divided">
        {judges.map((j) => (
          <p key={j.user_id} style={{ margin: 0, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <span>
              <strong>{j.name}</strong>{" "}
              <span className={`tag ${j.status === "done" ? "tag-validated" : "tag-status"}`}>
                {j.status === "done" ? "scored" : label(j.status)}
              </span>
            </span>
            {can_update && (
              <button className="btn btn-quiet" onClick={() => unassign(j.user_id)}>
                Remove
              </button>
            )}
          </p>
        ))}
      </div>
      {can_update && assignable.length > 0 && (
        <>
          <label htmlFor="assign-judge">Assign a judge</label>
          <select id="assign-judge" value="" onChange={assign}>
            <option value="">Choose a staff member…</option>
            {assignable.map((s) => (
              <option key={s.user_id} value={s.user_id}>
                {s.display_name} ({s.role})
              </option>
            ))}
          </select>
        </>
      )}
    </div>
  );
}

function RatingCard({ data, submissionId, onChanged, onError }) {
  const {
    rubric = [],
    my_scores = {},
    rating = { average: null, judges: 0 },
    can_rate,
  } = data;
  const [open, setOpen] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const scores = rubric
      .map((c) => ({ criterion_id: c.id, score: Number(form.get(`c${c.id}`)) }))
      .filter((s) => s.score >= 1);
    try {
      await api(`/api/festival/submissions/${submissionId}/rate`, {
        method: "POST",
        body: { scores },
      });
      setOpen(false);
      onChanged();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Rating</h2>
      {rating.average !== null ? (
        <p>
          <span className="display" style={{ fontSize: "1.8rem" }}>{rating.average}</span>
          <span className="muted"> / 10 · {rating.judges} judge{rating.judges !== 1 ? "s" : ""}</span>
        </p>
      ) : (
        <p className="muted">This entry has not been rated yet.</p>
      )}
      {can_rate && rubric.length === 0 && (
        <p className="muted">Set up rubric criteria on the dashboard to rate entries.</p>
      )}
      {can_rate && rubric.length > 0 && !open && (
        <button className="btn btn-secondary" onClick={() => setOpen(true)}>
          {Object.keys(my_scores).length ? "Edit my scores" : "Rate this entry"}
        </button>
      )}
      {can_rate && open && (
        <form onSubmit={submit}>
          {rubric.map((c) => (
            <div key={c.id}>
              <label htmlFor={`c${c.id}`}>
                {c.name} <span className="muted">(weight {c.weight})</span>
              </label>
              <select
                id={`c${c.id}`}
                name={`c${c.id}`}
                defaultValue={my_scores[String(c.id)] ?? ""}
                required
              >
                <option value="" disabled>Score 1–10</option>
                {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          ))}
          <div className="btn-row">
            <button className="btn btn-primary" type="submit">Save scores</button>
            <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default function FestivalSubmissionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("overview");

  const load = useCallback(() => {
    api(`/api/festival/submissions/${id}`).then(setData).catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    setTab("overview");
    load();
  }, [load]);

  const updateStatus = async (status) => {
    try {
      await api(`/api/festival/submissions/${id}/status`, { method: "POST", body: { status } });
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const addNote = async (e) => {
    e.preventDefault();
    const form = e.target;
    const text = new FormData(form).get("text");
    try {
      await api(`/api/festival/submissions/${id}/notes`, { method: "POST", body: { text } });
      form.reset();
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  if (error && !data) return <p className="form-error">{error}</p>;
  if (!data) return <p className="center-note">Loading…</p>;

  const { submission, film, filmmaker, status_log, notes, statuses, can_update, prev_id, next_id } = data;
  const screener = embedUrl(film.screener_url);
  const trailer = embedUrl(film.trailer_url);

  return (
    <>
      <div className="btn-row" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <Link className="btn btn-quiet" to="/festival/dashboard">← All submissions</Link>
        <span>
          {prev_id && (
            <button className="btn btn-quiet" onClick={() => navigate(`/festival/submissions/${prev_id}`)}>
              ‹ Previous
            </button>
          )}
          {next_id && (
            <button className="btn btn-quiet" onClick={() => navigate(`/festival/submissions/${next_id}`)}>
              Next ›
            </button>
          )}
        </span>
      </div>

      <h1>
        {film.title}{" "}
        <span className="tracking-number">{submission.tracking_number}</span>
      </h1>
      <p className="muted">
        {film.kind === "screenplay" ? "screenplay · " : ""}
        {film.genre}
        {film.runtime_minutes != null && <> · {film.runtime_minutes} min</>}
        {film.country && <> · {film.country}</>} · {film.year}
      </p>
      {error && <p className="form-error">{error}</p>}

      {screener ? (
        <div className="screener-frame">
          <iframe
            src={screener}
            title={`Screener: ${film.title}`}
            allow="fullscreen"
            allowFullScreen
          />
        </div>
      ) : film.screener_url ? (
        <div className="card">
          <a href={film.screener_url} target="_blank" rel="noreferrer">
            Open screener ↗
          </a>
        </div>
      ) : (
        <div className="card"><p className="muted">No screener provided.</p></div>
      )}

      <div className="two-col">
        <div>
          <div className="tab-row" role="tablist">
            {["overview", "credits", "specifications", "cover letter"].map((t) => (
              <button
                key={t}
                role="tab"
                aria-selected={tab === t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}
              >
                {t[0].toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {tab === "overview" && (
            <div className="card">
              {film.logline && <p><em>{film.logline}</em></p>}
              <p>{film.synopsis || "No synopsis provided."}</p>
              <h3>About the filmmaker — {filmmaker.display_name}</h3>
              <p>{filmmaker.bio || "No bio provided."}</p>
              {trailer && (
                <div className="screener-frame">
                  <iframe src={trailer} title="Trailer" allow="fullscreen" allowFullScreen />
                </div>
              )}
            </div>
          )}

          {tab === "credits" && (
            <div className="card">
              {film.credits ? (
                <table className="stack">
                  <tbody>
                    {film.credits.split("\n").map((line, i) => {
                      const [name, role] = line.split("—").map((s) => s.trim());
                      return (
                        <tr key={i}>
                          <td data-label="Name"><strong>{name}</strong></td>
                          <td data-label="Role">{role || ""}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <p className="muted">No credits provided.</p>
              )}
            </div>
          )}

          {tab === "specifications" && (
            <div className="card">
              <table className="stack">
                <tbody>
                  <SpecRow name="Project type" value={label(film.kind)} />
                  <SpecRow
                    name="Runtime"
                    value={film.runtime_minutes != null ? `${film.runtime_minutes} minutes` : null}
                  />
                  <SpecRow name="Completion year" value={film.year} />
                  <SpecRow name="Country of origin" value={film.country} />
                  <SpecRow name="Language" value={film.language} />
                  <SpecRow
                    name="First-time filmmaker"
                    value={film.first_time_filmmaker ? "Yes" : "No"}
                  />
                  <SpecRow
                    name="Student project"
                    value={film.student_project ? "Yes" : "No"}
                  />
                </tbody>
              </table>
            </div>
          )}

          {tab === "cover letter" && (
            <div className="card">
              {submission.cover_letter
                ? submission.cover_letter.split("\n").map((line, i) => <p key={i}>{line}</p>)
                : <p className="muted">No cover letter included.</p>}
            </div>
          )}

          <div className="card">
            <h2>Internal notes</h2>
            <p className="muted">Jury-only — never visible to the filmmaker.</p>
            <form onSubmit={addNote}>
              <textarea name="text" placeholder="Add a note about this entry…" required />
              <div className="btn-row">
                <button className="btn btn-secondary" type="submit">Add note</button>
              </div>
            </form>
            <div className="list-divided" style={{ marginTop: 12 }}>
              {notes.map((n) => (
                <div key={n.id}>
                  <p style={{ margin: 0 }}>{n.text}</p>
                  <p className="muted" style={{ margin: 0, fontSize: "0.85rem" }}>
                    {n.author} · {new Date(n.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          <div className="card">
            <h2>Judging</h2>
            <label htmlFor="status">Judging status</label>
            {can_update ? (
              <select
                id="status"
                value={submission.status}
                onChange={(e) => updateStatus(e.target.value)}
              >
                {statuses.map((st) => (
                  <option key={st} value={st}>{label(st)}</option>
                ))}
              </select>
            ) : (
              <p><span className="tag tag-status">{label(submission.status)}</span></p>
            )}
            {submission.notified && (
              <p className="muted" style={{ marginTop: 8 }}>✓ filmmaker notified of current status</p>
            )}
          </div>

          <RatingCard data={data} submissionId={id} onChanged={load} onError={setError} />
          <JudgesCard data={data} submissionId={id} onChanged={load} onError={setError} />

          <div className="card">
            <h2>Submission</h2>
            <table className="stack">
              <tbody>
                <SpecRow name="Category" value={submission.category} />
                <SpecRow name="Fee paid" value={money(submission.fee_paid_cents)} />
                <SpecRow
                  name="Code used"
                  value={submission.discount_code || null}
                />
                <SpecRow
                  name="Submitted"
                  value={new Date(submission.created_at).toLocaleDateString()}
                />
                <SpecRow name="Contact" value={submission.contact} />
              </tbody>
            </table>
            <p className="muted" style={{ fontSize: "0.9rem" }}>
              Contact goes through the filmmaker's Reelfit relay — direct
              details are never shared.
            </p>
          </div>

          <div className="card">
            <h2>Log</h2>
            {status_log.length === 0 && <p className="muted">No status changes yet.</p>}
            <div className="list-divided">
              {status_log.map((c, i) => (
                <p key={i} style={{ margin: 0 }}>
                  <strong>{c.actor}</strong> moved this from{" "}
                  <em>{label(c.from_status)}</em> to <em>{label(c.to_status)}</em>
                  <br />
                  <span className="muted" style={{ fontSize: "0.85rem" }}>
                    {new Date(c.created_at).toLocaleString()}
                  </span>
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
