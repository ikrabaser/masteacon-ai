import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import * as api from "../api/endpoints";
import { LocaleSwitcher } from "../components/LocaleSwitcher";
import { Logo } from "../components/Logo";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      const response = await api.forgotPassword(email);
      setMessage(response.message);
    } catch (err) {
      // Even a network/server error shouldn't reveal anything about the
      // account beyond the same generic message the backend itself sends.
      setError(err instanceof Error ? err.message : "Unable to request a password reset.");
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
        <div className="masteacon-verification-icon">🔑</div>

        <span className="masteacon-auth-eyebrow">MASTEACON SECURITY</span>

        <h1>Reset your password</h1>

        <p className="masteacon-verification-muted">
          Enter your account email and we'll send you a link to reset your password.
        </p>

        {message ? (
          <div className="masteacon-verification-success">{message}</div>
        ) : (
          <form onSubmit={handleSubmit} className="masteacon-auth-form">
            <div className="masteacon-auth-field">
              <label htmlFor="forgot-password-email">Email</label>

              <div className="masteacon-auth-input-wrap">
                <input
                  id="forgot-password-email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
            </div>

            {error && <div className="error-banner masteacon-auth-error">{error}</div>}

            <button type="submit" className="masteacon-auth-submit masteacon-verification-button" disabled={isSubmitting}>
              {isSubmitting ? "Sending..." : "Send reset link"}
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
