import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api.js";

const RATINGS = [
  [5, "★★★★★ Excellent"],
  [4, "★★★★☆ Good"],
  [3, "★★★☆☆ Fair"],
  [2, "★★☆☆☆ Poor"],
  [1, "★☆☆☆☆ Very poor"],
];

export default function ReviewNew() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const submissionId = Number(params.get("submission"));
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.target);
    try {
      await api("/api/reviews", {
        method: "POST",
        body: {
          submission_id: submissionId,
          rating: Number(form.get("rating")),
          text: form.get("text") || "",
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
      <h1>Review this festival</h1>
      <p className="muted">
        Your review is tied to your real submission and will be visible to
        other filmmakers. The festival can reply publicly.
      </p>
      {error && <p className="form-error">{error}</p>}
      <div className="card form-narrow">
        <form onSubmit={onSubmit}>
          <label htmlFor="rating">Rating</label>
          <select id="rating" name="rating" required>
            {RATINGS.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <label htmlFor="text">Your experience</label>
          <textarea
            id="text"
            name="text"
            placeholder="How was communication, judging transparency, the event itself?"
          />
          <div className="btn-row">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Publishing…" : "Publish review"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
