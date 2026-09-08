import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ChatIcon, CheckIcon, FolderIcon, MenuIcon, SearchIcon, SparkleIcon, XIcon } from "../components/icons";
import { LocaleSwitcher } from "../components/LocaleSwitcher";
import { Logo } from "../components/Logo";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useI18n } from "../context/I18nContext";
import { landingTranslations } from "../i18n/landingTranslations";

const FEATURE_ICONS = {
  search: SearchIcon,
  chat: ChatIcon,
  folder: FolderIcon,
  sparkle: SparkleIcon,
} as const;

export function LandingPage() {
  const { locale } = useI18n();
  const copy = landingTranslations[locale];

  useEffect(() => {
    document.title = copy.seo.title;

    let description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (!description) {
      description = document.createElement("meta");
      description.name = "description";
      document.head.appendChild(description);
    }
    description.content = copy.seo.description;
  }, [copy.seo.description, copy.seo.title]);

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const root = document.querySelector<HTMLElement>(".masteacon-landing");
    if (!root) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const targets = root.querySelectorAll<HTMLElement>(".masteacon-landing-hero-copy, .reveal");
    if (targets.length === 0) return;

    root.setAttribute("data-reveal", "ready");

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -60px 0px" },
    );

    targets.forEach((el) => observer.observe(el));

    const fallback = window.setTimeout(() => {
      targets.forEach((el) => el.classList.add("is-visible"));
    }, 1500);

    return () => {
      observer.disconnect();
      window.clearTimeout(fallback);
    };
  }, []);

  const navLinks = [
    { href: "#features", label: copy.nav.features },
    { href: "#how-it-works", label: copy.nav.howItWorks },
    { href: "#security", label: copy.nav.security },
  ];

  return (
    <main className="masteacon-landing">
      <div className="masteacon-landing-ambient masteacon-landing-ambient-one" />
      <div className="masteacon-landing-ambient masteacon-landing-ambient-two" />

      <header className="masteacon-landing-header">
        <Link to="/" className="masteacon-landing-brand" aria-label="Masteacon">
          <Logo size={32} withWordmark />
        </Link>

        <nav className="masteacon-landing-nav">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>

        <div className="masteacon-landing-actions">
          <div className="masteacon-landing-controls">
            <ThemeSwitcher />
            <LocaleSwitcher />
          </div>

          <Link to="/login" className="masteacon-landing-signin">
            {copy.nav.signIn}
          </Link>

          <Link to="/register" className="masteacon-landing-cta-small">
            {copy.nav.getStarted}
            <span aria-hidden="true">→</span>
          </Link>

          <button
            type="button"
            className="masteacon-landing-menu-button"
            aria-label={mobileMenuOpen ? copy.nav.closeMenu : copy.nav.openMenu}
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen((current) => !current)}
          >
            {mobileMenuOpen ? <XIcon width={20} height={20} /> : <MenuIcon width={20} height={20} />}
          </button>
        </div>
      </header>

      {mobileMenuOpen && (
        <>
          <button
            type="button"
            className="masteacon-landing-mobile-backdrop"
            aria-label={copy.nav.closeMenu}
            onClick={() => setMobileMenuOpen(false)}
          />

          <div className="masteacon-landing-mobile-menu">
            <div className="masteacon-landing-mobile-menu-label">{copy.nav.explore}</div>

            <nav>
              {navLinks.map((link, index) => (
                <a key={link.href} href={link.href} onClick={() => setMobileMenuOpen(false)}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  {link.label}
                </a>
              ))}
            </nav>

            <div className="masteacon-landing-mobile-preferences">
              <ThemeSwitcher />
              <LocaleSwitcher />
            </div>

            <div className="masteacon-landing-mobile-account">
              <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                {copy.nav.signIn}
              </Link>

              <Link to="/register" className="primary" onClick={() => setMobileMenuOpen(false)}>
                {copy.nav.getStarted}
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </>
      )}

      <section className="masteacon-landing-hero">
        <div className="masteacon-landing-hero-copy">
          <span className="masteacon-landing-eyebrow">
            <span className="masteacon-landing-eyebrow-dot" />
            {copy.hero.eyebrow}
          </span>

          <h1>
            {copy.hero.titleStart}
            <span>{copy.hero.titleAccent}</span>
          </h1>

          <p className="masteacon-landing-hero-description">{copy.hero.description}</p>

          <div className="masteacon-landing-hero-actions">
            <Link to="/register" className="masteacon-landing-primary">
              {copy.hero.primary}
              <span aria-hidden="true">→</span>
            </Link>

            <a href="#how-it-works" className="masteacon-landing-secondary">
              {copy.hero.secondary}
            </a>
          </div>

          <div className="masteacon-landing-trust-row">
            {copy.hero.signals.map((signal) => (
              <span key={signal}>{signal}</span>
            ))}
          </div>
        </div>

        <div className="masteacon-landing-hero-visual">
          <div className="masteacon-landing-hero-mockup">
            <div className="masteacon-landing-hero-mockup-bar">
              <span />
              <span />
              <span />
              <span className="masteacon-landing-hero-mockup-title">Masteacon / {copy.mockup.workspaceLabel}</span>
            </div>

            <div className="masteacon-landing-hero-mockup-body">
              <div className="masteacon-landing-hero-mockup-input">
                <span>{copy.mockup.question}</span>
                <span className="masteacon-landing-hero-mockup-send" aria-hidden="true">
                  →
                </span>
              </div>

              <div className="masteacon-landing-hero-mockup-answer">
                <span className="masteacon-landing-hero-mockup-answer-label">{copy.mockup.answerLabel}</span>
                <p>{copy.mockup.answerTitle}</p>

                <div className="masteacon-landing-hero-mockup-sources">
                  <span>{copy.mockup.sourceLabel}</span>
                  {copy.mockup.sources.map((source, index) => (
                    <span key={source} className="masteacon-landing-hero-mockup-source">
                      {index + 1}. {source}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="masteacon-landing-section reveal masteacon-features-section">
        <div className="masteacon-landing-section-heading">
          <span>{copy.features.eyebrow}</span>
          <h2>{copy.features.title}</h2>
        </div>

        <div className="masteacon-features-grid">
          {copy.features.items.map((item) => {
            const FeatureIcon = FEATURE_ICONS[item.icon as keyof typeof FEATURE_ICONS];
            return (
              <article key={item.title} className="masteacon-feature-card">
                <span className="masteacon-feature-icon">
                  <FeatureIcon width={20} height={20} />
                </span>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section id="how-it-works" className="masteacon-landing-section reveal masteacon-how-section">
        <div className="masteacon-landing-section-heading">
          <span>{copy.how.eyebrow}</span>
          <h2>{copy.how.title}</h2>
        </div>

        <div className="masteacon-how-grid">
          {copy.how.steps.map((step) => (
            <article key={step.number}>
              <span>{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="security" className="masteacon-landing-section reveal masteacon-trust-section">
        <div className="masteacon-trust-copy">
          <span className="masteacon-landing-eyebrow">
            <span className="masteacon-landing-eyebrow-dot" />
            {copy.trust.eyebrow}
          </span>

          <h2>
            {copy.trust.title}
            <em>{copy.trust.titleAccent}</em>
          </h2>

          <p>{copy.trust.description}</p>
        </div>

        <ul className="masteacon-trust-list">
          {copy.trust.points.map((point) => (
            <li key={point}>
              <CheckIcon width={16} height={16} />
              {point}
            </li>
          ))}
        </ul>
      </section>

      <section className="masteacon-landing-section reveal masteacon-faq-section">
        <div className="masteacon-faq-heading">
          <span>{copy.faq.eyebrow}</span>
          <h2>{copy.faq.title}</h2>
        </div>

        <div className="masteacon-faq-list">
          {copy.faq.items.map((item) => (
            <details key={item.question}>
              <summary>
                <span>{item.question}</span>
                <i>+</i>
              </summary>
              <p>{item.answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="masteacon-landing-section reveal masteacon-landing-final-cta">
        <div>
          <span>{copy.finalCta.eyebrow}</span>
          <h2>{copy.finalCta.title}</h2>
        </div>

        <Link to="/register">
          {copy.finalCta.button}
          <span aria-hidden="true">→</span>
        </Link>
      </section>

      <footer className="masteacon-landing-footer">
        <div className="masteacon-footer-brand">
          <Logo size={30} withWordmark />
          <p>{copy.footer.description}</p>
          <span>© 2026 Masteacon</span>
        </div>

        <div className="masteacon-footer-column">
          <strong>{copy.footer.product}</strong>
          {copy.footer.productLinks.map((label) => (
            <a key={label} href="#features">
              {label}
            </a>
          ))}
        </div>

        <div className="masteacon-footer-column">
          <strong>{copy.footer.explore}</strong>
          {navLinks.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </div>

        <div className="masteacon-footer-column masteacon-footer-account">
          <strong>Masteacon</strong>
          <Link to="/login">{copy.footer.signIn}</Link>
          <Link to="/register" className="masteacon-footer-primary">
            {copy.nav.getStarted}
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </footer>
    </main>
  );
}
