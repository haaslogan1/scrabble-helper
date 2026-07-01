import { Link, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import GuestRoute from "./auth/GuestRoute";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import GameSettingsPage from "./pages/GameSettingsPage";
import GamePlayersPage from "./pages/GamePlayersPage";
import GameOrderPage from "./pages/GameOrderPage";
import GamePlayPage from "./pages/GamePlayPage";
import GameEndPage from "./pages/GameEndPage";
import GamesListPage from "./pages/GamesListPage";
import GameDetailPage from "./pages/GameDetailPage";
import LeaderboardPage from "./pages/LeaderboardPage";

function NavBar() {
  const { user, logout } = useAuth();

  return (
    <nav className="nav">
      {user ? (
        <>
          <Link to="/">Scrabble Helper</Link>
          <span className="muted" style={{ flex: 1 }}>{user.name}</span>
          <button type="button" className="btn secondary" onClick={() => logout()}>
            Sign out
          </button>
        </>
      ) : (
        <Link to="/login">Scrabble Helper</Link>
      )}
    </nav>
  );
}

function NavigateToLoginOrHome() {
  const { user, loading } = useAuth();
  if (loading) return <div className="card"><p>Loading…</p></div>;
  return <Navigate to={user ? "/" : "/login"} replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
      <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
      <Route path="/game/new" element={<ProtectedRoute><GameSettingsPage /></ProtectedRoute>} />
      <Route path="/game/:id/players" element={<ProtectedRoute><GamePlayersPage /></ProtectedRoute>} />
      <Route path="/game/:id/order" element={<ProtectedRoute><GameOrderPage /></ProtectedRoute>} />
      <Route path="/game/:id/play" element={<ProtectedRoute><GamePlayPage /></ProtectedRoute>} />
      <Route path="/game/:id/end" element={<ProtectedRoute><GameEndPage /></ProtectedRoute>} />
      <Route path="/games" element={<ProtectedRoute><GamesListPage /></ProtectedRoute>} />
      <Route path="/games/:id" element={<ProtectedRoute><GameDetailPage /></ProtectedRoute>} />
      <Route path="/leaderboard" element={<ProtectedRoute><LeaderboardPage /></ProtectedRoute>} />
      <Route path="*" element={<NavigateToLoginOrHome />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <div className="container">
        <NavBar />
        <AppRoutes />
      </div>
    </AuthProvider>
  );
}
