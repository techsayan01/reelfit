import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, money } from "../api.js";
import { useAuth } from "../AuthContext.jsx";

export default function Credits() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [packs, setPacks] = useState([]);
  const [error, setError] = useState(null);
  const needed = params.get("needed");

  useEffect(() => {
    api("/api/credits/packs").then((d) => setPacks(d.packs));
  }, []);

  const buy = async (pack) => {
    if (!window.confirm(`Buy the ${pack.label} for ${money(pack.price_cents)}?`)) return;
    try {
      await api("/api/credits/buy", { method: "POST", body: { pack: pack.id } });
      await refresh();
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <h1>Scoring credits</h1>
      {needed && (
        <p className="form-error">You're out of credits — you'll need one to score a film.</p>
      )}
      {error && <p className="form-error">{error}</p>}
      <p>
        One credit scores one film against <strong>every</strong> listed
        festival — one flat fee, not a fee per festival.
      </p>
      <div className="card-grid">
        {packs.map((pack) => (
          <div className="card" key={pack.id}>
            <h2>{pack.label}</h2>
            <p className="display" style={{ fontSize: "2rem", margin: "4px 0" }}>
              {money(pack.price_cents)}
            </p>
            <p className="muted">
              {pack.credits} credit{pack.credits !== 1 ? "s" : ""}
            </p>
            <button className="btn btn-primary" onClick={() => buy(pack)}>
              Buy {pack.label.toLowerCase()}
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
