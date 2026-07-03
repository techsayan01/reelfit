import { useCallback, useEffect, useState } from "react";
import { api, money } from "../api.js";
import { useAuth } from "../AuthContext.jsx";
import CalibrationTag from "../components/CalibrationTag.jsx";

const Stars = ({ rating }) => (
  <span className="stars">{"★".repeat(rating)}{"☆".repeat(5 - rating)}</span>
);

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

  const { festival, role, can_update, overview, submissions, reviews, statuses } = data;

  return (
    <>
      <h1>
        {festival.name} <CalibrationTag status={festival.calibration_status} />
      </h1>
      <p className="muted">Signed in as {user.display_name} ({role})</p>
      {error && <p className="form-error">{error}</p>}

      <div className="two-col">
        <div>
          <div className="card">
            <h2>Submissions ({overview.total_submissions})</h2>
            {submissions.length === 0 && <p>No submissions yet.</p>}
            {submissions.length > 0 && (
              <table className="stack">
                <thead>
                  <tr><th>Film</th><th>Contact</th><th>Fee</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {submissions.map((s) => (
                    <tr key={s.id}>
                      <td data-label="Film">
                        <strong>{s.film_title}</strong>
                        <br />
                        <span className="muted">
                          {s.film_genre} · {s.film_runtime_minutes} min
                        </span>
                      </td>
                      <td data-label="Contact"><span className="muted">{s.contact}</span></td>
                      <td data-label="Fee">{money(s.fee_paid_cents)}</td>
                      <td data-label="Status">
                        {can_update ? (
                          <select
                            aria-label="Judging status"
                            value={s.status}
                            onChange={(e) => updateStatus(s, e.target.value)}
                          >
                            {statuses.map((st) => (
                              <option key={st} value={st}>{st.replace("_", " ")}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="tag tag-status">{s.status.replace("_", " ")}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

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
                    <td data-label="Metric">{status.replace("_", " ")}</td>
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
