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

  useEffect(() => {
    listPlayers().then(setPlayersList).catch(() => {});
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
      setError(String(err));
    }
  }

  return (
    <div className="card">
      <h1>Select players</h1>
      <p className="muted">Choose saved players or add new ones.</p>
      {players.map((p) => (
        <label key={p.id} style={{ display: "block", marginBottom: ".5rem" }}>
          <input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggle(p.id)} /> {p.name}
        </label>
      ))}
      <div style={{ display: "flex", gap: ".5rem", marginTop: "1rem" }}>
        <input placeholder="New player name" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="button" className="btn secondary" onClick={addNew}>Add</button>
      </div>
      {error && <p>{error}</p>}
      <p><button className="btn" disabled={selected.length < 2} onClick={onContinue}>Next: Turn order</button></p>
    </div>
  );
}
