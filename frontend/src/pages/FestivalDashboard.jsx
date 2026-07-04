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
  const { submissions, statuses, can_update, flags = [] } = data;
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [flagFilter, setFlagFilter] = useState("all");

  const categories = useMemo(
    () => [...new Set(submissions.map((s) => s.category).filter(Boolean))],
    [submissions]
  );

  const filtered = submissions.filter((s) => {
    if (statusFilter !== "all" && s.status !== statusFilter) return false;
    if (categoryFilter !== "all" && s.category !== categoryFilter) return false;
    if (flagFilter !== "all" && String(s.flag?.id ?? "") !== flagFilter) return false;
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
            {flags.length > 0 && (
              <select
                aria-label="Filter by flag"
                value={flagFilter}
                onChange={(e) => setFlagFilter(e.target.value)}
              >
                <option value="all">All flags</option>
                {flags.map((f) => (
                  <option key={f.id} value={String(f.id)}>{f.name}</option>
                ))}
              </select>
            )}
          </div>
          <p className="muted" style={{ fontSize: "0.9rem" }}>
            {filtered.length} submission{filtered.length !== 1 ? "s" : ""} match your criteria
          </p>
          <table className="stack">
            <thead>
              <tr>
                <th>Project</th><th>Category</th><th>Fee</th><th>Rating</th><th>Date</th><th>Judging status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td data-label="Project">
                    {s.flag && (
                      <span className="flag-dot" style={{ background: s.flag.color }}
                            title={s.flag.name} />
                    )}
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
                  <td data-label="Rating">
                    {s.rating !== null ? (
                      <><strong>{s.rating}</strong><span className="muted">/10</span></>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
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

function QueueCard() {
  const [queue, setQueue] = useState([]);

  useEffect(() => {
    api("/api/festival/queue").then((d) => setQueue(d.queue)).catch(() => {});
  }, []);

  if (queue.length === 0) return null;
  return (
    <div className="card">
      <h2>Your review queue ({queue.length})</h2>
      <div className="list-divided">
        {queue.map((q) => (
          <p key={q.submission_id} style={{ margin: 0 }}>
            <Link to={`/festival/submissions/${q.submission_id}`}>
              <strong>{q.film_title}</strong>
            </Link>{" "}
            <span className="tracking-number">{q.tracking_number}</span>
          </p>
        ))}
      </div>
    </div>
  );
}

function StaffCard({ onError }) {
  const [staff, setStaff] = useState([]);
  const [role, setRole] = useState("jury");

  const load = useCallback(() => {
    api("/api/festival/staff").then((d) => setStaff(d.staff)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const add = async (e) => {
    e.preventDefault();
    const form = e.target;
    try {
      await api("/api/festival/staff", {
        method: "POST",
        body: { email: new FormData(form).get("email"), role },
      });
      form.reset();
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  const remove = async (member) => {
    if (!window.confirm(`Remove ${member.display_name} from your festival's staff?`)) return;
    try {
      await api(`/api/festival/staff/${member.membership_id}`, { method: "DELETE" });
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Staff & judges</h2>
      <div className="list-divided">
        {staff.map((m) => (
          <p key={m.membership_id} style={{ margin: 0, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <span>
              <strong>{m.display_name}</strong>{" "}
              <span className="tag tag-status">{m.role}</span>
            </span>
            {m.role !== "owner" && (
              <button className="btn btn-quiet" onClick={() => remove(m)}>Remove</button>
            )}
          </p>
        ))}
      </div>
      <form onSubmit={add}>
        <label htmlFor="staff-email">Add by email (existing Reelfit account)</label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input id="staff-email" name="email" type="email" required
                 placeholder="jury@example.com" style={{ flex: 2, minWidth: 160 }} />
          <select aria-label="Role" value={role} onChange={(e) => setRole(e.target.value)}
                  style={{ flex: 1, minWidth: 110 }}>
            <option value="programmer">programmer</option>
            <option value="jury">jury</option>
            <option value="viewer">viewer</option>
          </select>
        </div>
        <div className="btn-row">
          <button className="btn btn-secondary" type="submit">Add staff member</button>
        </div>
      </form>
    </div>
  );
}

function RubricCard({ onError }) {
  const [criteria, setCriteria] = useState([]);

  const load = useCallback(() => {
    api("/api/festival/rubric").then((d) => setCriteria(d.criteria)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const add = async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    try {
      await api("/api/festival/rubric", {
        method: "POST",
        body: { name: fd.get("name"), weight: Number(fd.get("weight")) || 1 },
      });
      form.reset();
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  const remove = async (c) => {
    if (!window.confirm(`Delete “${c.name}”? Existing scores for it are removed too.`)) return;
    try {
      await api(`/api/festival/rubric/${c.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  const addDefaults = async () => {
    try {
      await api("/api/festival/rubric/defaults", { method: "POST" });
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Scoring rubric</h2>
      <p className="muted">Judges score each entry 1–10 on these criteria; weights set their importance.</p>
      {criteria.length === 0 && (
        <div className="btn-row" style={{ marginTop: 0 }}>
          <button className="btn btn-secondary" onClick={addDefaults}>
            Use the standard film judging form
          </button>
        </div>
      )}
      <div className="list-divided">
        {criteria.map((c) => (
          <p key={c.id} style={{ margin: 0, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <span><strong>{c.name}</strong> <span className="muted">weight {c.weight}</span></span>
            <button className="btn btn-quiet" onClick={() => remove(c)}>Delete</button>
          </p>
        ))}
      </div>
      <form onSubmit={add}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input name="name" required placeholder="e.g. Storytelling" style={{ flex: 2, minWidth: 140 }} />
          <input name="weight" type="number" step="0.5" min="0.5" max="10"
                 placeholder="Weight" style={{ flex: 1, minWidth: 90 }} />
        </div>
        <div className="btn-row">
          <button className="btn btn-secondary" type="submit">Add criterion</button>
        </div>
      </form>
    </div>
  );
}

const FIELD_TYPES = [
  ["text", "Text (single line answer)"],
  ["paragraph", "Text (paragraph answer)"],
  ["dropdown", "Dropdown (choose one)"],
  ["yes_no", "Yes / No"],
];

function QuestionsCard({ onError }) {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [fieldType, setFieldType] = useState("text");

  const load = useCallback(() => {
    api("/api/festival/questions").then(setData).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const add = async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    try {
      await api("/api/festival/questions", {
        method: "POST",
        body: {
          field_type: fieldType,
          question: fd.get("question"),
          options: fd.get("options") || "",
          category_id: fd.get("category_id") ? Number(fd.get("category_id")) : null,
        },
      });
      form.reset();
      setOpen(false);
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  const remove = async (q) => {
    if (!window.confirm(`Delete “${q.question}”? Existing answers are removed too.`)) return;
    try {
      await api(`/api/festival/questions/${q.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  if (!data) return null;
  const typeLabel = (v) => FIELD_TYPES.find(([t]) => t === v)?.[1] ?? v;
  const catName = (id) =>
    data.categories.find((c) => c.id === id)?.name ?? "unknown category";

  return (
    <div className="card">
      <h2>Custom submission form</h2>
      <p className="muted">
        Submitters must answer these questions when they send you a project.
        Answers appear on the Custom form tab of each submission.
      </p>
      <div className="list-divided">
        {data.questions.map((q) => (
          <div key={q.id} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "start" }}>
            <div>
              <strong>{q.question}</strong>
              <br />
              <span className="muted" style={{ fontSize: "0.9rem" }}>
                {typeLabel(q.field_type)}
                {q.category_id !== null ? ` · ${catName(q.category_id)} only` : " · all categories"}
              </span>
            </div>
            <button className="btn btn-quiet" onClick={() => remove(q)}>Delete</button>
          </div>
        ))}
      </div>

      {!open ? (
        <div className="btn-row">
          <button className="btn btn-secondary" onClick={() => setOpen(true)}>
            Add a question
          </button>
        </div>
      ) : (
        <form onSubmit={add}>
          <label htmlFor="field_type">Field type</label>
          <select id="field_type" value={fieldType} onChange={(e) => setFieldType(e.target.value)}>
            {FIELD_TYPES.map(([value, text]) => (
              <option key={value} value={value}>{text}</option>
            ))}
          </select>

          <label htmlFor="question">Title / question</label>
          <input id="question" name="question" required placeholder="Ex: Did you attend film school?" />

          {fieldType === "dropdown" && (
            <>
              <label htmlFor="options">Options (one per line)</label>
              <textarea id="options" name="options" required
                        placeholder={"Instagram\nA friend or colleague\nOther"} />
            </>
          )}

          <label htmlFor="q-category">Require for</label>
          <select id="q-category" name="category_id">
            <option value="">All categories</option>
            {data.categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name} only</option>
            ))}
          </select>

          <div className="btn-row">
            <button className="btn btn-primary" type="submit">Save question</button>
            <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}

const FLAG_COLORS = [
  ["#C0392B", "Red"], ["#D4A017", "Yellow"], ["#2E7D46", "Green"],
  ["#2C5AA0", "Blue"], ["#7D3C98", "Purple"], ["#C2185B", "Pink"],
  ["#C86A1B", "Orange"], ["#6B6560", "Gray"], ["#1C1917", "Black"],
];

function FlagsCard({ onError, onChanged }) {
  const [flags, setFlags] = useState([]);
  const [color, setColor] = useState(FLAG_COLORS[0][0]);

  const load = useCallback(() => {
    api("/api/festival/flags").then((d) => setFlags(d.flags)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const add = async (e) => {
    e.preventDefault();
    const form = e.target;
    try {
      await api("/api/festival/flags", {
        method: "POST",
        body: { name: new FormData(form).get("name"), color },
      });
      form.reset();
      load();
      onChanged();
    } catch (err) {
      onError(err.message);
    }
  };

  const remove = async (f) => {
    if (!window.confirm(`Delete the “${f.name}” flag? It will be cleared from all submissions.`)) return;
    try {
      await api(`/api/festival/flags/${f.id}`, { method: "DELETE" });
      load();
      onChanged();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Custom flags</h2>
      <p className="muted">Colored labels to organize submissions your way.</p>
      <div className="list-divided">
        {flags.map((f) => (
          <p key={f.id} style={{ margin: 0, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <span>
              <span className="flag-dot" style={{ background: f.color }} /> {f.name}
            </span>
            <button className="btn btn-quiet" onClick={() => remove(f)}>Delete</button>
          </p>
        ))}
      </div>
      <form onSubmit={add}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <select aria-label="Flag color" value={color} onChange={(e) => setColor(e.target.value)}
                  style={{ flex: 1, minWidth: 100 }}>
            {FLAG_COLORS.map(([hex, name]) => (
              <option key={hex} value={hex}>{name}</option>
            ))}
          </select>
          <input name="name" required placeholder="Flag name" style={{ flex: 2, minWidth: 120 }} />
        </div>
        <div className="btn-row">
          <button className="btn btn-secondary" type="submit">Add flag</button>
        </div>
      </form>
    </div>
  );
}

function MessagesCard({ onError }) {
  const [messages, setMessages] = useState([]);
  const [open, setOpen] = useState(false);
  const [audience, setAudience] = useState("submitters");

  const load = useCallback(() => {
    api("/api/festival/messages").then((d) => setMessages(d.messages)).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const send = async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    if (!window.confirm(
      `Send this message to all ${audience}? Each person gets a copy in their notifications.`
    )) return;
    try {
      const res = await api("/api/festival/messages", {
        method: "POST",
        body: { audience, subject: fd.get("subject"), body: fd.get("body") || "" },
      });
      window.alert(`Sent to ${res.recipient_count} recipient${res.recipient_count !== 1 ? "s" : ""}.`);
      form.reset();
      setOpen(false);
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Messages</h2>
      <p className="muted">
        Bulk messages to your submitters or staff — e.g. a notification-date
        delay. Not for selection results; those go out automatically with
        status changes.
      </p>
      {!open ? (
        <div className="btn-row" style={{ marginTop: 0 }}>
          <button className="btn btn-secondary" onClick={() => setOpen(true)}>
            Create a new message
          </button>
        </div>
      ) : (
        <form onSubmit={send}>
          <label htmlFor="audience">Send to</label>
          <select id="audience" value={audience} onChange={(e) => setAudience(e.target.value)}>
            <option value="submitters">All submitters</option>
            <option value="staff">Judges & staff</option>
          </select>
          <label htmlFor="msg-subject">Subject</label>
          <input id="msg-subject" name="subject" required />
          <label htmlFor="msg-body">Message</label>
          <textarea id="msg-body" name="body" />
          <div className="btn-row">
            <button className="btn btn-primary" type="submit">Send message</button>
            <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      )}
      {messages.length > 0 && (
        <div className="list-divided" style={{ marginTop: 8 }}>
          {messages.map((m) => (
            <p key={m.id} style={{ margin: 0 }}>
              <strong>{m.subject}</strong>
              <br />
              <span className="muted" style={{ fontSize: "0.9rem" }}>
                {m.audience === "submitters" ? "All submitters" : "Judges & staff"} ({m.recipient_count})
                {" · "}{new Date(m.created_at).toLocaleDateString()}
              </span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function InsightsCard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api("/api/festival/insights").then(setData).catch(() => {});
  }, []);

  if (!data || data.judges.length === 0) return null;
  const { totals, judges } = data;

  return (
    <div className="card">
      <h2>Judging insights</h2>
      <p className="muted">
        {totals.judged} of {totals.submissions} submissions judged
        ({totals.pct_judged}%) across {totals.judges} judge{totals.judges !== 1 ? "s" : ""}.
      </p>
      <table className="stack">
        <thead>
          <tr><th>Judge</th><th>Judged</th><th>Assigned</th><th>% judged</th><th>Runtime assigned</th></tr>
        </thead>
        <tbody>
          {judges.map((j) => (
            <tr key={j.user_id}>
              <td data-label="Judge"><strong>{j.name}</strong></td>
              <td data-label="Judged">{j.judged}</td>
              <td data-label="Assigned">{j.assigned}</td>
              <td data-label="% judged">{j.pct_judged}%</td>
              <td data-label="Runtime assigned">
                {Math.floor(j.runtime_minutes_assigned / 60)} hr {j.runtime_minutes_assigned % 60} min
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const CODE_TYPE_LABELS = {
  discount: "Discount",
  fee_waiver: "Entry fee waiver",
  deadline_waiver: "Deadline waiver",
};

function codeSummary(c) {
  if (c.code_type === "discount") {
    return c.kind === "percent"
      ? `${c.amount}% off entry fee`
      : `${money(c.amount)} off entry fee`;
  }
  if (c.code_type === "fee_waiver") return "free entry";
  return "late entry allowed";
}

function DiscountsCard({ onError }) {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [codeType, setCodeType] = useState("discount");
  const [kind, setKind] = useState("percent");
  const [uses, setUses] = useState("unlimited");

  const load = useCallback(() => {
    api("/api/festival/codes").then(setData).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const create = async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const body = {
      code: fd.get("code"),
      code_type: codeType,
      label: fd.get("label") || "",
      category_id: fd.get("category_id") ? Number(fd.get("category_id")) : null,
      valid_from: fd.get("valid_from") || null,
      valid_to: fd.get("valid_to") || null,
      redemption_limit: uses === "limited" ? Number(fd.get("max_uses")) || 1 : null,
      one_use_per_submitter: fd.get("one_use_per_submitter") === "on",
      also_deadline_waiver:
        codeType === "discount" && fd.get("also_deadline_waiver") === "on",
    };
    if (codeType === "discount") {
      body.kind = kind;
      body.amount =
        kind === "percent"
          ? Number(fd.get("amount_percent"))
          : Math.round(Number(fd.get("amount_dollars")) * 100);
    }
    try {
      await api("/api/festival/codes", { method: "POST", body });
      form.reset();
      setOpen(false);
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  const remove = async (c) => {
    if (!window.confirm(`Delete the code ${c.code}? Filmmakers won't be able to use it anymore.`)) return;
    try {
      await api(`/api/festival/codes/${c.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      onError(err.message);
    }
  };

  if (!data) return null;

  return (
    <div className="card">
      <h2>Discounts & waivers</h2>
      {data.codes.length === 0 && (
        <p className="muted">No codes yet — create one for partners, outreach, or late entries.</p>
      )}
      <div className="list-divided">
        {data.codes.map((c) => (
          <div key={c.id} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "start" }}>
            <div>
              <span className="tracking-number">{c.code}</span>{" "}
              <span className="tag tag-status">{CODE_TYPE_LABELS[c.code_type]}</span>
              {c.also_deadline_waiver && <span className="tag tag-status"> +deadline waiver</span>}
              <br />
              <span className="muted" style={{ fontSize: "0.9rem" }}>
                {codeSummary(c)}
                {" · "}
                {c.redemptions}/{c.redemption_limit ?? "∞"} used
                {c.one_use_per_submitter && " · one per submitter"}
                {c.valid_to && ` · until ${c.valid_to}`}
                {c.label && ` · ${c.label}`}
              </span>
            </div>
            <button className="btn btn-quiet" onClick={() => remove(c)}>Delete</button>
          </div>
        ))}
      </div>

      {!open ? (
        <div className="btn-row">
          <button className="btn btn-secondary" onClick={() => setOpen(true)}>
            Create a discount or waiver
          </button>
        </div>
      ) : (
        <form onSubmit={create}>
          <label>Code type</label>
          {Object.entries(CODE_TYPE_LABELS).map(([value, text]) => (
            <label key={value} style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400, margin: "4px 0" }}>
              <input
                type="radio"
                name="code_type"
                checked={codeType === value}
                onChange={() => setCodeType(value)}
                style={{ width: "auto", minHeight: "auto" }}
              />
              {text}
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                {value === "discount" && "— discounted entry fees"}
                {value === "fee_waiver" && "— free entry to your festival"}
                {value === "deadline_waiver" && "— entry after your final deadline"}
              </span>
            </label>
          ))}

          <label htmlFor="code">Code</label>
          <input id="code" name="code" required placeholder="e.g. HILLSIDE2026"
                 pattern="[A-Za-z0-9]+" title="Letters and numbers only" />

          <label htmlFor="label">Label (optional, internal only)</label>
          <input id="label" name="label" placeholder="e.g. Film school partnership" />

          {codeType === "discount" && (
            <>
              <label>Discount amount</label>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <select aria-label="Discount kind" value={kind}
                        onChange={(e) => setKind(e.target.value)} style={{ flex: 1, minWidth: 110 }}>
                  <option value="percent">% off</option>
                  <option value="flat">$ off</option>
                </select>
                {kind === "percent" ? (
                  <input name="amount_percent" type="number" min="1" max="100" required
                         placeholder="e.g. 20" style={{ flex: 1, minWidth: 90 }} />
                ) : (
                  <input name="amount_dollars" type="number" min="0.5" step="0.5" required
                         placeholder="e.g. 10.00" style={{ flex: 1, minWidth: 90 }} />
                )}
              </div>
              <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400 }}>
                <input name="also_deadline_waiver" type="checkbox" style={{ width: "auto", minHeight: "auto" }} />
                Allow this code to also function as a deadline waiver
              </label>
            </>
          )}

          <label htmlFor="category_id">Categories</label>
          <select id="category_id" name="category_id">
            <option value="">All categories</option>
            {data.categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name} only</option>
            ))}
          </select>

          <label>Maximum uses</label>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <select aria-label="Maximum uses" value={uses}
                    onChange={(e) => setUses(e.target.value)} style={{ flex: 1, minWidth: 120 }}>
              <option value="unlimited">Unlimited</option>
              <option value="limited">Limit to…</option>
            </select>
            {uses === "limited" && (
              <input name="max_uses" type="number" min="1" required
                     placeholder="e.g. 50" style={{ flex: 1, minWidth: 80 }} />
            )}
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 400 }}>
            <input name="one_use_per_submitter" type="checkbox" style={{ width: "auto", minHeight: "auto" }} />
            Limit code to one use per submitter
          </label>

          <label htmlFor="valid_from">Start date (optional)</label>
          <input id="valid_from" name="valid_from" type="date" />
          <label htmlFor="valid_to">End date (optional)</label>
          <input id="valid_to" name="valid_to" type="date" />

          <div className="btn-row">
            <button className="btn btn-primary" type="submit">Save code</button>
            <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}

function WaiverPeriodCard({ festival, onSaved, onError }) {
  const [days, setDays] = useState(festival.deadline_waiver_days ?? 0);
  const [info, setInfo] = useState(null);

  useEffect(() => {
    api("/api/festival/codes").then(setInfo).catch(() => {});
  }, [festival.deadline_waiver_days]);

  const save = async (e) => {
    e.preventDefault();
    try {
      await api("/api/festival/profile", {
        method: "PATCH",
        body: { deadline_waiver_days: Number(days) || 0 },
      });
      onSaved();
    } catch (err) {
      onError(err.message);
    }
  };

  return (
    <div className="card">
      <h2>Deadline waiver period</h2>
      <p className="muted">
        How many days after your final deadline deadline-waiver codes still
        work. Set to 0 to disallow late entries.
      </p>
      <form onSubmit={save} style={{ display: "flex", gap: 10, alignItems: "end", flexWrap: "wrap" }}>
        <div style={{ width: 110 }}>
          <label htmlFor="waiver-days">Days</label>
          <input id="waiver-days" type="number" min="0" max="90" value={days}
                 onChange={(e) => setDays(e.target.value)} />
        </div>
        <button className="btn btn-secondary" type="submit">Save</button>
      </form>
      {info?.waiver_accepted_through && Number(days) > 0 && (
        <p className="muted" style={{ marginTop: 10 }}>
          Deadline waiver codes will be accepted through{" "}
          <strong>{info.waiver_accepted_through}</strong>.
        </p>
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
          <InsightsCard />

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
          <QueueCard />
          {can_edit_profile && (
            <>
              <ProfileEditor festival={festival} onSaved={load} onError={setError} />
              <StaffCard onError={setError} />
              <RubricCard onError={setError} />
              <QuestionsCard onError={setError} />
              <FlagsCard onError={setError} onChanged={load} />
              <MessagesCard onError={setError} />
              <DiscountsCard onError={setError} />
              <WaiverPeriodCard festival={festival} onSaved={load} onError={setError} />
            </>
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
