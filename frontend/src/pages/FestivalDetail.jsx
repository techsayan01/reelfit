import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money } from "../api.js";
import { useAuth } from "../AuthContext.jsx";
import CalibrationTag from "../components/CalibrationTag.jsx";

const Stars = ({ rating }) => (
  <span className="stars">{"★".repeat(rating)}{"☆".repeat(5 - rating)}</span>
);

function StatBlock({ value, label }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="stat-block">
      <div className="display stat-value">{value}</div>
      <div className="muted">{label}</div>
    </div>
  );
}

export default function FestivalDetail() {
  const { slug } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("about");

  useEffect(() => {
    api(`/api/festivals/${slug}`).then(setData).catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p className="center-note">Loading…</p>;

  const { festival, edition, tier, timeline, stats, categories, reviews } = data;

  return (
    <>
      <div
        className="festival-cover"
        style={festival.cover_url ? { backgroundImage: `url(${festival.cover_url})` } : undefined}
      >
        {festival.logo_url && (
          <img className="festival-logo" src={festival.logo_url} alt={`${festival.name} logo`} />
        )}
      </div>

      <h1>
        {festival.name} <CalibrationTag status={festival.calibration_status} />
      </h1>
      {festival.country && (
        <p className="muted">
          {festival.country}
          {festival.region && <> · {festival.region}</>}
        </p>
      )}

      <div className="stat-row">
        <StatBlock value={stats.years_running} label={`year${stats.years_running !== 1 ? "s" : ""} running`} />
        <StatBlock value={stats.total_submissions} label="submissions on Reelfit" />
        <StatBlock value={stats.selected} label="selected" />
        <StatBlock
          value={stats.avg_rating !== null ? `${stats.avg_rating}★` : null}
          label={`from ${stats.review_count} verified review${stats.review_count !== 1 ? "s" : ""}`}
        />
      </div>
      <p className="muted" style={{ fontSize: "0.9rem" }}>
        Stats come from real Reelfit submission records — never self-reported.
      </p>

      <div className="tab-row" role="tablist">
        {["about", "rules", "reviews"].map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            className={`tab-btn ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t[0].toUpperCase() + t.slice(1)}
            {t === "reviews" && ` (${reviews.length})`}
          </button>
        ))}
      </div>

      <div className="two-col">
        <div>
          {tab === "about" && (
            <div className="card">
              <p>{festival.description || "No description yet."}</p>
              {festival.awards_and_prizes && (
                <>
                  <h3>Awards & prizes</h3>
                  {festival.awards_and_prizes.split("\n").map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </>
              )}
              {(festival.venue_name || festival.venue_address) && (
                <>
                  <h3>Venue</h3>
                  <p>
                    {festival.venue_name}
                    {festival.venue_address && (
                      <>
                        <br />
                        <span className="muted">{festival.venue_address}</span>
                      </>
                    )}
                  </p>
                </>
              )}
              {(festival.contact_email || festival.phone || festival.website || festival.twitter || festival.instagram) && (
                <>
                  <h3>Contact</h3>
                  <p className="contact-links">
                    {festival.contact_email && <a href={`mailto:${festival.contact_email}`}>Email</a>}
                    {festival.phone && <a href={`tel:${festival.phone}`}>{festival.phone}</a>}
                    {festival.website && <a href={festival.website} target="_blank" rel="noreferrer">Website</a>}
                    {festival.twitter && <a href={festival.twitter} target="_blank" rel="noreferrer">X</a>}
                    {festival.instagram && <a href={festival.instagram} target="_blank" rel="noreferrer">Instagram</a>}
                  </p>
                </>
              )}
            </div>
          )}

          {tab === "rules" && (
            <div className="card">
              {festival.rules
                ? festival.rules.split("\n").map((line, i) => <p key={i}>{line}</p>)
                : <p className="muted">This festival hasn't published rules yet.</p>}
            </div>
          )}

          {tab === "reviews" && (
            <div className="card">
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
          )}

          <div className="card">
            <h2>Categories & fees</h2>
            {edition ? (
              <table className="stack">
                <thead>
                  <tr><th>Category</th><th>Accepts</th><th>Fee</th></tr>
                </thead>
                <tbody>
                  {categories.map((c) => (
                    <tr key={c.id}>
                      <td data-label="Category">{c.name}</td>
                      <td data-label="Accepts">
                        {c.kind === "screenplay"
                          ? "Scripts"
                          : `Films ${c.min_runtime_minutes}–${c.max_runtime_minutes} min`}
                      </td>
                      <td data-label="Fee">{money(c.fee_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>Not currently open for submissions.</p>
            )}
            {user && user.kind === "filmmaker" && edition && (
              <p className="muted" style={{ marginTop: 16 }}>
                To send a project here, score it first from{" "}
                <Link to="/dashboard">your films</Link> — you'll see how well it
                fits before paying.
              </p>
            )}
          </div>
        </div>

        <div>
          {edition && (
            <div className="card">
              <h2>Dates & deadlines</h2>
              <p className="muted">{edition.label} edition</p>
              <ol className="timeline">
                {timeline.map((t, i) => (
                  <li key={i} className={t.is_current ? "current" : ""}>
                    <span className="timeline-date">{t.date}</span>
                    <span className="timeline-label">
                      {t.label}
                      {t.is_current && <span className="tag tag-calibrating"> current</span>}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
