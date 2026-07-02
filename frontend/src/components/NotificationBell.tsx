import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  acceptNotificationFriendRequest,
  denyNotificationFriendRequest,
  getNotifications,
  getUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from "../api";

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function notificationLink(n: Notification): string | null {
  const gameId = n.payload.game_id;
  if (!gameId) return null;
  if (n.type === "live_game_started") return `/game/${gameId}/play`;
  if (n.type === "game_completed") return `/games/${gameId}`;
  return null;
}

export default function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  async function refreshCount() {
    try {
      const res = await getUnreadCount();
      setUnread(res.unread_count);
    } catch {
      /* ignore */
    }
  }

  async function loadList() {
    setLoading(true);
    try {
      const res = await getNotifications();
      setItems(res.notifications);
      setUnread(res.unread_count);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshCount();
    const interval = window.setInterval(refreshCount, 60000);
    const onFocus = () => refreshCount();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", onClickOutside);
      loadList();
    }
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  async function onAccept(n: Notification) {
    await acceptNotificationFriendRequest(n.id);
    await loadList();
    await refreshCount();
  }

  async function onDeny(n: Notification) {
    await denyNotificationFriendRequest(n.id);
    await loadList();
    await refreshCount();
  }

  async function onOpenItem(n: Notification) {
    const link = notificationLink(n);
    if (!link) return;
    await markNotificationRead(n.id);
    setOpen(false);
    navigate(link);
    refreshCount();
  }

  async function onMarkAllRead() {
    await markAllNotificationsRead();
    await loadList();
  }

  const badge = unread > 9 ? "9+" : String(unread);

  return (
    <div className="notification-bell" ref={ref}>
      <button
        type="button"
        className="notification-bell__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      >
        <svg className="notification-bell__icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 1 0-14 0v5l-2 2v1h18v-1l-2-2Z" />
        </svg>
        {unread > 0 && <span className="notification-bell__badge">{badge}</span>}
      </button>
      {open && (
        <div className="notification-bell__dropdown" role="menu">
          <div className="notification-bell__header">
            <strong>Notifications</strong>
            {unread > 0 && (
              <button type="button" className="notification-bell__mark-all" onClick={onMarkAllRead}>
                Mark all read
              </button>
            )}
          </div>
          {loading && <p className="muted notification-bell__empty">Loading…</p>}
          {!loading && items.length === 0 && (
            <p className="muted notification-bell__empty">No notifications</p>
          )}
          <ul className="notification-bell__list">
            {items.map((n) => (
              <li
                key={n.id}
                className={`notification-bell__item${n.read ? "" : " notification-bell__item--unread"}`}
              >
                <button
                  type="button"
                  className="notification-bell__item-body"
                  onClick={() => onOpenItem(n)}
                  disabled={!notificationLink(n)}
                >
                  <div className="notification-bell__title">{n.title}</div>
                  <div className="notification-bell__text">{n.body}</div>
                  <div className="notification-bell__time">{formatRelativeTime(n.created_at)}</div>
                </button>
                {n.type === "friend_request" && (
                  <div className="notification-bell__actions">
                    <button type="button" className="btn secondary" onClick={() => onAccept(n)}>
                      Accept
                    </button>
                    <button type="button" className="btn secondary" onClick={() => onDeny(n)}>
                      Deny
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
