import { useState } from "react";
import { Link } from "react-router-dom";
import { deleteAvatar, updateUsername, uploadAvatar } from "../api";
import { useAuth } from "../auth/AuthContext";
import Avatar from "../components/Avatar";
import PhotoUploadButton from "../components/PhotoUploadButton";
import { useTheme, type ThemePreference } from "../theme/ThemeContext";

const THEME_OPTIONS: { value: ThemePreference; label: string; description: string }[] = [
  { value: "system", label: "System", description: "Match your device appearance" },
  { value: "light", label: "Light", description: "Warm, bright theme" },
  { value: "dark", label: "Dark", description: "Dark navy theme" },
];

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const { preference, setPreference } = useTheme();
  const [username, setUsername] = useState(user?.username ?? "");
  const [usernameMsg, setUsernameMsg] = useState("");
  const [usernameErr, setUsernameErr] = useState("");
  const [avatarErr, setAvatarErr] = useState("");
  const [avatarMsg, setAvatarMsg] = useState("");

  async function saveUsername() {
    setUsernameErr("");
    setUsernameMsg("");
    try {
      await updateUsername(username.trim());
      setUsernameMsg("Username saved.");
      await refresh();
    } catch (err) {
      setUsernameErr(err instanceof Error ? err.message : String(err));
    }
  }

  async function onAvatarUpload(file: File) {
    setAvatarErr("");
    setAvatarMsg("");
    await uploadAvatar(file);
    setAvatarMsg("Profile photo updated.");
    await refresh();
  }

  async function onRemoveAvatar() {
    setAvatarErr("");
    setAvatarMsg("");
    try {
      await deleteAvatar();
      setAvatarMsg(user?.provider === "google" ? "Reverted to Google photo." : "Profile photo removed.");
      await refresh();
    } catch (err) {
      setAvatarErr(err instanceof Error ? err.message : String(err));
    }
  }

  const removeLabel = user?.provider === "google" ? "Use Google photo" : "Remove photo";

  return (
    <div>
      <div className="card">
        <h1 className="page-title">Settings</h1>
        <Link to="/" className="back-link muted">← Home</Link>
      </div>

      <div className="card settings-section">
        <h2>Account</h2>
        <div className="profile-photo-settings">
          <Avatar
            name={user?.name ?? ""}
            email={user?.email}
            avatarUrl={user?.avatar_url}
            size="lg"
          />
          <div>
            <PhotoUploadButton label="Upload profile photo" onUpload={onAvatarUpload} />
            {user?.has_custom_avatar && (
              <button type="button" className="btn secondary" onClick={onRemoveAvatar}>
                {removeLabel}
              </button>
            )}
            {avatarMsg && <p className="muted">{avatarMsg}</p>}
            {avatarErr && <p className="error-text">{avatarErr}</p>}
          </div>
        </div>
        <div className="form-field">
          <label>Display name</label>
          <p>{user?.name}</p>
        </div>
        <div className="form-field">
          <label>Email</label>
          <p className="muted">{user?.email}</p>
        </div>
        <div className="form-field">
          <label htmlFor="username">Username</label>
          <div className="inline-form">
            <input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="your_username"
            />
            <button type="button" className="btn secondary" onClick={saveUsername}>Save</button>
          </div>
          <p className="muted">3–32 characters: lowercase letters, numbers, underscores.</p>
          {usernameMsg && <p className="muted">{usernameMsg}</p>}
          {usernameErr && <p className="error-text">{usernameErr}</p>}
        </div>
      </div>

      <div className="card settings-section">
        <h2>Appearance</h2>
        <div className="theme-options" role="radiogroup" aria-label="Theme">
          {THEME_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`theme-option${preference === opt.value ? " theme-option--selected" : ""}`}
            >
              <input
                type="radio"
                name="theme"
                value={opt.value}
                checked={preference === opt.value}
                onChange={() => setPreference(opt.value)}
              />
              <div>
                <div>{opt.label}</div>
                <div className="muted" style={{ fontSize: "0.85rem" }}>{opt.description}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="card settings-section">
        <p>
          <Link to="/privacy">Privacy policy</Link>
        </p>
      </div>
    </div>
  );
}
