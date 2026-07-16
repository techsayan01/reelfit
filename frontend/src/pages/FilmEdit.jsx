import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";

const LINK_KINDS = [
  ["website", "Website"],
  ["instagram", "Instagram"],
  ["bluesky", "Bluesky"],
  ["other", "Other"],
];
const linkLabel = (k) => LINK_KINDS.find(([v]) => v === k)?.[1] ?? k;

/* A small add/remove manager used for each media collection. `fields` describes
   the inputs of the add-row form; `render` draws each existing item. */
function MediaCard({ title, help, items, fields, render, onAdd, onDelete }) {
  const submit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const body = {};
    fields.forEach((f) => { body[f.name] = form.get(f.name) || ""; });
    await onAdd(body);
    e.target.reset();
  };

  return (
    <div className="card">
      <h2>{title}</h2>
      {help && <p className="muted">{help}</p>}
      {items.length > 0 && (
        <div className="list-divided">
          {items.map((it) => (
            <div key={it.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
              <div style={{ flex: 1, minWidth: 0, overflowWrap: "anywhere" }}>{render(it)}</div>
              <button className="btn btn-quiet" onClick={() => onDelete(it.id)}>Remove</button>
            </div>
          ))}
        </div>
      )}
      <form onSubmit={submit} style={{ marginTop: 12 }}>
        {fields.map((f) => (
          f.type === "select" ? (
            <select key={f.name} name={f.name} defaultValue={f.options[0][0]} aria-label={f.label}>
              {f.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          ) : (
            <input key={f.name} name={f.name} required={f.required}
                   placeholder={f.label} aria-label={f.label} type={f.type || "text"} />
          )
        ))}
        <div className="btn-row">
          <button className="btn btn-secondary" type="submit">Add</button>
        </div>
      </form>
    </div>
  );
}

export default function FilmEdit() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api(`/api/films/${id}`).then(setData).catch((e) => setError(e.message));
  }, [id]);
  useEffect(load, [load]);

  const call = (path, opts) => api(path, opts).then((media) =>
    setData((d) => ({ ...d, ...media }))).catch((e) => setError(e.message));

  if (error && !data) return <p className="form-error">{error}</p>;
  if (!data) return <p className="center-note">Loading…</p>;

  const base = `/api/films/${id}`;
  const add = (kind) => (body) => call(`${base}/${kind}`, { method: "POST", body });
  const del = (kind) => (itemId) => call(`${base}/${kind}/${itemId}`, { method: "DELETE" });

  return (
    <>
      <div className="btn-row" style={{ marginTop: 0 }}>
        <Link className="btn btn-quiet" to="/dashboard">← My films</Link>
      </div>
      <h1>Project page — {data.film.title}</h1>
      <p className="muted">
        Everything here appears to festivals on your submission and, where public,
        on your profile. Verified festival selections are added automatically — you
        only need to list screenings and awards from outside Reelfit.
      </p>
      {error && <p className="form-error">{error}</p>}

      <div className="two-col">
        <div>
          <MediaCard
            title="Still photos"
            help="Image URLs shown as a gallery on your project page."
            items={data.photos}
            fields={[
              { name: "url", label: "Image URL (https://…)", required: true },
              { name: "caption", label: "Caption (optional)" },
            ]}
            render={(p) => (
              <p style={{ margin: 0 }}>
                <a href={p.url} target="_blank" rel="noreferrer">{p.url}</a>
                {p.caption && <><br /><span className="muted">{p.caption}</span></>}
              </p>
            )}
            onAdd={add("photos")}
            onDelete={del("photos")}
          />

          <MediaCard
            title="News &amp; Reviews"
            help="Press about your project."
            items={data.press}
            fields={[
              { name: "title", label: "Headline", required: true },
              { name: "outlet", label: "Outlet (e.g. Variety)" },
              { name: "url", label: "Link (https://…)" },
            ]}
            render={(pr) => (
              <p style={{ margin: 0 }}>
                <strong>{pr.url ? <a href={pr.url} target="_blank" rel="noreferrer">{pr.title}</a> : pr.title}</strong>
                {pr.outlet && <><br /><span className="muted">{pr.outlet}</span></>}
              </p>
            )}
            onAdd={add("press")}
            onDelete={del("press")}
          />
        </div>

        <div>
          <MediaCard
            title="Project links"
            help="Website and social links for this project."
            items={data.links}
            fields={[
              { name: "kind", label: "Type", type: "select", options: LINK_KINDS },
              { name: "url", label: "URL (https://…)", required: true },
            ]}
            render={(l) => (
              <p style={{ margin: 0 }}>
                <span className="credit-kind">{linkLabel(l.kind)}</span><br />
                <a href={l.url} target="_blank" rel="noreferrer">{l.url}</a>
              </p>
            )}
            onAdd={add("links")}
            onDelete={del("links")}
          />

          <MediaCard
            title="Screenings &amp; Awards"
            help="Festival screenings or awards from outside Reelfit. Your Reelfit selections show automatically."
            items={data.screenings}
            fields={[
              { name: "festival_name", label: "Festival / event", required: true },
              { name: "award", label: "Award (optional)" },
              { name: "location", label: "Location (optional)" },
              { name: "happened_on", label: "Year or date (optional)" },
            ]}
            render={(s) => (
              <p style={{ margin: 0 }}>
                <strong>{s.festival_name}</strong>
                {s.award && <> — {s.award}</>}
                {(s.location || s.happened_on) && (
                  <><br /><span className="muted">{[s.location, s.happened_on].filter(Boolean).join(" · ")}</span></>
                )}
              </p>
            )}
            onAdd={add("screenings")}
            onDelete={del("screenings")}
          />
        </div>
      </div>
    </>
  );
}
