import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  acceptFriendRequest,
  denyFriendRequest,
  listFriends,
  listIncomingFriendRequests,
  removeFriend,
  searchUsers,
  sendFriendRequest,
  type Friend,
  type FriendRequest,
  type UserSearchResult,
} from "../api";
import Avatar from "../components/Avatar";

export default function FindFriendsPage() {
  const [friends, setFriends] = useState<Friend[]>([]);
  const [incoming, setIncoming] = useState<FriendRequest[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function refresh() {
    listFriends().then(setFriends).catch(() => {});
    listIncomingFriendRequests().then(setIncoming).catch(() => {});
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!query.trim()) return;
    try {
      const found = await searchUsers(query.trim());
      setResults(found);
    } catch (err) {
      setError(String(err));
    }
  }

  async function onSendRequest(user: UserSearchResult) {
    setError("");
    setMessage("");
    try {
      const res = await sendFriendRequest({ user_id: user.id });
      if (res.mutual) {
        setMessage(`You and ${user.name} are now friends`);
      } else {
        setMessage(`Friend request sent to ${user.name}`);
      }
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onAccept(requestId: number) {
    setError("");
    await acceptFriendRequest(requestId);
    refresh();
  }

  async function onDeny(requestId: number) {
    setError("");
    await denyFriendRequest(requestId);
    refresh();
  }

  async function onRemove(userId: number) {
    setError("");
    try {
      await removeFriend(userId);
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  function userLabel(user: { username: string | null; name: string }) {
    return user.username ? `@${user.username}` : user.name;
  }

  return (
    <div>
      <div className="card">
        <h1 className="page-title">Find Friends</h1>
        <Link to="/" className="back-link muted">← Home</Link>
        <p className="muted">Send friend requests by username or email. Both must accept to become friends.</p>
      </div>

      {incoming.length > 0 && (
        <div className="card">
          <h2>Incoming requests</h2>
          <ul className="friend-list">
            {incoming.map((req) => (
              <li key={req.id} className="friend-list__row">
                <Avatar
                  name={req.from_user.name}
                  avatarUrl={req.from_user.avatar_url}
                  size="sm"
                />
                <span className="friend-list__row__label">
                  {userLabel(req.from_user)} — {req.from_user.name}
                </span>
                <span>
                  <button type="button" className="btn secondary" onClick={() => onAccept(req.id)}>Accept</button>
                  <button type="button" className="btn secondary" onClick={() => onDeny(req.id)}>Deny</button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2>Search</h2>
        <form className="inline-form" onSubmit={onSearch}>
          <input
            placeholder="Username or email"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn secondary">Search</button>
        </form>
        {results.length > 0 && (
          <ul className="friend-list">
            {results.map((u) => (
              <li key={u.id} className="friend-list__row">
                <Avatar name={u.name} avatarUrl={u.avatar_url} size="sm" />
                <span className="friend-list__row__label">{userLabel(u)} — {u.name}</span>
                <button type="button" className="btn secondary" onClick={() => onSendRequest(u)}>Send request</button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Your friends</h2>
        {friends.length === 0 && <p className="muted">No friends yet.</p>}
        <ul className="friend-list">
          {friends.map((f) => (
            <li key={f.id} className="friend-list__row">
              <Avatar name={f.name} avatarUrl={f.avatar_url} size="sm" />
              <span className="friend-list__row__label">
                {userLabel(f)} — {f.name}
                <span className="tag tag--ok"> Friend</span>
              </span>
              <button type="button" className="btn secondary" onClick={() => onRemove(f.id)}>Remove</button>
            </li>
          ))}
        </ul>
      </div>

      {message && <p className="muted">{message}</p>}
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
