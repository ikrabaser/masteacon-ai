import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import * as api from "../api/endpoints";
import { LocaleSwitcher } from "../components/LocaleSwitcher";
import { Logo } from "../components/Logo";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting) return;

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      const response = await api.resetPassword(token, newPassword);
      setMessage(response.message);
      // Resetting revokes every existing session (see PasswordResetService)
      // - send the user to sign in with the new password rather than
      // pretending they're still logged in anywhere.
      setTimeout(() => navigate("/login"), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset your password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="masteacon-auth-page masteacon-verification-page">
      <div className="masteacon-auth-ambient masteacon-auth-ambient-one" />
      <div className="masteacon-auth-ambient masteacon-auth-ambient-two" />

      <header className="masteacon-auth-header">
        <Link to="/" className="masteacon-auth-header-brand" aria-label="Masteacon">
          <Logo size={34} withWordmark />
        </Link>

        <div className="masteacon-auth-controls">
          <ThemeSwitcher />
          <LocaleSwitcher />
        </div>
      </header>

      <section className="masteacon-verification-card">
        <div className="masteacon-verification-icon">🔒</div>

        <span className="masteacon-auth-eyebrow">MASTEACON SECURITY</span>

        <h1>Choose a new password</h1>

        {!token ? (
          <div className="masteacon-verification-error">
            This reset link is missing its token. Request a new one from the{" "}
            <Link to="/forgot-password">forgot password</Link> page.
          </div>
        ) : message ? (
          <div className="masteacon-verification-success">{message}</div>
        ) : (
          <form onSubmit={handleSubmit} className="masteacon-auth-form">
            <div className="masteacon-auth-field">
              <label htmlFor="reset-new-password">New password</label>

              <div className="masteacon-auth-input-wrap">
                <input
                  id="reset-new-password"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
              </div>
            </div>

            <div className="masteacon-auth-field">
              <label htmlFor="reset-confirm-password">Confirm password</label>

              <div className="masteacon-auth-input-wrap">
                <input
                  id="reset-confirm-password"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </div>
            </div>

            {error && <div className="error-banner masteacon-auth-error">{error}</div>}

            <button type="submit" className="masteacon-auth-submit masteacon-verification-button" disabled={isSubmitting}>
              {isSubmitting ? "Resetting..." : "Reset password"}
            </button>
          </form>
        )}

        <Link to="/login" className="masteacon-verification-link">
          Back to sign in
        </Link>
      </section>
    </main>
  );
}
