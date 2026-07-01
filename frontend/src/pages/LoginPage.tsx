import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { getAuthConfig, login, sendRegistrationCode, verifyRegistration } from "../api";
import { useAuth } from "../auth/AuthContext";
import { validateEmailInput } from "../emailValidation";

export default function LoginPage() {
  const navigate = useNavigate();
  const { refresh, user } = useAuth();
  const [config, setConfig] = useState({
    google_login_enabled: true,
    dev_login_enabled: false,
    local_auth_enabled: false,
    email_verification_enabled: true,
  });
  const [mode, setMode] = useState<"login" | "register">("login");
  const [registerStep, setRegisterStep] = useState<"details" | "verify">("details");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getAuthConfig().then(setConfig).catch(() => {});
  }, []);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  function resetRegisterFlow() {
    setRegisterStep("details");
    setVerificationCode("");
    setInfo(null);
    setError(null);
    setEmailError(null);
  }

  function switchMode(next: "login" | "register") {
    setMode(next);
    resetRegisterFlow();
  }

  function validateEmailField(): string | null {
    const result = validateEmailInput(email);
    if (!result.ok) {
      setEmailError(result.message);
      return result.message;
    }
    setEmailError(null);
    return null;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);

    const emailValidationError = validateEmailField();
    if (emailValidationError) {
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "register") {
        const normalizedEmail = validateEmailInput(email);
        if (!normalizedEmail.ok) {
          setEmailError(normalizedEmail.message);
          return;
        }
        if (registerStep === "details") {
          const res = await sendRegistrationCode(normalizedEmail.email, password, name);
          setInfo(res.message);
          setRegisterStep("verify");
        } else {
          await verifyRegistration(normalizedEmail.email, verificationCode.trim());
          await refresh();
          navigate("/", { replace: true });
        }
      } else {
        await login(email, password);
        await refresh();
        navigate("/", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 420, margin: "2rem auto" }}>
      <h1>Scrabble Helper</h1>
      <p className="muted">Sign in to start games, track scores, and view your personal stats.</p>

      {config.google_login_enabled && (
        <a className="btn" href="/auth/login/google" style={{ display: "inline-block", marginTop: "1rem" }}>
          Continue with Google
        </a>
      )}

      {config.local_auth_enabled && (
        <>
          {config.google_login_enabled && (
            <p className="muted" style={{ margin: "1.25rem 0 0.75rem", textAlign: "center" }}>or</p>
          )}
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
            <button
              type="button"
              className={mode === "login" ? "btn" : "btn secondary"}
              onClick={() => switchMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              className={mode === "register" ? "btn" : "btn secondary"}
              onClick={() => switchMode("register")}
            >
              Create account
            </button>
          </div>
          <form onSubmit={onSubmit} noValidate>
            {mode === "register" && registerStep === "details" && (
              <input
                placeholder="Display name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={{ marginBottom: "0.5rem", width: "100%" }}
              />
            )}
            <input
              type="text"
              inputMode="email"
              autoComplete="email"
              placeholder="Email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError(null);
              }}
              onBlur={validateEmailField}
              disabled={mode === "register" && registerStep === "verify"}
              style={{ marginBottom: "0.25rem", width: "100%" }}
            />
            {emailError && (
              <p style={{ color: "crimson", margin: "0 0 0.5rem", fontSize: "0.9rem" }}>{emailError}</p>
            )}
            {mode === "register" && registerStep === "details" && (
              <input
                type="password"
                placeholder="Password (10+ chars, letter and digit)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ marginBottom: "0.5rem", width: "100%" }}
              />
            )}
            {mode === "register" && registerStep === "verify" && (
              <>
                {info && (
                  <p className="muted" style={{ marginBottom: "0.75rem", fontSize: "0.95rem" }}>
                    {info}
                  </p>
                )}
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="6-digit verification code"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  maxLength={6}
                  style={{ marginBottom: "0.5rem", width: "100%", letterSpacing: "0.2em" }}
                />
                <button
                  type="button"
                  className="btn secondary"
                  style={{ width: "100%", marginBottom: "0.5rem" }}
                  disabled={submitting}
                  onClick={async () => {
                    setError(null);
                    setSubmitting(true);
                    try {
                      const normalized = validateEmailInput(email);
                      if (!normalized.ok) {
                        setEmailError(normalized.message);
                        return;
                      }
                      const res = await sendRegistrationCode(normalized.email, password, name);
                      setInfo(res.message);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Could not resend code");
                    } finally {
                      setSubmitting(false);
                    }
                  }}
                >
                  Resend code
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  style={{ width: "100%", marginBottom: "0.5rem" }}
                  onClick={() => setRegisterStep("details")}
                >
                  Edit email or password
                </button>
              </>
            )}
            {mode === "login" && (
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ marginBottom: "0.5rem", width: "100%" }}
              />
            )}
            {error && <p style={{ color: "crimson" }}>{error}</p>}
            <button className="btn" type="submit" disabled={submitting} style={{ marginTop: "0.5rem", width: "100%" }}>
              {mode === "register"
                ? registerStep === "verify"
                  ? "Verify and create account"
                  : "Send verification code"
                : "Sign in"}
            </button>
          </form>
        </>
      )}

      {!config.google_login_enabled && !config.local_auth_enabled && !config.dev_login_enabled && (
        <p>No sign-in methods are configured on this server.</p>
      )}

      {config.dev_login_enabled && (
        <p style={{ marginTop: "1rem" }}>
          <a className="btn secondary" href="/auth/dev-login">Dev sign-in (local only)</a>
        </p>
      )}
    </div>
  );
}
