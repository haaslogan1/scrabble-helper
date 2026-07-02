import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { endGame, gameWatchUrl, getGameState, recordTurn, type GameState } from "../api";
import { validateTurnPointsInput } from "../turnPoints";

export default function GamePlayPage() {
  const { id } = useParams();
  const gameId = Number(id);
  const navigate = useNavigate();
  const [state, setState] = useState<GameState | null>(null);
  const [points, setPoints] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const timerRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<number | null>(null);

  function load() {
    getGameState(gameId).then(setState).catch(() => {});
  }

  useEffect(() => {
    load();
    const wsUrl = gameWatchUrl(gameId);
    let closed = false;

    function startPolling() {
      if (pollRef.current) return;
      pollRef.current = window.setInterval(load, 3000);
    }

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onmessage = (event) => {
        try {
          const next = JSON.parse(event.data) as GameState;
          setState((prev) => ({ ...next, role: prev?.role ?? next.role }));
        } catch {
          /* ignore */
        }
      };
      ws.onerror = () => {
        ws.close();
        startPolling();
      };
      ws.onclose = () => {
        if (!closed) startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      closed = true;
      wsRef.current?.close();
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [gameId]);

  useEffect(() => {
    if (!state || state.role === "spectator") return;
    setElapsed(0);
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => { if (timerRef.current) window.clearInterval(timerRef.current); };
  }, [state?.current_player, state?.current_round, state?.role]);

  if (!state) return <p className="loading-state">Loading...</p>;
  if (state.status === "ending") {
    navigate(`/game/${gameId}/end`);
    return null;
  }
  if (state.status === "completed") {
    navigate(`/games/${gameId}`);
    return null;
  }

  const isSpectator = state.role === "spectator";
  const limit = (state.settings.minutes_per_turn || 3) * 60;

  async function submitTurn(playType: string) {
    if (submitting || isSpectator) return;
    setError(null);

    let validatedPoints: number | undefined;
    if (playType === "score") {
      const check = validateTurnPointsInput(points);
      if (!check.ok) {
        setError(check.message);
        return;
      }
      validatedPoints = check.points;
    }

    setSubmitting(true);
    const body: Record<string, unknown> = {
      play_type: playType,
      timer_elapsed_sec: elapsed,
    };
    if (playType === "score") {
      body.points = validatedPoints;
    }
    try {
      const next = await recordTurn(gameId, body);
      setState(next);
      setPoints("");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to submit turn";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  function onInputKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      submitTurn("score");
    }
  }

  async function onEnd() {
    await endGame(gameId);
    navigate(`/game/${gameId}/end`);
  }

  return (
    <div>
      {isSpectator && (
        <div className="card banner banner--info">
          <strong>Watching live</strong> — scores update automatically.
        </div>
      )}
      <div className="card">
        <h1 className="page-title">Round {state.current_round}</h1>
        <p>Current player: <strong>{state.current_player}</strong></p>
        {!isSpectator && (
          <>
            <div className="timer">
              {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")} / {state.settings.minutes_per_turn}:00
            </div>
            {elapsed > limit && <p className="muted">Time exceeded — continue when ready.</p>}
            <input
              className="input"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              placeholder="Points (1–1786)"
              value={points}
              onChange={(e) => setPoints(e.target.value)}
              onKeyDown={onInputKeyDown}
              autoFocus
            />
            {error && <p className="error-text">{error}</p>}
            <div className="btn-row">
              <button className="btn" disabled={submitting} onClick={() => submitTurn("score")}>Submit turn</button>
              <button className="btn secondary" disabled={submitting} onClick={() => submitTurn("challenge")}>Lost challenge</button>
              <button className="btn secondary" disabled={submitting} onClick={() => submitTurn("skip")}>Skip turn</button>
              <button className="btn secondary" onClick={onEnd}>End game</button>
            </div>
          </>
        )}
      </div>
      {state.settings.show_live_leaderboard && (
        <div className="card">
          <h2>Standings</h2>
          <table>
            <thead><tr><th>Player</th><th>Score</th></tr></thead>
            <tbody>
              {state.standings.map((s) => (
                <tr key={s.player_id}><td>{s.name}</td><td>{s.total_score ?? "—"}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
