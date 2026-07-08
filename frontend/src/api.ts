export type User = {
  id: number;
  email: string;
  name: string;
  username?: string | null;
  is_admin?: boolean;
  avatar_url?: string | null;
  has_custom_avatar?: boolean;
  provider?: string;
};
export type Player = {
  id: number;
  name: string;
  linked_user_id?: number | null;
  is_friend?: boolean;
  mutual?: boolean | null;
  is_self?: boolean;
};
export type Friend = {
  id: number;
  username: string | null;
  name: string;
  mutual: boolean;
  avatar_url?: string | null;
};
export type FriendSendResult = {
  id: number;
  username: string | null;
  name: string;
  request_id?: number;
  status: string;
  mutual?: boolean | null;
};
export type FriendRequest = {
  id: number;
  from_user: UserSearchResult;
  created_at: string;
};
export type Notification = {
  id: number;
  type: string;
  title: string;
  body: string;
  payload: Record<string, number | string>;
  read: boolean;
  created_at: string;
};
export type NotificationList = {
  notifications: Notification[];
  unread_count: number;
};
export type UserSearchResult = {
  id: number;
  username: string | null;
  name: string;
  reason?: string;
  avatar_url?: string | null;
};
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
  role?: "owner" | "spectator";
  settings: GameSettings;
  current_round: number;
  current_turn_index: number;
  current_player: string | null;
  standings: Standing[];
  played_date?: string | null;
  completed_at?: string | null;
  last_activity_at?: string | null;
  inactivity_warning?: boolean;
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
export type LeaderboardScope = "all" | "friends" | "manual";
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
export const updateUsername = (username: string) =>
  api<User>("/api/me", { method: "PATCH", body: JSON.stringify({ username }) });

export type GamePhoto = {
  id: number;
  url: string;
  caption?: string | null;
  context: string;
  created_at: string;
  uploaded_by_name: string;
};

async function uploadMultipart<T>(path: string, file: File, fields?: Record<string, string>): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  if (fields) {
    for (const [key, value] of Object.entries(fields)) {
      if (value) form.append(key, value);
    }
  }
  const res = await fetch(path, { method: "POST", credentials: "include", body: form });
  if (res.status === 401) throw new AuthError();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text) || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const uploadGamePhoto = (
  gameId: number,
  file: File,
  meta?: { caption?: string; context?: string },
) =>
  uploadMultipart<GamePhoto>(`/api/games/${gameId}/photos`, file, {
    caption: meta?.caption ?? "",
    context: meta?.context ?? "",
  });

export const listGamePhotos = (gameId: number) => api<GamePhoto[]>(`/api/games/${gameId}/photos`);

export async function deleteGamePhoto(gameId: number, photoId: number): Promise<void> {
  const res = await fetch(`/api/games/${gameId}/photos/${photoId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (res.status === 401) throw new AuthError();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text) || res.statusText);
  }
}

export const uploadAvatar = (file: File) => uploadMultipart<User>("/api/me/avatar", file);

export const deleteAvatar = () => api<User>("/api/me/avatar", { method: "DELETE" });

export const logout = () => api<{ status: string }>("/auth/logout", { method: "POST" });
export const getHome = () =>
  api<{ completed_games: number; in_progress_games: number; saved_players: number }>("/api/home");
export const listPlayers = () => api<Player[]>("/api/players");
export const createPlayer = (name: string) =>
  api<Player>("/api/players", { method: "POST", body: JSON.stringify({ name }) });
export const listFriends = () => api<Friend[]>("/api/friends");
export const sendFriendRequest = (body: { user_id?: number; username?: string }) =>
  api<FriendSendResult>("/api/friends", { method: "POST", body: JSON.stringify(body) });
export const addFriend = sendFriendRequest;
export const listIncomingFriendRequests = () => api<FriendRequest[]>("/api/friends/requests/incoming");
export const acceptFriendRequest = (requestId: number) =>
  api<Friend>(`/api/friends/requests/${requestId}/accept`, { method: "POST" });
export const denyFriendRequest = (requestId: number) =>
  api<{ status: string }>(`/api/friends/requests/${requestId}/deny`, { method: "POST" });
export const removeFriend = (userId: number) =>
  api<{ status: string }>(`/api/friends/${userId}`, { method: "DELETE" });
export const getNotifications = () => api<NotificationList>("/api/notifications");
export const getUnreadCount = () => api<{ unread_count: number }>("/api/notifications/unread-count");
export const markNotificationRead = (id: number) =>
  api<Notification>(`/api/notifications/${id}/read`, { method: "POST" });
export const markAllNotificationsRead = () =>
  api<{ status: string }>("/api/notifications/read-all", { method: "POST" });
export const acceptNotificationFriendRequest = (id: number) =>
  api<Friend>(`/api/notifications/${id}/accept`, { method: "POST" });
export const denyNotificationFriendRequest = (id: number) =>
  api<{ status: string }>(`/api/notifications/${id}/deny`, { method: "POST" });
export const friendSuggestions = () => api<UserSearchResult[]>("/api/friends/suggestions");
export const searchUsers = (q: string) =>
  api<UserSearchResult[]>(`/api/users/search?q=${encodeURIComponent(q)}`);
export const createGame = (settings: Partial<GameSettings> & Pick<GameSettings, "minutes_per_turn" | "show_live_leaderboard">) =>
  api<{ id: number }>("/api/games", { method: "POST", body: JSON.stringify({ settings }) });
export const setPlayers = (gameId: number, player_ids: number[]) =>
  api<GameState>(`/api/games/${gameId}/players`, { method: "PUT", body: JSON.stringify({ player_ids }) });
export const setTurnOrder = (gameId: number, player_ids: number[]) =>
  api<GameState>(`/api/games/${gameId}/turn-order`, { method: "POST", body: JSON.stringify({ player_ids }) });
export const randomFirst = (gameId: number) =>
  api<GameState>(`/api/games/${gameId}/random-first`, { method: "POST" });
export const beginGame = (gameId: number) =>
  api<GameState>(`/api/games/${gameId}/begin`, { method: "POST" });
export const recordTurn = (gameId: number, body: Record<string, unknown>) =>
  api<GameState>(`/api/games/${gameId}/turns`, { method: "POST", body: JSON.stringify(body) });
export const nextPlayer = (gameId: number) =>
  api<GameState>(`/api/games/${gameId}/next-player`, { method: "POST" });
export const endGame = (gameId: number) =>
  api<GameState>(`/api/games/${gameId}/end`, { method: "POST" });
export const ackInactivity = (gameId: number) =>
  api<GameState>(`/api/games/${gameId}/ack-inactivity`, { method: "POST" });
export const finalizeGame = (gameId: number, rack_adjustments: Record<string, number>) =>
  api<GameState>(`/api/games/${gameId}/finalize`, { method: "POST", body: JSON.stringify({ rack_adjustments }) });
export const getGameState = (gameId: number) => api<GameState>(`/api/games/${gameId}/state`);
export const getGameDetail = (gameId: number) => api<GameState>(`/api/games/${gameId}`);
export const listGames = (status?: string) =>
  api<Array<{ id: number; status: string; played_date: string | null; winner: string | null }>>(
    `/api/games${status ? `?status=${status}` : ""}`,
  );
export const getLeaderboard = (scope: LeaderboardScope = "all") =>
  api<Leaderboard>(`/api/leaderboard?scope=${scope}`);

export type DictionaryCheckResult = {
  word: string;
  valid: boolean;
};

export const checkDictionaryWord = (word: string) =>
  api<DictionaryCheckResult>(`/api/dictionary/check/${encodeURIComponent(word)}`);

export async function submitFeedback(body: {
  message: string;
  category?: "bug" | "idea" | "other";
  page_url?: string;
  game_id?: number;
}): Promise<void> {
  const res = await fetch("/api/feedback", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.status === 401) {
    throw new AuthError();
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text) || res.statusText);
  }
}

export function gameWatchUrl(gameId: number): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/games/${gameId}/watch`;
}
