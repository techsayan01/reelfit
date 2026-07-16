import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";

const KIND_LABEL = { film: "Film", screenplay: "Screenplay" };

function initials(name) {
  return name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

function ContactLink({ href, label }) {
  if (!href) return null;
  return (
    <li>
      <a href={href} target="_blank" rel="noreferrer noopener">{label}</a>
    </li>
  );
}

export default function FilmmakerProfile() {
  const { handle } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/api/filmmakers/${handle}`).then(setData).catch((e) => setError(e.message));
  }, [handle]);

  if (error) return <p className="center-note">{error}</p>;
  if (!data) return <p className="center-note">Loading…</p>;

  const { summary, selections, filmography, photos = [], press = [] } = data;
  const social = [
    { href: data.website_url, label: "Website" },
    { href: data.instagram && toUrl(data.instagram, "instagram.com"), label: "Instagram" },
    { href: data.facebook && toUrl(data.facebook, "facebook.com"), label: "Facebook" },
    { href: data.twitter && toUrl(data.twitter, "x.com"), label: "X / Twitter" },
    { href: data.linkedin && toUrl(data.linkedin, "linkedin.com/in"), label: "LinkedIn" },
    { href: data.imdb_url, label: "IMDb" },
    { href: data.email && `mailto:${data.email}`, label: data.email },
  ].filter((s) => s.href);

  const hasDetails = data.location || data.hometown || data.education;

  return (
    <>
      <div className="profile-header">
        <div
          className="festival-cover"
          style={data.cover_url ? { backgroundImage: `url(${data.cover_url})` } : undefined}
        >
          {data.headshot_url ? (
            <img className="profile-headshot" src={data.headshot_url} alt={data.display_name} />
          ) : (
            <div className="profile-headshot">{initials(data.display_name)}</div>
          )}
        </div>
      </div>

      <h1 style={{ marginBottom: 0 }}>{data.display_name}</h1>
      {data.title && <p className="profile-title">{data.title}</p>}
      {data.tagline && <p className="profile-tagline">“{data.tagline}”</p>}

      <div className="two-col">
        <div>
          {data.bio && (
            <div className="card">
              <h2>Bio</h2>
              <p style={{ whiteSpace: "pre-wrap" }}>{data.bio}</p>
            </div>
          )}

          {photos.length > 0 && (
            <div className="card">
              <h2>Stills</h2>
              <div className="photo-grid">
                {photos.map((p, i) => (
                  <a key={i} href={p.url} target="_blank" rel="noreferrer"
                     title={[p.caption, p.film_title].filter(Boolean).join(" — ")}>
                    <img src={p.url} alt={p.caption || p.film_title} loading="lazy" />
                  </a>
                ))}
              </div>
            </div>
          )}

          <div className="card">
            <h2>Filmography</h2>
            {filmography.length === 0 && <p className="muted">No public projects yet.</p>}
            <div className="list-divided">
              {filmography.map((f) => (
                <div className="credit-row" key={f.id}>
                  <span className="credit-year">{f.year}</span>
                  <div className="credit-body">
                    <h3>{f.title}</h3>
                    <span className="credit-kind">
                      {KIND_LABEL[f.kind] || f.kind}
                      {f.genre ? ` · ${f.genre}` : ""}
                      {f.runtime_minutes != null ? ` · ${f.runtime_minutes} min` : ""}
                    </span>
                    {f.logline && <p style={{ margin: "6px 0 0" }}>{f.logline}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2>Awards &amp; Selections</h2>
            <p className="muted">
              Every entry here is verified from a real Reelfit submission —
              nothing self-reported.
            </p>
            {selections.length === 0 ? (
              <p className="muted">No festival selections yet.</p>
            ) : (
              <>
                <p>
                  <strong>{summary.awards}</strong> award
                  {summary.awards !== 1 ? "s" : ""} ·{" "}
                  <strong>{summary.selections}</strong> selection
                  {summary.selections !== 1 ? "s" : ""}
                </p>
                <div className="list-divided">
                  {selections.map((s, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <div>
                        <strong>
                          {s.festival_slug ? (
                            <Link to={`/festivals/${s.festival_slug}`}>{s.festival_name}</Link>
                          ) : s.festival_name}
                        </strong>
                        {s.edition_label && <span className="muted"> · {s.edition_label}</span>}
                        <br />
                        <span className="muted">{s.film_title}</span>
                      </div>
                      <span className={badgeClass(s.status)}>{s.achievement}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          {press.length > 0 && (
            <div className="card">
              <h2>News &amp; Reviews</h2>
              <div className="list-divided">
                {press.map((pr, i) => (
                  <p key={i} style={{ margin: 0 }}>
                    {pr.url
                      ? <a href={pr.url} target="_blank" rel="noreferrer"><strong>{pr.title}</strong></a>
                      : <strong>{pr.title}</strong>}
                    <br />
                    <span className="muted">
                      {[pr.outlet, pr.film_title].filter(Boolean).join(" · ")}
                    </span>
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        <div>
          {social.length > 0 && (
            <div className="card">
              <h2>Contact &amp; links</h2>
              <ul className="contact-list">
                {social.map((s) => (
                  <ContactLink key={s.label} href={s.href} label={s.label} />
                ))}
              </ul>
            </div>
          )}

          {hasDetails && (
            <div className="card">
              <h2>Details</h2>
              <dl className="detail-grid">
                {data.location && (<><dt>Based in</dt><dd>{data.location}</dd></>)}
                {data.hometown && (<><dt>Hometown</dt><dd>{data.hometown}</dd></>)}
                {data.education && (<><dt>Education</dt><dd style={{ whiteSpace: "pre-wrap" }}>{data.education}</dd></>)}
              </dl>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function badgeClass(status) {
  if (status === "award_winner") return "selection-badge badge-award";
  if (["selected", "honorable_mention"].includes(status)) return "selection-badge badge-selected";
  return "selection-badge";
}

// Accept either a full URL or a bare handle/username and normalize to a URL.
function toUrl(value, host) {
  if (/^https?:\/\//i.test(value)) return value;
  const clean = value.replace(/^@/, "").replace(/^\//, "");
  return `https://${host}/${clean}`;
}
