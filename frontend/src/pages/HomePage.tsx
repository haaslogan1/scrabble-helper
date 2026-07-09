import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getHome } from "../api";
import { useAuth } from "../auth/AuthContext";
import {
  consumeSessionReplacedMessage,
  sessionReplacedMessageFromDevice,
} from "../auth/sessionReplaced";

export default function HomePage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [summary, setSummary] = useState({ completed_games: 0, in_progress_games: 0, saved_players: 0 });
  const [sessionInfo, setSessionInfo] = useState<string | null>(null);

  useEffect(() => {
    getHome().then(setSummary).catch(() => {});
  }, []);

  useEffect(() => {
    const stored = consumeSessionReplacedMessage();
    if (stored) {
      setSessionInfo(stored);
      return;
    }
    if (searchParams.get("session_replaced") === "1") {
      const device = searchParams.get("device") as "mobile" | "tablet" | "computer" | null;
      setSessionInfo(sessionReplacedMessageFromDevice(device));
      const next = new URLSearchParams(searchParams);
      next.delete("session_replaced");
      next.delete("device");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  return (
    <div className="hero">
      <h1>Welcome, {user?.name}</h1>
      <p className="muted">End-to-end Scrabble scorekeeping and analytics.</p>
      {sessionInfo && <p className="muted">{sessionInfo}</p>}
      <div className="tile-grid">
        <Link className="card card--link" to="/game/new">
          <h2>Start Game</h2>
          <p>Configure settings, pick players, and begin.</p>
        </Link>
        <Link className="card card--link" to="/games">
          <h2>Review Past Games</h2>
          <p>{summary.completed_games} completed games</p>
        </Link>
        <Link className="card card--link" to="/leaderboard">
          <h2>Scrabble Leaderboard</h2>
          <p>{summary.saved_players} saved players</p>
        </Link>
        <Link className="card card--link" to="/friends">
          <h2>Find Friends</h2>
          <p>Add friends and play live together</p>
        </Link>
      </div>
    </div>
  );
}
