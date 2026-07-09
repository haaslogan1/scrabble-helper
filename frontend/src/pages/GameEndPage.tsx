import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { finalizeGame, getGameState } from "../api";
import {
  MAX_RACK_ADJUSTMENT,
  MIN_RACK_ADJUSTMENT,
  validateRackAdjustmentInput,
} from "../scoring";

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
    const rack: Record<string, number> = {};
    for (const player of players) {
      const pid = String(player.player_id);
      const result = validateRackAdjustmentInput(adjustments[pid] ?? "");
      if (!result.ok) {
        setError(`${player.name}: ${result.message}`);
        return;
      }
      rack[pid] = result.adjustment;
    }
    try {
      await finalizeGame(gameId, rack);
      navigate(`/games/${gameId}`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <h1 className="page-title">End game</h1>
      <p className="muted">Enter leftover tile penalty (0 to -70) for each player.</p>
      {players.map((p) => (
        <div key={p.player_id} className="form-field">
          <label>{p.name}</label>
          <input
            type="number"
            min={MIN_RACK_ADJUSTMENT}
            max={MAX_RACK_ADJUSTMENT}
            step={1}
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
