import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../AuthContext.jsx";
import CalibrationTag from "../components/CalibrationTag.jsx";
import ScoreDial from "../components/ScoreDial.jsx";

export default function FilmScores() {
  const { id } = useParams();
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api(`/api/films/${id}/scores`).then(setData).catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  const scoreNow = async () => {
    if (!window.confirm(
      `Score “${data.film.title}” against every listed festival? This uses 1 scoring credit.`
    )) return;
    try {
      await api(`/api/films/${id}/score`, { method: "POST" });
      await refresh();
      load();
    } catch (err) {
      if (err.status === 402) navigate("/credits?needed=1");
      else setError(err.message);
    }
  };

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p className="center-note">Loading…</p>;

  const { film, scores, guidance } = data;

  return (
    <>
      <h1>Where “{film.title}” fits</h1>
      <p className="muted">{film.genre} · {film.runtime_minutes} min · {film.year}</p>

      {scores.length > 0 ? (
        <div className="card">
          <p className="muted">
            Scores estimate how closely your film matches what each festival has
            actually selected before. A lower number isn't a failure — it's
            information that saves you a fee.
          </p>
          {scores.map((row) => (
            <div className="dial-row" key={row.festival.id}>
              <ScoreDial score={row.score} calibration={row.calibration_status} />
              <div className="dial-info">
                <h3 style={{ margin: 0 }}>
                  <Link to={`/festivals/${row.festival.slug}`}>{row.festival.name}</Link>{" "}
                  <CalibrationTag status={row.calibration_status} />
                </h3>
                <p className="muted" style={{ margin: "4px 0 10px" }}>
                  Confidence: {Math.round(row.confidence * 100)}%
                </p>
                <Link
                  className="btn btn-primary"
                  to={`/submit?film=${film.id}&festival=${row.festival.id}`}
                >
                  Send your film
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <p>This film hasn't been scored yet.</p>
          <button className="btn btn-primary" onClick={scoreNow}>
            Score this film (1 credit)
          </button>
        </div>
      )}

      <div className="card">
        <h2>After the festivals: distribution guidance</h2>
        <p className="muted">
          Realistic next steps for a film like yours. Reelfit recommends — we
          never act as a distributor or take rights.
        </p>
        <div className="list-divided">
          {guidance.map((g) => (
            <div key={g.path}>
              <h3 style={{ margin: "0 0 6px" }}>{g.title}</h3>
              <p style={{ margin: 0 }}>{g.rationale}</p>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
