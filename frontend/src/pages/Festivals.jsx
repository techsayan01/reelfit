import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import CalibrationTag from "../components/CalibrationTag.jsx";

export default function Festivals() {
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState(null);
  const q = params.get("q") || "";

  useEffect(() => {
    api(`/api/festivals?q=${encodeURIComponent(q)}`).then((d) => setRows(d.festivals));
  }, [q]);

  const onSearch = (e) => {
    e.preventDefault();
    setParams({ q: new FormData(e.target).get("q") });
  };

  return (
    <>
      <h1>Festivals</h1>
      <p className="muted">A curated list — every festival here has a real selection process.</p>

      <form onSubmit={onSearch} style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap", margin: "20px 0" }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <label htmlFor="q">Search by name</label>
          <input id="q" name="q" defaultValue={q} placeholder="e.g. Hillside" />
        </div>
        <button className="btn btn-secondary" type="submit">Search</button>
      </form>

      {rows === null && <p className="center-note">Loading festivals…</p>}
      {rows && rows.length === 0 && <p>No festivals match that search.</p>}
      {rows &&
        rows.map(({ festival, edition, tier }) => (
          <div className="card" key={festival.id}>
            <h2>
              <Link to={`/festivals/${festival.slug}`}>{festival.name}</Link>{" "}
              <CalibrationTag status={festival.calibration_status} />
            </h2>
            <p>{festival.description || "No description yet."}</p>
            {edition ? (
              <p className="muted">
                {edition.label} edition — open until {edition.closes_on}
                {tier && <> · current deadline: {tier.name} ({tier.deadline})</>}
              </p>
            ) : (
              <p className="muted">Not currently open for submissions.</p>
            )}
          </div>
        ))}
    </>
  );
}
