import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { abandonGame, getHome, listParticipatingGames, type ParticipatingGame } from "../api";
import { useAuth } from "../auth/AuthContext";
import {
  consumeSessionReplacedMessage,
  sessionReplacedMessageFromDevice,
} from "../auth/sessionReplaced";

export default function HomePage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sessionReplacedInfo, setSessionReplacedInfo] = useState<string | null>(null);
  const [summary, setSummary] = useState({
    completed_games: 0,
    in_progress_games: 0,
    participating_in_progress_games: 0,
    saved_players: 0,
  });
  const [participating, setParticipating] = useState<ParticipatingGame[]>([]);
  const [abandonError, setAbandonError] = useState("");

  useEffect(() => {
    const stored = consumeSessionReplacedMessage();
    if (stored) {
      setSessionReplacedInfo(stored);
      return;
    }
    if (searchParams.get("session_replaced") !== "1") return;
    const device = searchParams.get("device") as "mobile" | "tablet" | "computer" | null;
    setSessionReplacedInfo(sessionReplacedMessageFromDevice(device));
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    getHome().then(setSummary).catch(() => {});
    listParticipatingGames("active,ending").then(setParticipating).catch(() => {});
  }, []);

  async function handleAbandon(gameId: number) {
    setAbandonError("");
    try {
      await abandonGame(gameId);
      setParticipating((prev) => prev.filter((g) => g.id !== gameId));
      const home = await getHome();
      setSummary(home);
    } catch (err) {
      setAbandonError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="hero">
      {sessionReplacedInfo && <p className="muted session-replaced-banner">{sessionReplacedInfo}</p>}
      <h1>Welcome, {user?.name}</h1>
      <p className="muted">End-to-end Scrabble scorekeeping and analytics.</p>
      {participating.length > 0 && (
        <div className="card participating-banner">
          <h2>Unfinished live games</h2>
          {participating.map((game) => (
            <p key={game.id}>
              You have an unfinished live game with {game.owner_name}.{" "}
              <Link to={game.resume_url}>Resume</Link>
              {game.can_abandon && (
                <>
                  {" "}
                  or{" "}
                  <button
                    type="button"
                    className="btn-link"
                    onClick={() => handleAbandon(game.id)}
                  >
                    Abandon
                  </button>
                </>
              )}
            </p>
          ))}
          {abandonError && <p className="error-text">{abandonError}</p>}
        </div>
      )}
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
