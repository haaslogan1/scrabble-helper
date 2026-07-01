import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { beginGame, getGameState, randomFirst, setTurnOrder } from "../api";

export default function GameOrderPage() {
  const { id } = useParams();
  const gameId = Number(id);
  const navigate = useNavigate();
  const [order, setOrder] = useState<number[]>([]);
  const [names, setNames] = useState<Record<number, string>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    getGameState(gameId).then((state) => {
      const sorted = [...state.standings].sort((a, b) => a.turn_order - b.turn_order);
      setOrder(sorted.map((s) => s.player_id));
      setNames(Object.fromEntries(sorted.map((s) => [s.player_id, s.name])));
    });
  }, [gameId]);

  function move(idx: number, dir: -1 | 1) {
    const next = [...order];
    const target = idx + dir;
    if (target < 0 || target >= next.length) return;
    [next[idx], next[target]] = [next[target], next[idx]];
    setOrder(next);
  }

  async function onRandom() {
    const state = await randomFirst(gameId);
    const sorted = [...state.standings].sort((a, b) => a.turn_order - b.turn_order);
    setOrder(sorted.map((s) => s.player_id));
  }

  async function onBegin() {
    setError("");
    try {
      await setTurnOrder(gameId, order);
      await beginGame(gameId);
      navigate(`/game/${gameId}/play`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="card">
      <h1>Turn order</h1>
      <p className="muted">Randomize first player, then adjust order if needed.</p>
      <button type="button" className="btn secondary" onClick={onRandom}>Random first player</button>
      <ol>
        {order.map((pid, idx) => (
          <li key={pid} style={{ margin: ".5rem 0" }}>
            {names[pid]}
            <button type="button" className="btn secondary" style={{ marginLeft: ".5rem" }} onClick={() => move(idx, -1)}>Up</button>
            <button type="button" className="btn secondary" style={{ marginLeft: ".5rem" }} onClick={() => move(idx, 1)}>Down</button>
          </li>
        ))}
      </ol>
      {error && <p>{error}</p>}
      <button className="btn" onClick={onBegin}>Begin game</button>
    </div>
  );
}
