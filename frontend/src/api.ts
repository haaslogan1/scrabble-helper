export type User = { id: number; email: string; name: string; is_admin?: boolean };
export type Player = { id: number; name: string };
export type GameSettings = {
  minutes_per_turn: number;
  input_mode?: string;
  show_live_leaderboard: boolean;
};
export type Standing = {
  player_id: number;
  name: string;
  total_score: number | null;
  turn_order: number;
};
export type GameState = {
  id: number;
  status: string;
  settings: GameSettings;
  current_round: number;
  current_turn_index: number;
  current_player: string | null;
  standings: Standing[];
  played_date?: string | null;
  completed_at?: string | null;
  winner?: string | null;
  players?: Array<{
    player_id: number;
    name: string;
    total_score: number;
    placement: number;
    won: boolean;
    rack_adjustment: number;
  }>;
  rounds?: Array<{
    round_number: number;
    player_id: number;
    score: number;
    play_type: string;
    word?: string | null;
  }>;
};
export type Leaderboard = Record<string, Array<Record<string, string | number>>>;

export class AuthError extends Error {
  constructor(message = "Not authenticated") {
    super(message);
    this.name = "AuthError";
  }
}

function parseApiError(text: string): string {
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      const messages = parsed.detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return "";
        })
        .filter(Boolean);
      if (messages.length) return messages.join(" ");
    }
  } catch {
    /* use raw text */
  }
  return text || "Request failed";
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (res.status === 401) {
    throw new AuthError();
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text) || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type AuthConfig = {
  google_login_enabled: boolean;
  dev_login_enabled: boolean;
  local_auth_enabled: boolean;
  email_verification_enabled: boolean;
};

export const getAuthConfig = () => api<AuthConfig>("/auth/config");

export type RegisterSendCodeResponse = {
  message: string;
  expires_in_minutes: number;
  dev_code?: string;
};

export const sendRegistrationCode = (email: string, password: string, name: string) =>
  api<RegisterSendCodeResponse>("/auth/register/send-code", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });

export const verifyRegistration = (email: string, code: string) =>
  api<User>("/auth/register/verify", {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });

export const register = (email: string, password: string, name: string) =>
  api<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password, name }) });

export const login = (email: string, password: string) =>
  api<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });

export const getMe = () => api<User>("/auth/me");
export const logout = () => api<{ status: string }>("/auth/logout", { method: "POST" });
export const getHome = () => api<{ completed_games: number; in_progress_games: number; saved_players: number }>("/api/home");
export const listPlayers = () => api<Player[]>("/api/players");
export const createPlayer = (name: string) => api<Player>("/api/players", { method: "POST", body: JSON.stringify({ name }) });
export const createGame = (settings: Partial<GameSettings> & Pick<GameSettings, "minutes_per_turn" | "show_live_leaderboard">) =>
  api<{ id: number }>("/api/games", { method: "POST", body: JSON.stringify({ settings }) });
export const setPlayers = (gameId: number, player_ids: number[]) => api<GameState>(`/api/games/${gameId}/players`, { method: "PUT", body: JSON.stringify({ player_ids }) });
export const setTurnOrder = (gameId: number, player_ids: number[]) => api<GameState>(`/api/games/${gameId}/turn-order`, { method: "POST", body: JSON.stringify({ player_ids }) });
export const randomFirst = (gameId: number) => api<GameState>(`/api/games/${gameId}/random-first`, { method: "POST" });
export const beginGame = (gameId: number) => api<GameState>(`/api/games/${gameId}/begin`, { method: "POST" });
export const recordTurn = (gameId: number, body: Record<string, unknown>) => api<GameState>(`/api/games/${gameId}/turns`, { method: "POST", body: JSON.stringify(body) });
export const nextPlayer = (gameId: number) => api<GameState>(`/api/games/${gameId}/next-player`, { method: "POST" });
export const endGame = (gameId: number) => api<GameState>(`/api/games/${gameId}/end`, { method: "POST" });
export const finalizeGame = (gameId: number, rack_adjustments: Record<string, number>) => api<GameState>(`/api/games/${gameId}/finalize`, { method: "POST", body: JSON.stringify({ rack_adjustments }) });
export const getGameState = (gameId: number) => api<GameState>(`/api/games/${gameId}/state`);
export const getGameDetail = (gameId: number) => api<GameState>(`/api/games/${gameId}`);
export const listGames = (status?: string) => api<Array<{ id: number; status: string; played_date: string | null; winner: string | null }>>(`/api/games${status ? `?status=${status}` : ""}`);
export const getLeaderboard = () => api<Leaderboard>("/api/leaderboard");
