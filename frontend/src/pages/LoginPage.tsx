import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { LocaleSwitcher } from "../components/LocaleSwitcher";
import { Logo } from "../components/Logo";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";

export function LoginPage() {
  const { login } = useAuth();
  const { t, locale } = useI18n();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const copy =
    locale === "tr"
      ? {
          eyebrow: "KNOWLEDGE INTELLIGENCE",
          titleStart: "Bilginizi",
          titleAccent: "güvenilir yanıtlara",
          titleEnd: "dönüştürün.",
          description:
            "Dokümanlarınızı, çalışma alanlarınızı ve kurumsal bilginizi tek bir yapay zekâ destekli bilgi merkezinde birleştirin.",
          grounded: "Kaynaklı Yanıtlar",
          groundedText: "Her cevabın arkasındaki kanıtı görün.",
          semantic: "Semantik Arama",
          semanticText: "Anahtar kelimelerin ötesinde anlamı bulun.",
          agent: "AI Agent",
          agentText: "Bilginiz üzerinde çalışan akıllı iş akışları.",
          secure: "Trusted knowledge. Grounded intelligence.",
          welcome: "Tekrar hoş geldiniz",
          loginDescription:
            "Bilgi çalışma alanınıza devam etmek için giriş yapın.",
          emailPlaceholder: "ornek@company.com",
          passwordPlaceholder: "Şifrenizi girin",
          enter: "Masteacon'a Gir",
          entering: "Giriş yapılıyor...",
          noAccount: "Henüz hesabınız yok mu?",
          create: "Hesap oluşturun",
        }
      : {
          eyebrow: "KNOWLEDGE INTELLIGENCE",
          titleStart: "Turn knowledge into",
          titleAccent: "trusted answers",
          titleEnd: ".",
          description:
            "Bring documents, workspaces and organizational knowledge together in one AI-powered intelligence layer.",
          grounded: "Grounded Answers",
          groundedText: "See the evidence behind every response.",
          semantic: "Semantic Search",
          semanticText: "Find meaning beyond exact keywords.",
          agent: "AI Agent",
          agentText: "Intelligent workflows across your knowledge.",
          secure: "Trusted knowledge. Grounded intelligence.",
          welcome: "Welcome back",
          loginDescription:
            "Sign in to continue to your knowledge workspace.",
          emailPlaceholder: "you@company.com",
          passwordPlaceholder: "Enter your password",
          enter: "Enter Masteacon",
          entering: "Signing in...",
          noAccount: "New to Masteacon?",
          create: "Create an account",
        };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate("/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="masteacon-auth-page">
      <div className="masteacon-auth-ambient masteacon-auth-ambient-one" />
      <div className="masteacon-auth-ambient masteacon-auth-ambient-two" />

      <header className="masteacon-auth-header">
        <Link
          to="/login"
          className="masteacon-auth-header-brand"
          aria-label="Masteacon"
        >
          <Logo size={34} withWordmark />
        </Link>

        <div className="masteacon-auth-controls">
          <ThemeSwitcher />
          <LocaleSwitcher />
        </div>
      </header>

      <section className="masteacon-auth-shell">
        <div className="masteacon-auth-story">
          <div className="masteacon-auth-story-grid" />

          <div className="masteacon-auth-story-content">
            <span className="masteacon-auth-eyebrow">
              <span className="masteacon-auth-eyebrow-dot" />
              {copy.eyebrow}
            </span>

            <h1 className="masteacon-auth-title">
              {copy.titleStart}
              <span>{copy.titleAccent}</span>
              {copy.titleEnd}
            </h1>

            <p className="masteacon-auth-description">
              {copy.description}
            </p>

            <div className="masteacon-auth-beacon">
              <div className="masteacon-auth-beacon-ring masteacon-auth-beacon-ring-one" />
              <div className="masteacon-auth-beacon-ring masteacon-auth-beacon-ring-two" />
              <div className="masteacon-auth-beacon-ring masteacon-auth-beacon-ring-three" />

              <div className="masteacon-auth-beacon-mark">
                <Logo size={100} mColor="#F5F1E8" />
              </div>

              <div className="masteacon-auth-beacon-light" />
            </div>

            <div className="masteacon-auth-features">
              <div className="masteacon-auth-feature">
                <span className="masteacon-auth-feature-number">01</span>
                <div>
                  <strong>{copy.grounded}</strong>
                  <p>{copy.groundedText}</p>
                </div>
              </div>

              <div className="masteacon-auth-feature">
                <span className="masteacon-auth-feature-number">02</span>
                <div>
                  <strong>{copy.semantic}</strong>
                  <p>{copy.semanticText}</p>
                </div>
              </div>

              <div className="masteacon-auth-feature">
                <span className="masteacon-auth-feature-number">03</span>
                <div>
                  <strong>{copy.agent}</strong>
                  <p>{copy.agentText}</p>
                </div>
              </div>
            </div>
          </div>

          <footer className="masteacon-auth-story-footer">
            <span className="masteacon-auth-status-dot" />
            {copy.secure}
          </footer>
        </div>

        <div className="masteacon-auth-form-panel">
          <div className="masteacon-auth-form-wrap">
            <div className="masteacon-auth-mobile-brand">
              <Logo size={52} withWordmark />
              <span>Your beacon to mastery</span>
            </div>

            <div className="masteacon-auth-form-heading">
              <span className="masteacon-auth-form-kicker">
                MASTEACON
              </span>

              <h2>{copy.welcome}</h2>

              <p>{copy.loginDescription}</p>
            </div>

            {error && (
              <div className="error-banner masteacon-auth-error">
                {error}
              </div>
            )}

            <form
              className="masteacon-auth-form"
              onSubmit={handleSubmit}
            >
              <div className="masteacon-auth-field">
                <label htmlFor="email">{t("auth.email")}</label>

                <div className="masteacon-auth-input-wrap">
                  <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                  >
                    <path d="M4 6.75h16v10.5H4z" />
                    <path d="m4.5 7.5 7.5 5.75L19.5 7.5" />
                  </svg>

                  <input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder={copy.emailPlaceholder}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="masteacon-auth-field">
                <label htmlFor="password">
                  {t("auth.password")}
                </label>

                <div className="masteacon-auth-input-wrap">
                  <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                  >
                    <rect
                      x="5"
                      y="10"
                      width="14"
                      height="10"
                      rx="2"
                    />
                    <path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10" />
                  </svg>

                  <input
                    id="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    placeholder={copy.passwordPlaceholder}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                <Link to="/forgot-password" className="masteacon-auth-forgot-link">
                  Forgot password?
                </Link>
              </div>

              <button
                type="submit"
                className="masteacon-auth-submit"
                disabled={isSubmitting}
              >
                <span>
                  {isSubmitting ? copy.entering : copy.enter}
                </span>

                {!isSubmitting && (
                  <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  >
                    <path d="M5 12h14" />
                    <path d="m14 7 5 5-5 5" />
                  </svg>
                )}
              </button>
            </form>

            <div className="masteacon-auth-register">
              <span>{copy.noAccount}</span>{" "}
              <Link to="/register">{copy.create}</Link>
            </div>

            <div className="masteacon-auth-trust">
              <span />
              <p>
                RAG
                <i />
                Semantic Search
                <i />
                Source Grounding
              </p>
              <span />
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
