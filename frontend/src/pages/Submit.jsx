import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, money } from "../api.js";

export default function Submit() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const filmId = params.get("film");
  const festivalId = params.get("festival");
  const [options, setOptions] = useState(null);
  const [categoryId, setCategoryId] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api(`/api/submissions/options?film=${filmId}&festival=${festivalId}`)
      .then((d) => {
        setOptions(d);
        if (d.categories.length > 0) setCategoryId(d.categories[0].id);
      })
      .catch((e) => setError(e.message));
  }, [filmId, festivalId]);

  if (error && !options) return <p className="form-error">{error}</p>;
  if (!options) return <p className="center-note">Loading…</p>;

  const {
    film, festival, edition, tier, categories, waiver_required,
    questions = [],
  } = options;
  const applicableQuestions = questions.filter(
    (q) => q.category_id === null || q.category_id === Number(categoryId)
  );
  const chosen = categories.find((c) => c.id === Number(categoryId));

  const onSubmit = async (e) => {
    e.preventDefault();
    const fee = chosen ? money(chosen.fee_cents) : "";
    if (!window.confirm(`Send “${film.title}” to ${festival.name} and pay ${fee}?`)) return;
    setBusy(true);
    setError(null);
    const form = new FormData(e.target);
    const answers = {};
    for (const q of applicableQuestions) {
      answers[q.id] = form.get(`q${q.id}`) || "";
    }
    try {
      await api("/api/submissions", {
        method: "POST",
        body: {
          film_id: Number(filmId),
          festival_id: Number(festivalId),
          category_id: Number(categoryId),
          discount_code: form.get("discount_code") || "",
          cover_letter: form.get("cover_letter") || "",
          answers,
          source: sessionStorage.getItem("reelfit_ref") || "direct",
        },
      });
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <>
      <h1>Send “{film.title}” to {festival.name}</h1>
      {error && <p className="form-error">{error}</p>}

      {!edition && (
        <div className="card"><p>{festival.name} isn't open for submissions right now.</p></div>
      )}
      {edition && categories.length === 0 && (
        <div className="card">
          <p>
            None of this festival's categories fit your film's runtime or
            production year. That's worth knowing before paying a fee.
          </p>
        </div>
      )}
      {edition && categories.length > 0 && (
        <div className="card form-narrow">
          {waiver_required && (
            <div className="confirm-note">
              {festival.name}'s final deadline has passed. Late entries are
              accepted for a short window — you'll need a <strong>deadline
              waiver code</strong> from the festival to submit.
            </div>
          )}
          <form onSubmit={onSubmit}>
            <label htmlFor="category_id">Category</label>
            <select
              id="category_id"
              value={categoryId ?? ""}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} — {money(c.fee_cents)}
                </option>
              ))}
            </select>
            {tier && (
              <p className="muted">Current deadline tier: {tier.name} (until {tier.deadline})</p>
            )}

            <label htmlFor="discount_code">Promo code (optional)</label>
            <input id="discount_code" name="discount_code" placeholder="e.g. EARLYBIRD" />

            {applicableQuestions.length > 0 && (
              <>
                <h3 style={{ marginTop: 24 }}>A few questions from {festival.name}</h3>
                {applicableQuestions.map((q) => (
                  <div key={q.id}>
                    <label htmlFor={`q${q.id}`}>{q.question}</label>
                    {q.field_type === "text" && (
                      <input id={`q${q.id}`} name={`q${q.id}`} required />
                    )}
                    {q.field_type === "paragraph" && (
                      <textarea id={`q${q.id}`} name={`q${q.id}`} required />
                    )}
                    {q.field_type === "dropdown" && (
                      <select id={`q${q.id}`} name={`q${q.id}`} required defaultValue="">
                        <option value="" disabled>Choose…</option>
                        {q.options.map((o) => (
                          <option key={o} value={o}>{o}</option>
                        ))}
                      </select>
                    )}
                    {q.field_type === "yes_no" && (
                      <select id={`q${q.id}`} name={`q${q.id}`} required defaultValue="">
                        <option value="" disabled>Choose…</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                      </select>
                    )}
                  </div>
                ))}
              </>
            )}

            <label htmlFor="cover_letter">Cover letter (optional)</label>
            <textarea
              id="cover_letter"
              name="cover_letter"
              placeholder="A short message to this festival's programmers."
            />

            <div className="confirm-note">
              This is a paid submission. The fee shown for your chosen category
              will be charged when you confirm. The festival will only be able
              to contact you through your Reelfit relay address — you can revoke
              it at any time.
            </div>

            <div className="btn-row">
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "Sending…" : `Confirm & send film${chosen ? ` (${money(chosen.fee_cents)})` : ""}`}
              </button>
              <Link className="btn btn-quiet" to={`/films/${filmId}/scores`}>Back to scores</Link>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
