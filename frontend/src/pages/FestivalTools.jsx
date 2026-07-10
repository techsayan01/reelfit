import { useCallback, useEffect, useState } from "react";
import { api, money } from "../api.js";

/* Owner-side analytics & tooling cards for the festival dashboard:
   marketing attribution, transactions, reports & exports, webhooks,
   ad creator, laurel center. */

export function MarketingCard() {
  const [data, setData] = useState(null);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    api("/api/festival/marketing").then(setData).catch(() => {});
  }, []);

  if (!data) return null;
  const { rows, totals, share_base } = data;

  const copyLink = async (source) => {
    const url = `${window.location.origin}${share_base}${source}`;
    await navigator.clipboard.writeText(url);
    setCopied(source);
    setTimeout(() => setCopied(""), 1500);
  };

  return (
    <div className="card">
      <h2>Marketing summary</h2>
      <p className="muted">
        Real conversion analytics: page views → submissions by traffic source.
        Share links like <span className="tracking-number">?ref=instagram</span>{" "}
        to attribute each channel.
      </p>
      <p>
        <strong>{totals.views}</strong> page views ·{" "}
        <strong>{totals.submissions}</strong> submissions ·{" "}
        <strong>{money(totals.revenue_cents)}</strong> in fees
      </p>
      {rows.length > 0 && (
        <table className="stack">
          <thead>
            <tr><th>Source</th><th>Views</th><th>Submissions</th><th>Conversion</th><th>Fees</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.source}>
                <td data-label="Source"><strong>{r.source}</strong></td>
                <td data-label="Views">{r.views}</td>
                <td data-label="Submissions">{r.submissions}</td>
                <td data-label="Conversion">
                  {r.conversion_pct !== null ? `${r.conversion_pct}%` : "—"}
                </td>
                <td data-label="Fees">{money(r.revenue_cents)}</td>
                <td data-label="">
                  <button className="btn btn-quiet" onClick={() => copyLink(r.source)}>
                    {copied === r.source ? "Copied!" : "Copy link"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function TransactionsCard() {
  const [months, setMonths] = useState(null);
  const [openMonth, setOpenMonth] = useState(null);

  useEffect(() => {
    api("/api/festival/transactions").then((d) => setMonths(d.months)).catch(() => {});
  }, []);

  if (!months || months.length === 0) return null;

  return (
    <div className="card">
      <h2>Transactions</h2>
      <div className="list-divided">
        {months.map((m) => (
          <div key={m.month}>
            <p style={{ margin: 0, display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span>
                <strong>{m.month}</strong>{" "}
                <button className="btn btn-quiet"
                        onClick={() => setOpenMonth(openMonth === m.month ? null : m.month)}>
                  {openMonth === m.month ? "Hide details" : "Show details"}
                </button>
              </span>
              <strong>{money(m.total_cents)}</strong>
            </p>
            {openMonth === m.month && (
              <table className="stack">
                <tbody>
                  {m.items.map((item, i) => (
                    <tr key={i}>
                      <td data-label="Ref"><span className="tracking-number">{item.tracking_number}</span></td>
                      <td data-label="Project">{item.film_title}</td>
                      <td data-label="Date">{item.date}</td>
                      <td data-label="Amount">{money(item.amount_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

const REPORT_TYPES = [
  ["sales_by_category", "Sales by category"],
  ["sales_by_status", "Sales by judging status"],
  ["sales_by_month", "Sales by month"],
  ["sales_by_source", "Sales by traffic source"],
];

export function ReportsCard({ onError }) {
  const [report, setReport] = useState("sales_by_category");
  const [configs, setConfigs] = useState([]);
  const [availableColumns, setAvailableColumns] = useState([]);
  const [building, setBuilding] = useState(false);

  const load = useCallback(() => {
    api("/api/festival/export-configs").then((d) => {
      setConfigs(d.configs);
      setAvailableColumns(d.available_columns);
    }).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const addConfig = async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const columns = availableColumns.filter((c) => fd.get(`col-${c}`) === "on");
    try {
      await api("/api/festival/export-configs", {
        method: "POST",
        body: { name: fd.get("name"), columns },
      });
      form.reset();
      setBuilding(false);
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  const removeConfig = async (c) => {
    if (!window.confirm(`Delete the “${c.name}” export configuration?`)) return;
    try {
      await api(`/api/festival/export-configs/${c.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Reports & exports</h2>

      <label htmlFor="report-type">Report type</label>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <select id="report-type" value={report} onChange={(e) => setReport(e.target.value)}
                style={{ flex: 2, minWidth: 160 }}>
          {REPORT_TYPES.map(([value, text]) => (
            <option key={value} value={value}>{text}</option>
          ))}
        </select>
        <a className="btn btn-secondary" href={`/api/festival/reports?report=${report}`}>
          Create report
        </a>
      </div>

      <h3 style={{ marginTop: 24 }}>Submission exports</h3>
      <p className="muted" style={{ fontSize: "0.9rem" }}>
        Spreadsheets of your submissions. Contact columns use Reelfit relay
        addresses — filmmaker PII never leaves through exports.
      </p>
      <div className="list-divided">
        <p style={{ margin: 0, display: "flex", justifyContent: "space-between", gap: 8 }}>
          <span>All columns</span>
          <a className="btn btn-quiet" href="/api/festival/export">Download CSV</a>
        </p>
        {configs.map((c) => (
          <p key={c.id} style={{ margin: 0, display: "flex", justifyContent: "space-between", gap: 8 }}>
            <span>
              <strong>{c.name}</strong>{" "}
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                ({c.columns.length} columns)
              </span>
            </span>
            <span>
              <a className="btn btn-quiet" href={`/api/festival/export?config_id=${c.id}`}>
                Download CSV
              </a>
              <button className="btn btn-quiet" onClick={() => removeConfig(c)}>Delete</button>
            </span>
          </p>
        ))}
      </div>

      {!building ? (
        <div className="btn-row">
          <button className="btn btn-secondary" onClick={() => setBuilding(true)}>
            Add a configuration
          </button>
        </div>
      ) : (
        <form onSubmit={addConfig}>
          <label htmlFor="config-name">Configuration name</label>
          <input id="config-name" name="name" required placeholder="e.g. Website results" />
          <label>Columns</label>
          {availableColumns.map((c) => (
            <label key={c} style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400, margin: "2px 0" }}>
              <input name={`col-${c}`} type="checkbox" defaultChecked
                     style={{ width: "auto", minHeight: "auto" }} />
              {c.replaceAll("_", " ")}
            </label>
          ))}
          <div className="btn-row">
            <button className="btn btn-primary" type="submit">Save configuration</button>
            <button className="btn btn-quiet" type="button" onClick={() => setBuilding(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}

export function WebhooksCard({ onError }) {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);

  const load = useCallback(() => {
    api("/api/festival/webhooks").then(setData).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const add = async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const events = data.available_events.filter((ev) => fd.get(`ev-${ev}`) === "on");
    try {
      await api("/api/festival/webhooks", {
        method: "POST",
        body: { url: fd.get("url"), events },
      });
      form.reset();
      setOpen(false);
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  const remove = async (w) => {
    if (!window.confirm(`Remove the webhook to ${w.url}?`)) return;
    try {
      await api(`/api/festival/webhooks/${w.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  if (!data) return null;

  return (
    <div className="card">
      <h2>Webhooks</h2>
      <p className="muted">
        Reelfit POSTs event JSON to your URL — new submissions, judging status
        changes.
      </p>
      <div className="list-divided">
        {data.webhooks.map((w) => (
          <div key={w.id}>
            <p style={{ margin: 0, display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span style={{ wordBreak: "break-all" }}>
                <strong>{w.url}</strong>
                <br />
                <span className="muted" style={{ fontSize: "0.85rem" }}>
                  {w.events.join(", ")}
                  {w.recent.length > 0 && (
                    <> · last delivery: {w.recent[0].ok ? "✓ ok" : "✗ failed"}</>
                  )}
                </span>
              </span>
              <button className="btn btn-quiet" onClick={() => remove(w)}>Remove</button>
            </p>
          </div>
        ))}
      </div>
      {!open ? (
        <div className="btn-row">
          <button className="btn btn-secondary" onClick={() => setOpen(true)}>
            Add a webhook
          </button>
        </div>
      ) : (
        <form onSubmit={add}>
          <label htmlFor="hook-url">URL</label>
          <input id="hook-url" name="url" type="url" required placeholder="https://…" />
          <label>Events</label>
          {data.available_events.map((ev) => (
            <label key={ev} style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400 }}>
              <input name={`ev-${ev}`} type="checkbox" defaultChecked
                     style={{ width: "auto", minHeight: "auto" }} />
              {ev}
            </label>
          ))}
          <div className="btn-row">
            <button className="btn btn-primary" type="submit">Add webhook</button>
            <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}

export function AdCreatorCard() {
  const [headline, setHeadline] = useState("Submissions open");
  const [subline, setSubline] = useState("");
  const [cta, setCta] = useState("Submit now");
  const [bg, setBg] = useState("amber");

  const params = new URLSearchParams({ headline, subline, cta, bg });

  return (
    <div className="card">
      <h2>Ad creator</h2>
      <p className="muted">
        Graphics for Instagram, Facebook or X, in your Reelfit branding.
      </p>
      <label htmlFor="ad-headline">Headline</label>
      <input id="ad-headline" value={headline} onChange={(e) => setHeadline(e.target.value)} />
      <label htmlFor="ad-subline">Subline</label>
      <input id="ad-subline" value={subline} onChange={(e) => setSubline(e.target.value)}
             placeholder="e.g. Final deadline July 25" />
      <label htmlFor="ad-cta">Call to action</label>
      <input id="ad-cta" value={cta} onChange={(e) => setCta(e.target.value)} />
      <label htmlFor="ad-bg">Background</label>
      <select id="ad-bg" value={bg} onChange={(e) => setBg(e.target.value)}>
        <option value="amber">Marquee amber</option>
        <option value="ink">Reel ink</option>
        <option value="teal">Darkroom teal</option>
      </select>
      <img
        src={`/api/festival/ad.svg?${params.toString()}&fmt=square`}
        alt="Ad preview"
        style={{ width: "100%", borderRadius: 8, marginTop: 12 }}
      />
      <div className="btn-row">
        <a className="btn btn-secondary" download="reelfit-ad-square.svg"
           href={`/api/festival/ad.svg?${params.toString()}&fmt=square`}>
          Instagram (square)
        </a>
        <a className="btn btn-secondary" download="reelfit-ad-wide.svg"
           href={`/api/festival/ad.svg?${params.toString()}&fmt=wide`}>
          Facebook / X (wide)
        </a>
      </div>
    </div>
  );
}

export function LaurelCard({ festival }) {
  const [text, setText] = useState("Official Selection");
  const [variant, setVariant] = useState("black");
  const [copied, setCopied] = useState(false);

  const url = `/api/festivals/${festival.slug}/laurel.svg?text=${encodeURIComponent(text)}&variant=${variant}`;

  const copyLink = async () => {
    await navigator.clipboard.writeText(window.location.origin + url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="card">
      <h2>Laurel center</h2>
      <p className="muted">
        Laurels for your selected filmmakers — share the public link so
        recipients can download them.
      </p>
      <label htmlFor="laurel-text">Laurel text</label>
      <input id="laurel-text" value={text} onChange={(e) => setText(e.target.value)} />
      <label htmlFor="laurel-variant">Variant</label>
      <select id="laurel-variant" value={variant} onChange={(e) => setVariant(e.target.value)}>
        <option value="black">Black (for light backgrounds)</option>
        <option value="white">White (for dark backgrounds)</option>
      </select>
      <div style={{
        background: variant === "white" ? "#1C1917" : "#fff",
        borderRadius: 8, padding: 12, marginTop: 12,
      }}>
        <img src={url} alt="Laurel preview" style={{ width: "100%" }} />
      </div>
      <div className="btn-row">
        <a className="btn btn-secondary" download="reelfit-laurel.svg" href={url}>
          Download laurel
        </a>
        <button className="btn btn-quiet" onClick={copyLink}>
          {copied ? "Copied!" : "Copy public link"}
        </button>
      </div>
    </div>
  );
}
