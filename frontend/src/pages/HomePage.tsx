import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHome } from "../api";
import { useAuth } from "../auth/AuthContext";

export default function HomePage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState({ completed_games: 0, in_progress_games: 0, saved_players: 0 });

  useEffect(() => {
    getHome().then(setSummary).catch(() => {});
  }, []);

  return (
    <div className="hero">
      <h1>Welcome, {user?.name}</h1>
      <p className="muted">End-to-end Scrabble scorekeeping and analytics.</p>
      <div className="grid grid-3">
        <Link className="card" to="/game/new">
          <h2>Start Game</h2>
          <p>Configure settings, pick players, and begin.</p>
        </Link>
        <Link className="card" to="/games">
          <h2>Review Past Games</h2>
          <p>{summary.completed_games} completed games</p>
        </Link>
        <Link className="card" to="/leaderboard">
          <h2>Scrabble Leaderboard</h2>
          <p>{summary.saved_players} saved players</p>
        </Link>
      </div>
    </div>
  );
}
