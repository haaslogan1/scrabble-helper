import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme, type ThemePreference } from "../theme/ThemeContext";

const THEME_OPTIONS: { value: ThemePreference; label: string; description: string }[] = [
  { value: "system", label: "System", description: "Match your device appearance" },
  { value: "light", label: "Light", description: "Warm, bright theme" },
  { value: "dark", label: "Dark", description: "Dark navy theme" },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const { preference, setPreference } = useTheme();

  return (
    <div>
      <div className="card">
        <h1 className="page-title">Settings</h1>
        <Link to="/" className="back-link muted">← Home</Link>
      </div>

      <div className="card settings-section">
        <h2>Account</h2>
        <div className="form-field">
          <label>Display name</label>
          <p>{user?.name}</p>
        </div>
        <div className="form-field">
          <label>Email</label>
          <p className="muted">{user?.email}</p>
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
    </div>
  );
}
