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

  const { film, festival, edition, tier, categories, waiver_required } = options;
  const chosen = categories.find((c) => c.id === Number(categoryId));

  const onSubmit = async (e) => {
    e.preventDefault();
    const fee = chosen ? money(chosen.fee_cents) : "";
    if (!window.confirm(`Send “${film.title}” to ${festival.name} and pay ${fee}?`)) return;
    setBusy(true);
    setError(null);
    const form = new FormData(e.target);
    try {
      await api("/api/submissions", {
        method: "POST",
        body: {
          film_id: Number(filmId),
          festival_id: Number(festivalId),
          category_id: Number(categoryId),
          discount_code: form.get("discount_code") || "",
          cover_letter: form.get("cover_letter") || "",
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
