import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import GuestRoute from "./auth/GuestRoute";
import SiteHeader from "./components/SiteHeader";
import FeedbackButton from "./components/FeedbackButton";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import SettingsPage from "./pages/SettingsPage";
import GameSettingsPage from "./pages/GameSettingsPage";
import GamePlayersPage from "./pages/GamePlayersPage";
import GameOrderPage from "./pages/GameOrderPage";
import GamePlayPage from "./pages/GamePlayPage";
import GameEndPage from "./pages/GameEndPage";
import RulesPage from "./pages/RulesPage";
import GamesListPage from "./pages/GamesListPage";
import GameDetailPage from "./pages/GameDetailPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import FindFriendsPage from "./pages/FindFriendsPage";
import { ThemeProvider } from "./theme/ThemeContext";

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteHeader />
      <main className="container app-main">{children}</main>
      <FeedbackButton />
    </>
  );
}

function NavigateToLoginOrHome() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-state">Loading…</div>;
  return <Navigate to={user ? "/" : "/login"} replace />;
}

function ProtectedShell({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />
      <Route path="/" element={<ProtectedShell><HomePage /></ProtectedShell>} />
      <Route path="/settings" element={<ProtectedShell><SettingsPage /></ProtectedShell>} />
      <Route path="/game/new" element={<ProtectedShell><GameSettingsPage /></ProtectedShell>} />
      <Route path="/game/rules" element={<ProtectedShell><RulesPage /></ProtectedShell>} />
      <Route path="/game/:id/players" element={<ProtectedShell><GamePlayersPage /></ProtectedShell>} />
      <Route path="/game/:id/order" element={<ProtectedShell><GameOrderPage /></ProtectedShell>} />
      <Route path="/game/:id/play" element={<ProtectedShell><GamePlayPage /></ProtectedShell>} />
      <Route path="/game/:id/end" element={<ProtectedShell><GameEndPage /></ProtectedShell>} />
      <Route path="/games" element={<ProtectedShell><GamesListPage /></ProtectedShell>} />
      <Route path="/games/:id" element={<ProtectedShell><GameDetailPage /></ProtectedShell>} />
      <Route path="/leaderboard" element={<ProtectedShell><LeaderboardPage /></ProtectedShell>} />
      <Route path="/friends" element={<ProtectedShell><FindFriendsPage /></ProtectedShell>} />
      <Route path="*" element={<NavigateToLoginOrHome />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  );
}
