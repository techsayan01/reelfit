import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Festivals from "./pages/Festivals.jsx";
import FestivalDetail from "./pages/FestivalDetail.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import FilmNew from "./pages/FilmNew.jsx";
import FilmEdit from "./pages/FilmEdit.jsx";
import FilmScores from "./pages/FilmScores.jsx";
import Submit from "./pages/Submit.jsx";
import Credits from "./pages/Credits.jsx";
import ReviewNew from "./pages/ReviewNew.jsx";
import FestivalDashboard from "./pages/FestivalDashboard.jsx";
import FestivalSubmissionDetail from "./pages/FestivalSubmissionDetail.jsx";
import FilmmakerProfile from "./pages/FilmmakerProfile.jsx";
import ProfileSettings from "./pages/ProfileSettings.jsx";
import Help from "./pages/Help.jsx";

function Protected({ kind, children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="center-note">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (kind && user.kind !== kind) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/help" element={<Help />} />
        <Route path="/festivals" element={<Festivals />} />
        <Route path="/festivals/:slug" element={<FestivalDetail />} />
        <Route path="/f/:handle" element={<FilmmakerProfile />} />
        <Route path="/dashboard" element={<Protected kind="filmmaker"><Dashboard /></Protected>} />
        <Route path="/profile" element={<Protected kind="filmmaker"><ProfileSettings /></Protected>} />
        <Route path="/films/new" element={<Protected kind="filmmaker"><FilmNew /></Protected>} />
        <Route path="/films/:id/edit" element={<Protected kind="filmmaker"><FilmEdit /></Protected>} />
        <Route path="/films/:id/scores" element={<Protected kind="filmmaker"><FilmScores /></Protected>} />
        <Route path="/submit" element={<Protected kind="filmmaker"><Submit /></Protected>} />
        <Route path="/credits" element={<Protected kind="filmmaker"><Credits /></Protected>} />
        <Route path="/reviews/new" element={<Protected kind="filmmaker"><ReviewNew /></Protected>} />
        <Route path="/festival/dashboard" element={<Protected kind="organizer"><FestivalDashboard /></Protected>} />
        <Route path="/festival/submissions/:id" element={<Protected kind="organizer"><FestivalSubmissionDetail /></Protected>} />
        <Route path="*" element={<p className="center-note">Page not found.</p>} />
      </Routes>
    </Layout>
  );
}
