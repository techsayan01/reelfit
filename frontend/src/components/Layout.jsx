import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Close the mobile menu on navigation.
  const close = () => setOpen(false);

  const onLogout = async () => {
    await logout();
    close();
    navigate("/");
  };

  return (
    <>
      <header className="site-header">
        <div className="inner">
          <Link className="brand" to="/" onClick={close}>
            Reelfit<span className="dot">.</span>
          </Link>
          <button
            className="nav-toggle"
            aria-expanded={open}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen(!open)}
          >
            ☰
          </button>
          <nav className={`site-nav ${open ? "open" : ""}`} aria-label="Main">
            <Link to="/festivals" onClick={close}>Festivals</Link>
            <Link to="/help" onClick={close}>Help</Link>
            {user && user.kind === "filmmaker" && (
              <>
                <Link to="/dashboard" onClick={close}>My films</Link>
                <Link to="/profile" onClick={close}>My profile</Link>
                <span className="nav-item muted">
                  {user.credit_balance} credit{user.credit_balance !== 1 ? "s" : ""}
                </span>
              </>
            )}
            {user && user.kind === "organizer" && (
              <Link to="/festival/dashboard" onClick={close}>My festival</Link>
            )}
            {user ? (
              <button className="btn btn-quiet" onClick={onLogout}>Sign out</button>
            ) : (
              <>
                <Link to="/login" onClick={close}>Sign in</Link>
                <Link className="btn btn-primary" to="/register" onClick={close}>
                  Get started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="page" key={location.pathname}>{children}</main>
    </>
  );
}
