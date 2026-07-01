import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listGames } from "../api";

export default function GamesListPage() {
  const [games, setGames] = useState<Array<{ id: number; played_date: string | null; winner: string | null }>>([]);

  useEffect(() => {
    listGames("completed").then(setGames).catch(() => {});
  }, []);

  return (
    <div>
      <div className="card">
        <h1>Past games</h1>
        <Link to="/">← Home</Link>
      </div>
      {games.map((g) => (
        <Link key={g.id} className="card" to={`/games/${g.id}`} style={{ display: "block" }}>
          <strong>{g.played_date || "Unknown date"}</strong>
          <div className="muted">Winner: {g.winner || "—"}</div>
        </Link>
      ))}
      {!games.length && <p className="muted">No completed games yet.</p>}
    </div>
  );
}
