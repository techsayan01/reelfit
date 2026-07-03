import { Link } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function Home() {
  const { user } = useAuth();
  return (
    <>
      <div className="hero">
        <h1>See where your film fits — before you pay.</h1>
        <p className="lede">
          Reelfit scores your film against a festival's actual selection
          history, so every submission fee is spent where it counts.
        </p>
        <div className="btn-row">
          {!user && (
            <>
              <Link className="btn btn-primary" to="/register">Score my film</Link>
              <Link className="btn btn-secondary" to="/festivals">Browse festivals</Link>
            </>
          )}
          {user && user.kind === "filmmaker" && (
            <Link className="btn btn-primary" to="/dashboard">Go to my films</Link>
          )}
          {user && user.kind === "organizer" && (
            <Link className="btn btn-primary" to="/festival/dashboard">Go to my festival</Link>
          )}
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <h2>For filmmakers</h2>
          <ul>
            <li>One flat fee scores your film against every listed festival — not per festival.</li>
            <li>
              Every score is labeled <span className="tag tag-validated">validated</span>{" "}
              or <span className="tag tag-calibrating">calibrating</span>, so you always
              know how much to trust it.
            </li>
            <li>
              After your festival run, get plain-language distribution guidance.
              We recommend — we never take rights.
            </li>
          </ul>
        </div>
        <div className="card">
          <h2>For festivals</h2>
          <ul>
            <li>Cut programmer review time with fit scores calibrated to <em>your</em> past selections.</li>
            <li>Submission and conversion analytics the big platforms don't offer.</li>
            <li>Reviews only from verified submitters — with your right of reply on every one.</li>
          </ul>
        </div>
      </div>
    </>
  );
}
