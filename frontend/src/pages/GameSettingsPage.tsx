import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createGame } from "../api";

export default function GameSettingsPage() {
  const navigate = useNavigate();
  const [minutes, setMinutes] = useState(3);
  const [showBoard, setShowBoard] = useState(true);
  const [error, setError] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const game = await createGame({
        minutes_per_turn: minutes,
        show_live_leaderboard: showBoard,
      });
      navigate(`/game/${game.id}/players`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <h1 className="page-title">Game settings</h1>
      <div className="form-field">
        <label>Minutes per turn</label>
        <input type="number" min={1} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} />
      </div>
      <label className="checkbox-label">
        <input type="checkbox" checked={showBoard} onChange={(e) => setShowBoard(e.target.checked)} />
        Show live leaderboard during game
      </label>
      {error && <p className="error-text">{error}</p>}
      <p><button className="btn" type="submit">Next: Players</button></p>
    </form>
  );
}
