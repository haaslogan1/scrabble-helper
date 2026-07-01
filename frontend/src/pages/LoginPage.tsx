import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { getAuthConfig, login, sendRegistrationCode, verifyRegistration } from "../api";
import { useAuth } from "../auth/AuthContext";
import AuthLayout from "../components/AuthLayout";
import GoogleSignInButton from "../components/GoogleSignInButton";
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
    <AuthLayout>
      <div className="auth-card">
        {config.google_login_enabled && <GoogleSignInButton />}

        {config.local_auth_enabled && (
          <>
            {config.google_login_enabled && (
              <div className="auth-divider">or</div>
            )}
            <div className="auth-tabs">
              <button
                type="button"
                className={`btn secondary${mode === "login" ? " active" : ""}`}
                onClick={() => switchMode("login")}
              >
                Sign in
              </button>
              <button
                type="button"
                className={`btn secondary${mode === "register" ? " active" : ""}`}
                onClick={() => switchMode("register")}
              >
                Create account
              </button>
            </div>
            <form onSubmit={onSubmit} noValidate>
              {mode === "register" && registerStep === "details" && (
                <div className="form-field">
                  <input
                    className="input"
                    placeholder="Display name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
              )}
              <div className="form-field">
                <input
                  className="input"
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
                />
                {emailError && <p className="error-text">{emailError}</p>}
              </div>
              {mode === "register" && registerStep === "details" && (
                <div className="form-field">
                  <input
                    className="input"
                    type="password"
                    placeholder="Password (10+ chars, letter and digit)"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              )}
              {mode === "register" && registerStep === "verify" && (
                <>
                  {info && <p className="muted">{info}</p>}
                  <div className="form-field">
                    <input
                      className="input"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      placeholder="6-digit verification code"
                      value={verificationCode}
                      onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      maxLength={6}
                      style={{ letterSpacing: "0.2em" }}
                    />
                  </div>
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
                <div className="form-field">
                  <input
                    className="input"
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              )}
              {error && <p className="error-text">{error}</p>}
              <button className="btn" type="submit" disabled={submitting} style={{ width: "100%", marginTop: "0.5rem" }}>
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
    </AuthLayout>
  );
}
