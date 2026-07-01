import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createGame } from "../api";

export default function GameSettingsPage() {
  const navigate = useNavigate();
  const [minutes, setMinutes] = useState(3);
  const [inputMode, setInputMode] = useState("points");
  const [showBoard, setShowBoard] = useState(true);
  const [error, setError] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const game = await createGame({
        minutes_per_turn: minutes,
        input_mode: inputMode,
        show_live_leaderboard: showBoard,
      });
      navigate(`/game/${game.id}/players`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <h1>Game settings</h1>
      <label>Minutes per turn</label>
      <input type="number" min={1} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} />
      <label>Input mode</label>
      <select value={inputMode} onChange={(e) => setInputMode(e.target.value)}>
        <option value="points">Points per turn</option>
        <option value="words">Words (auto-scored)</option>
      </select>
      <label>
        <input type="checkbox" checked={showBoard} onChange={(e) => setShowBoard(e.target.checked)} /> Show live leaderboard during game
      </label>
      {error && <p>{error}</p>}
      <p><button className="btn" type="submit">Next: Players</button></p>
    </form>
  );
}
