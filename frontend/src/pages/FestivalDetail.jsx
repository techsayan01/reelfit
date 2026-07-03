import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money } from "../api.js";
import { useAuth } from "../AuthContext.jsx";
import CalibrationTag from "../components/CalibrationTag.jsx";

const Stars = ({ rating }) => (
  <span className="stars">{"★".repeat(rating)}{"☆".repeat(5 - rating)}</span>
);

export default function FestivalDetail() {
  const { slug } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/api/festivals/${slug}`).then(setData).catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p className="center-note">Loading…</p>;

  const { festival, edition, tier, categories, reviews } = data;

  return (
    <>
      <h1>
        {festival.name} <CalibrationTag status={festival.calibration_status} />
      </h1>
      <p>{festival.description}</p>
      {festival.country && (
        <p className="muted">
          {festival.country}
          {festival.region && <> · {festival.region}</>}
        </p>
      )}

      <div className="two-col">
        <div className="card">
          <h2>Submissions</h2>
          {edition ? (
            <>
              <p>
                {edition.label} edition — open until <strong>{edition.closes_on}</strong>
                {tier && <> · current tier: {tier.name} (deadline {tier.deadline})</>}
              </p>
              <table className="stack">
                <thead>
                  <tr><th>Category</th><th>Runtime</th><th>Fee</th></tr>
                </thead>
                <tbody>
                  {categories.map((c) => (
                    <tr key={c.id}>
                      <td data-label="Category">{c.name}</td>
                      <td data-label="Runtime">{c.min_runtime_minutes}–{c.max_runtime_minutes} min</td>
                      <td data-label="Fee">{money(c.fee_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {user && user.kind === "filmmaker" && (
                <p className="muted" style={{ marginTop: 16 }}>
                  To send a film here, score it first from <Link to="/dashboard">your films</Link> —
                  you'll see how well it fits before paying.
                </p>
              )}
            </>
          ) : (
            <p>Not currently open for submissions.</p>
          )}
        </div>

        <div className="card">
          <h2>Reviews from filmmakers</h2>
          <p className="muted">Only filmmakers who actually submitted here can review.</p>
          {reviews.length === 0 && <p>No reviews yet.</p>}
          <div className="list-divided">
            {reviews.map((r) => (
              <div key={r.id}>
                <p><strong><Stars rating={r.rating} /></strong></p>
                <p>{r.text}</p>
                {r.festival_reply && (
                  <p className="muted" style={{ marginLeft: 16 }}>
                    ↳ Festival's reply: {r.festival_reply}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
