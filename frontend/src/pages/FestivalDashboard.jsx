import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, money } from "../api.js";
import { useAuth } from "../AuthContext.jsx";
import CalibrationTag from "../components/CalibrationTag.jsx";

const Stars = ({ rating }) => (
  <span className="stars">{"★".repeat(rating)}{"☆".repeat(5 - rating)}</span>
);

const label = (s) => s.replaceAll("_", " ");

const PROFILE_FIELDS = [
  ["description", "Description", "textarea"],
  ["rules", "Submission rules", "textarea"],
  ["awards_and_prizes", "Awards & prizes", "textarea"],
  ["logo_url", "Logo URL", "input"],
  ["cover_url", "Cover image URL", "input"],
  ["contact_email", "Contact email", "input"],
  ["phone", "Phone", "input"],
  ["website", "Website", "input"],
  ["twitter", "X / Twitter", "input"],
  ["instagram", "Instagram", "input"],
  ["venue_name", "Venue name", "input"],
  ["venue_address", "Venue address", "input"],
  ["founded_year", "Founded year", "number"],
  ["tracking_prefix", "Tracking number prefix (e.g. HIL)", "input"],
];

function ProfileEditor({ festival, onSaved, onError }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    const form = new FormData(e.target);
    const body = {};
    for (const [field, , type] of PROFILE_FIELDS) {
      const value = form.get(field);
      if (value !== null) {
        body[field] = type === "number" ? (value ? Number(value) : null) : value;
      }
    }
    body.is_public = form.get("is_public") === "on";
    try {
      await api("/api/festival/profile", { method: "PATCH", body });
      setOpen(false);
      onSaved();
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <div className="card">
        <h2>Public profile</h2>
        <p className="muted">
          Logo, cover image, rules, awards, contact links and venue —
          everything filmmakers see on your public page.
        </p>
        <button className="btn btn-secondary" onClick={() => setOpen(true)}>
          Edit public profile
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Edit public profile</h2>
      <form onSubmit={save}>
        {PROFILE_FIELDS.map(([field, fieldLabel, type]) => (
          <div key={field}>
            <label htmlFor={field}>{fieldLabel}</label>
            {type === "textarea" ? (
              <textarea id={field} name={field} defaultValue={festival[field] ?? ""} />
            ) : (
              <input
                id={field}
                name={field}
                type={type === "number" ? "number" : "text"}
                defaultValue={festival[field] ?? ""}
              />
            )}
          </div>
        ))}
        <label htmlFor="is_public" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <input
            id="is_public"
            name="is_public"
            type="checkbox"
            defaultChecked={festival.is_public}
            style={{ width: "auto", minHeight: "auto" }}
          />
          Publicly listed (uncheck to hide while you finish setting up)
        </label>
        <div className="btn-row">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save profile"}
          </button>
          <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

function SubmissionsManager({ data, onStatusChange }) {
  const { submissions, statuses, can_update } = data;
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const categories = useMemo(
    () => [...new Set(submissions.map((s) => s.category).filter(Boolean))],
    [submissions]
  );

  const filtered = submissions.filter((s) => {
    if (statusFilter !== "all" && s.status !== statusFilter) return false;
    if (categoryFilter !== "all" && s.category !== categoryFilter) return false;
    if (query) {
      const q = query.toLowerCase();
      if (
        !s.film_title.toLowerCase().includes(q) &&
        !s.tracking_number.toLowerCase().includes(q)
      )
        return false;
    }
    return true;
  });

  return (
    <div className="card">
      <h2>Submissions ({submissions.length})</h2>
      {submissions.length === 0 ? (
        <p>No submissions yet.</p>
      ) : (
        <>
          <div className="filter-row">
            <input
              aria-label="Search by title or tracking number"
              placeholder="Search title or tracking number…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <select
              aria-label="Filter by judging status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All statuses</option>
              {statuses.map((st) => (
                <option key={st} value={st}>{label(st)}</option>
              ))}
            </select>
            <select
              aria-label="Filter by category"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="all">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <p className="muted" style={{ fontSize: "0.9rem" }}>
            {filtered.length} submission{filtered.length !== 1 ? "s" : ""} match your criteria
          </p>
          <table className="stack">
            <thead>
              <tr>
                <th>Project</th><th>Category</th><th>Fee</th><th>Date</th><th>Judging status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td data-label="Project">
                    <Link to={`/festival/submissions/${s.id}`}>
                      <strong>{s.film_title}</strong>
                    </Link>
                    <br />
                    <span className="muted">
                      {s.film_kind === "screenplay" ? "screenplay · " : ""}
                      {s.film_genre}
                      {s.film_runtime_minutes != null && <> · {s.film_runtime_minutes} min</>}
                      {s.film_country && <> · {s.film_country}</>}
                    </span>
                    <br />
                    <span className="tracking-number">{s.tracking_number}</span>
                    {" "}
                    <span className="muted" style={{ fontSize: "0.85rem" }}>{s.contact}</span>
                  </td>
                  <td data-label="Category">{s.category}</td>
                  <td data-label="Fee">{money(s.fee_paid_cents)}</td>
                  <td data-label="Date">{new Date(s.created_at).toLocaleDateString()}</td>
                  <td data-label="Judging status">
                    {can_update ? (
                      <select
                        aria-label={`Judging status for ${s.film_title}`}
                        value={s.status}
                        onChange={(e) => onStatusChange(s, e.target.value)}
                      >
                        {statuses.map((st) => (
                          <option key={st} value={st}>{label(st)}</option>
                        ))}
                      </select>
                    ) : (
                      <span className="tag tag-status">{label(s.status)}</span>
                    )}
                    {s.notified && (
                      <div className="muted" style={{ fontSize: "0.85rem" }}>✓ filmmaker notified</div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

export default function FestivalDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api("/api/festival/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  const updateStatus = async (sub, status) => {
    try {
      await api(`/api/festival/submissions/${sub.id}/status`, {
        method: "POST",
        body: { status },
      });
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const replyToReview = async (reviewId, e) => {
    e.preventDefault();
    const reply_text = new FormData(e.target).get("reply_text");
    try {
      await api(`/api/festival/reviews/${reviewId}/reply`, {
        method: "POST",
        body: { reply_text },
      });
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  if (error && !data) return <p className="form-error">{error}</p>;
  if (!data) return <p className="center-note">Loading…</p>;

  const { festival, role, can_edit_profile, overview, reviews } = data;

  return (
    <>
      <h1>
        {festival.name} <CalibrationTag status={festival.calibration_status} />
      </h1>
      <p className="muted">Signed in as {user.display_name} ({role})</p>
      {error && <p className="form-error">{error}</p>}

      <div className="two-col">
        <div>
          <SubmissionsManager data={data} onStatusChange={updateStatus} />

          <div className="card">
            <h2>Filmmaker reviews</h2>
            {reviews.length === 0 && <p className="muted">No reviews yet.</p>}
            <div className="list-divided">
              {reviews.map((r) => (
                <div key={r.id}>
                  <p><strong><Stars rating={r.rating} /></strong> {r.text}</p>
                  {r.festival_reply ? (
                    <p className="muted" style={{ marginLeft: 16 }}>
                      ↳ Your reply: {r.festival_reply}
                    </p>
                  ) : (
                    <form
                      onSubmit={(e) => replyToReview(r.id, e)}
                      style={{ display: "flex", gap: 10, flexWrap: "wrap" }}
                    >
                      <input
                        name="reply_text"
                        placeholder="Reply publicly…"
                        required
                        style={{ flex: 1, minWidth: 180 }}
                      />
                      <button className="btn btn-secondary" type="submit">Reply</button>
                    </form>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          {can_edit_profile && (
            <ProfileEditor festival={festival} onSaved={load} onError={setError} />
          )}
          <div className="card">
            <h2>This cycle</h2>
            <table className="stack">
              <tbody>
                <tr>
                  <td data-label="Metric">Total submissions</td>
                  <td data-label="Value"><strong>{overview.total_submissions}</strong></td>
                </tr>
                {Object.entries(overview.by_status).map(([status, count]) => (
                  <tr key={status}>
                    <td data-label="Metric">{label(status)}</td>
                    <td data-label="Value">{count}</td>
                  </tr>
                ))}
                <tr>
                  <td data-label="Metric">Gross fees</td>
                  <td data-label="Value"><strong>{money(overview.gross_revenue_cents)}</strong></td>
                </tr>
                <tr>
                  <td data-label="Metric">Used a discount</td>
                  <td data-label="Value">{overview.discounted_count}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="card">
            <h2>Fit scoring</h2>
            {festival.calibration_status === "validated" ? (
              <p>
                Your scoring is <strong>validated</strong> — it has enough
                confirmed selection history to be presented to filmmakers as
                reliable.
              </p>
            ) : (
              <p>
                Your scoring is <strong>calibrating</strong>. Add more past
                selection outcomes to reach validated status — filmmakers see
                this label on every score, so more history means more trust.
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
