import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getGameDetail, type GameState } from "../api";

export default function GameDetailPage() {
  const { id } = useParams();
  const [game, setGame] = useState<GameState | null>(null);

  useEffect(() => {
    getGameDetail(Number(id)).then(setGame).catch(() => {});
  }, [id]);

  if (!game) return <p className="loading-state">Loading...</p>;

  return (
    <div>
      <div className="card">
        <h1 className="page-title">Game on {game.played_date}</h1>
        <p>Winner: <strong>{game.winner}</strong></p>
        <Link to="/games" className="back-link muted">← Back to past games</Link>
      </div>
      <div className="card">
        <h2>Final standings</h2>
        <table>
          <thead><tr><th>Place</th><th>Player</th><th>Score</th><th>Rack adj.</th></tr></thead>
          <tbody>
            {(game.players || []).map((p) => (
              <tr key={p.player_id}>
                <td>{p.placement}</td>
                <td>{p.name}</td>
                <td>{p.total_score}</td>
                <td>{p.rack_adjustment}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h2>Turn log</h2>
        <table>
          <thead><tr><th>Round</th><th>Player</th><th>Type</th><th>Score</th><th>Word</th></tr></thead>
          <tbody>
            {(game.rounds || []).map((r, i) => (
              <tr key={i}>
                <td>{r.round_number}</td>
                <td>{(game.players || []).find((p) => p.player_id === r.player_id)?.name}</td>
                <td>{r.play_type}</td>
                <td>{r.score}</td>
                <td>{r.word || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
