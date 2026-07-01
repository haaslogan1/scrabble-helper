import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { finalizeGame, getGameState } from "../api";

export default function GameEndPage() {
  const { id } = useParams();
  const gameId = Number(id);
  const navigate = useNavigate();
  const [adjustments, setAdjustments] = useState<Record<string, string>>({});
  const [players, setPlayers] = useState<Array<{ player_id: number; name: string }>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getGameState(gameId).then((state) => {
      setPlayers(state.standings.map((s) => ({ player_id: s.player_id, name: s.name })));
    });
  }, [gameId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const rack: Record<string, number> = {};
      for (const [pid, val] of Object.entries(adjustments)) {
        rack[pid] = Number(val) || 0;
      }
      await finalizeGame(gameId, rack);
      navigate(`/games/${gameId}`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <h1 className="page-title">End game</h1>
      <p className="muted">Enter leftover letter penalties (negative numbers) or final adjustments for each player.</p>
      {players.map((p) => (
        <div key={p.player_id} className="form-field">
          <label>{p.name}</label>
          <input
            type="number"
            placeholder="Rack penalty (e.g. -12)"
            value={adjustments[String(p.player_id)] || ""}
            onChange={(e) => setAdjustments((prev) => ({ ...prev, [String(p.player_id)]: e.target.value }))}
          />
        </div>
      ))}
      {error && <p className="error-text">{error}</p>}
      <button className="btn" type="submit">Finalize game</button>
    </form>
  );
}
