import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../AuthContext.jsx";

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData(e.target);
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: { email: form.get("email"), password: form.get("password") },
      });
      setUser(data.user);
      navigate(data.user.kind === "organizer" ? "/festival/dashboard" : "/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1>Welcome back</h1>
      {error && <p className="form-error">{error}</p>}
      <div className="card form-narrow">
        <form onSubmit={onSubmit}>
          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" required autoComplete="email" />
          <label htmlFor="password">Password</label>
          <input id="password" name="password" type="password" required autoComplete="current-password" />
          <div className="btn-row">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
            <Link className="btn btn-quiet" to="/register">New here? Create an account</Link>
          </div>
        </form>
      </div>
    </>
  );
}
