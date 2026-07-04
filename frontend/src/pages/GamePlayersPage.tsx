import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createPlayer, listPlayers, setPlayers, type Player } from "../api";

export default function GamePlayersPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const gameId = Number(id);
  const [players, setPlayersList] = useState<Player[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");

  const selfPlayer = players.find((p) => p.is_self);
  const opponents = players.filter((p) => !p.is_self);

  useEffect(() => {
    listPlayers().then((list) => {
      setPlayersList(list);
      setSelected(
        list.filter((p) => p.is_friend && !p.is_self).map((p) => p.id),
      );
    }).catch(() => {});
  }, []);

  function toggle(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function addNew() {
    if (!newName.trim()) return;
    const p = await createPlayer(newName.trim());
    setPlayersList((prev) => [...prev, p]);
    setSelected((prev) => [...prev, p.id]);
    setNewName("");
  }

  async function onContinue() {
    setError("");
    try {
      await setPlayers(gameId, selected);
      navigate(`/game/${gameId}/order`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="card">
      <h1 className="page-title">Select players</h1>
      <p className="muted">You are always playing. Choose opponents or add new ones. Friends are pre-selected.</p>
      {selfPlayer && (
        <p className="owner-player-row">
          <strong>You ({selfPlayer.name})</strong> - always playing
        </p>
      )}
      {opponents.map((p) => (
        <label key={p.id} className="checkbox-label">
          <input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggle(p.id)} />
          {p.name}
          {p.is_friend && <span className="tag tag--ok"> Friend</span>}
          {p.is_friend && p.mutual === false && (
            <span className="tag tag--warn"> Needs to add you back for live play</span>
          )}
        </label>
      ))}
      <div className="inline-form">
        <input placeholder="New player name" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="button" className="btn secondary" onClick={addNew}>Add</button>
      </div>
      {error && <p className="error-text">{error}</p>}
      <p><button className="btn" disabled={selected.length < 1} onClick={onContinue}>Next: Turn order</button></p>
    </div>
  );
}
