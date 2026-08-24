import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LocaleSwitcher } from "../components/LocaleSwitcher";
import { Logo } from "../components/Logo";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useI18n } from "../context/I18nContext";
import { landingTranslations } from "../i18n/landingTranslations";

type PreviewKey = "command" | "library" | "chat" | "agent";

export function LandingPage() {
  const { locale } = useI18n();
  const copy = landingTranslations[locale];

  useEffect(() => {
    document.title = copy.seo.title;

    let description = document.querySelector<HTMLMetaElement>(
      'meta[name="description"]',
    );

    if (!description) {
      description = document.createElement("meta");
      description.name = "description";
      document.head.appendChild(description);
    }

    description.content = copy.seo.description;
  }, [copy.seo.description, copy.seo.title]);

  const [activePreview, setActivePreview] =
    useState<PreviewKey>("command");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const previewTabs = [
    {
      key: "command" as const,
      ...copy.preview.tabs.command,
    },
    {
      key: "library" as const,
      ...copy.preview.tabs.library,
    },
    {
      key: "chat" as const,
      ...copy.preview.tabs.chat,
    },
    {
      key: "agent" as const,
      ...copy.preview.tabs.agent,
    },
  ];

  const selectedPreview =
    previewTabs.find((tab) => tab.key === activePreview) ??
    previewTabs[0];

  return (
    <main className="masteacon-landing">
      <div className="masteacon-landing-ambient masteacon-landing-ambient-one" />
      <div className="masteacon-landing-ambient masteacon-landing-ambient-two" />

      <header className="masteacon-landing-header">
        <Link
          to="/"
          className="masteacon-landing-brand"
          aria-label="Masteacon"
        >
          <Logo size={34} withWordmark />
        </Link>

        <nav className="masteacon-landing-nav">
          <a href="#product">{copy.nav.product}</a>
          <a href="#solutions">{copy.nav.solutions}</a>
          <a href="#how-it-works">{copy.nav.howItWorks}</a>
          <a href="#architecture">{copy.nav.architecture}</a>
          <a href="#security">{copy.nav.security}</a>
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
            aria-label={
              mobileMenuOpen
                ? copy.nav.closeMenu
                : copy.nav.openMenu
            }
            aria-expanded={mobileMenuOpen}
            onClick={() =>
              setMobileMenuOpen((current) => !current)
            }
          >
            <span />
            <span />
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
            <div className="masteacon-landing-mobile-menu-label">
              {copy.nav.explore}
            </div>

            <nav>
              <a
                href="#product"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span>01</span>
                {copy.nav.product}
              </a>

              <a
                href="#solutions"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span>02</span>
                {copy.nav.solutions}
              </a>

              <a
                href="#how-it-works"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span>03</span>
                {copy.nav.howItWorks}
              </a>

              <a
                href="#architecture"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span>04</span>
                {copy.nav.architecture}
              </a>

              <a
                href="#security"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span>05</span>
                {copy.nav.security}
              </a>
            </nav>

            <div className="masteacon-landing-mobile-preferences">
              <ThemeSwitcher />
              <LocaleSwitcher />
            </div>

            <div className="masteacon-landing-mobile-account">
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
              >
                {copy.nav.signIn}
              </Link>

              <Link
                to="/register"
                className="primary"
                onClick={() => setMobileMenuOpen(false)}
              >
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

          <p className="masteacon-landing-hero-description">
            {copy.hero.description}
          </p>

          <div className="masteacon-landing-hero-actions">
            <Link
              to="/register"
              className="masteacon-landing-primary"
            >
              {copy.hero.primary}
              <span aria-hidden="true">→</span>
            </Link>

            <a
              href="#product"
              className="masteacon-landing-secondary"
            >
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
            <div className="masteacon-product-window-bar">
              <div className="masteacon-product-window-dots">
                <span />
                <span />
                <span />
              </div>

              <span className="masteacon-product-window-title">
                Masteacon
              </span>

              <span className="masteacon-product-window-status">
                <i />
                {copy.preview.grounded}
              </span>
            </div>

            <div className="masteacon-landing-hero-mockup-body">
              <div className="masteacon-landing-hero-mockup-input">
                <span>{copy.preview.question}</span>
                <span
                  className="masteacon-landing-hero-mockup-send"
                  aria-hidden="true"
                >
                  →
                </span>
              </div>

              <div className="masteacon-preview-answer masteacon-landing-hero-mockup-answer">
                <div className="masteacon-preview-answer-mark">
                  <Logo size={22} />
                </div>

                <div>
                  <strong>{copy.preview.answerReady}</strong>
                  <p>{copy.preview.answerDescription}</p>
                </div>
              </div>

              <div className="masteacon-preview-sources">
                <span>01 · product-notes.txt</span>
                <span>02 · company-policy.txt</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="product"
        className="masteacon-landing-section masteacon-product-showcase"
      >
        <div className="masteacon-landing-section-heading">
          <span>{copy.preview.sectionEyebrow}</span>

          <h2>
            {copy.preview.sectionTitle}
            <br />
            {copy.preview.sectionTitleSecond}
          </h2>

          <p>{copy.preview.sectionDescription}</p>
        </div>

        <div className="masteacon-product-tabs" role="tablist">
          {previewTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activePreview === tab.key}
              className={activePreview === tab.key ? "active" : ""}
              onClick={() => setActivePreview(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="masteacon-product-window">
          <div className="masteacon-product-window-bar">
            <div className="masteacon-product-window-dots">
              <span />
              <span />
              <span />
            </div>

            <span className="masteacon-product-window-title">
              Masteacon / {selectedPreview.label}
            </span>

            <span className="masteacon-product-window-status">
              <i />
              {copy.preview.grounded}
            </span>
          </div>

          <div className="masteacon-product-window-body">
            <aside className="masteacon-product-mini-sidebar">
              <Logo size={29} />

              <div className="masteacon-product-mini-nav">
                {previewTabs.map((tab) => (
                  <span
                    key={tab.key}
                    className={
                      activePreview === tab.key ? "active" : ""
                    }
                  >
                    {tab.label}
                  </span>
                ))}
              </div>
            </aside>

            <div className="masteacon-product-preview-content">
              <div className="masteacon-product-preview-copy">
                <span>{selectedPreview.eyebrow}</span>
                <h3>{selectedPreview.title}</h3>
                <p>{selectedPreview.description}</p>
              </div>

              <div className="masteacon-product-preview-grid">
                <article className="masteacon-product-preview-primary">
                  <span className="masteacon-preview-label">
                    {copy.preview.ask}
                  </span>

                  <h4>{copy.preview.question}</h4>

                  <div className="masteacon-preview-answer">
                    <div className="masteacon-preview-answer-mark">
                      <Logo size={26} />
                    </div>

                    <div>
                      <strong>{copy.preview.answerReady}</strong>
                      <p>{copy.preview.answerDescription}</p>
                    </div>
                  </div>

                  <div className="masteacon-preview-sources">
                    <span>01 · product-notes.txt</span>
                    <span>02 · company-policy.txt</span>
                  </div>
                </article>

                <div className="masteacon-product-preview-side">
                  <article>
                    <span>{selectedPreview.metricLabel}</span>
                    <strong>{selectedPreview.metricValue}</strong>
                    <small>{copy.preview.liveSignal}</small>
                  </article>

                  <article>
                    <span>{copy.preview.relevantContext}</span>
                    <strong>{copy.preview.grounded}</strong>
                    <small>{copy.preview.liveSignal}</small>
                  </article>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="solutions"
        className="masteacon-landing-section masteacon-problem-section"
      >
        <div className="masteacon-problem-heading">
          <span>{copy.problem.eyebrow}</span>

          <h2>
            {copy.problem.title}
            <br />
            <em>{copy.problem.accent}</em>
          </h2>

          <p>{copy.problem.description}</p>
        </div>

        <div className="masteacon-problem-grid">
          <article className="masteacon-problem-card without">
            <div className="masteacon-problem-card-heading">
              <span>{copy.problem.without}</span>
              <strong>{copy.problem.withoutTitle}</strong>
            </div>

            <ul>
              {copy.problem.withoutItems.map((item) => (
                <li key={item}>
                  <span aria-hidden="true">×</span>
                  {item}
                </li>
              ))}
            </ul>
          </article>

          <article
            className="masteacon-problem-card with"
            data-label={copy.problem.badge}
          >
            <div className="masteacon-problem-card-heading">
              <span>{copy.problem.with}</span>
              <strong>{copy.problem.withTitle}</strong>
            </div>

            <ul>
              {copy.problem.withItems.map((item) => (
                <li key={item}>
                  <span aria-hidden="true">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          </article>
        </div>
      </section>

      <section
        id="how-it-works"
        className="masteacon-landing-section masteacon-how-section"
      >
        <div className="masteacon-how-intro">
          <span>{copy.steps.eyebrow}</span>
          <h2>{copy.steps.title}</h2>
        </div>

        <div className="masteacon-how-grid">
          {copy.steps.items.map((item) => (
            <article key={item.number}>
              <span>{item.number}</span>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        id="architecture"
        className="masteacon-landing-section masteacon-architecture-section"
      >
        <div className="masteacon-architecture-heading">
          <span>{copy.architecture.eyebrow}</span>

          <div>
            <h2>
              {copy.architecture.title}
              <br />
              {copy.architecture.titleSecond}
            </h2>

            <p>{copy.architecture.description}</p>
          </div>
        </div>

        <div className="masteacon-architecture-flow">
          {copy.architecture.stages.map((stage, index) => (
            <div key={stage.number} className="masteacon-architecture-stage-fragment">
              <article>
                <span>{stage.number}</span>
                <strong>{stage.title}</strong>
                <small>{stage.description}</small>
              </article>

              {index < copy.architecture.stages.length - 1 && (
                <i>→</i>
              )}
            </div>
          ))}
        </div>

        <div className="masteacon-architecture-retrieval">
          <div className="masteacon-architecture-query">
            <span>{copy.architecture.questionLabel}</span>
            <strong>{copy.architecture.question}</strong>
          </div>

          <div className="masteacon-architecture-beam">
            {copy.architecture.flow.map((item, index) => (
              <div key={item} className="masteacon-architecture-beam-fragment">
                <span>{item}</span>

                {index < copy.architecture.flow.length - 1 && (
                  <i />
                )}
              </div>
            ))}
          </div>

          <div className="masteacon-architecture-answer">
            <Logo size={42} mColor="#F5F1E8" />

            <div>
              <span>{copy.architecture.answerLabel}</span>
              <strong>{copy.architecture.answerTitle}</strong>
              <small>{copy.architecture.answerDescription}</small>
            </div>
          </div>
        </div>

        <div className="masteacon-architecture-foot">
          {copy.architecture.signals.map((signal) => (
            <span key={signal}>{signal}</span>
          ))}
        </div>
      </section>

      <section className="masteacon-landing-section masteacon-capabilities-section">
        <div className="masteacon-capabilities-heading">
          <span>{copy.capabilities.eyebrow}</span>

          <div>
            <h2>
              {copy.capabilities.title}
              <br />
              {copy.capabilities.titleSecond}
            </h2>

            <p>{copy.capabilities.description}</p>
          </div>
        </div>

        <div className="masteacon-capabilities-grid">
          {copy.capabilities.items.map((item) => (
            <article key={item.number}>
              <span>{item.number}</span>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
              <small>{item.meta}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="masteacon-landing-section masteacon-audience-section">
        <div className="masteacon-audience-intro">
          <span>{copy.audience.eyebrow}</span>

          <h2>
            {copy.audience.title}
            <br />
            {copy.audience.titleSecond}
          </h2>

          <p>{copy.audience.description}</p>
        </div>

        <div className="masteacon-audience-grid">
          {copy.audience.items.map((item) => (
            <article key={item.label}>
              <span>{item.label}</span>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        id="security"
        className="masteacon-landing-section masteacon-trust-section"
      >
        <div className="masteacon-trust-copy">
          <span>{copy.trust.eyebrow}</span>

          <h2>
            {copy.trust.title}
            <em>{copy.trust.accent}</em>
          </h2>

          <p>{copy.trust.description}</p>

          <div className="masteacon-trust-signals">
            {copy.trust.signals.map((signal) => (
              <span key={signal}>
                <i />
                {signal}
              </span>
            ))}
          </div>
        </div>

        <div className="masteacon-trust-visual">
          <div className="masteacon-trust-visual-top">
            <span>{copy.trust.flowLabel}</span>
            <strong>{copy.trust.flowTitle}</strong>
          </div>

          <div className="masteacon-trust-flow">
            {copy.trust.stages.map((stage, index) => (
              <div key={stage.number} className="masteacon-trust-stage-fragment">
                <div>
                  <span>{stage.number}</span>
                  <strong>{stage.title}</strong>
                  <small>{stage.description}</small>
                </div>

                {index < copy.trust.stages.length - 1 && (
                  <i>→</i>
                )}
              </div>
            ))}
          </div>

          <div className="masteacon-trust-source">
            <Logo size={28} mColor="#F5F1E8" />

            <div>
              <span>{copy.trust.statusLabel}</span>
              <strong>{copy.trust.statusTitle}</strong>
            </div>

            <small>{copy.trust.ready}</small>
          </div>
        </div>
      </section>

      <section className="masteacon-landing-section masteacon-faq-section">
        <div className="masteacon-faq-heading">
          <span>{copy.faq.eyebrow}</span>

          <h2>
            {copy.faq.title}
            <br />
            {copy.faq.titleSecond}
          </h2>
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

      <section
        id="final-cta"
        className="masteacon-landing-section masteacon-landing-final-cta"
      >
        <div>
          <span>{copy.finalCta.eyebrow}</span>
          <h2>{copy.finalCta.title}</h2>
        </div>

        <Link to="/register">
          {copy.finalCta.button}
          <span aria-hidden="true">→</span>
        </Link>
      </section>

      <footer className="masteacon-landing-footer masteacon-landing-footer-full">
        <div className="masteacon-footer-brand">
          <Logo size={34} withWordmark />

          <p>{copy.footer.description}</p>

          <span>© 2026 Masteacon</span>
        </div>

        <div className="masteacon-footer-column">
          <strong>{copy.nav.product}</strong>

          <a href="#product">{copy.preview.tabs.command.label}</a>
          <a href="#product">{copy.preview.tabs.library.label}</a>
          <a href="#product">{copy.preview.tabs.chat.label}</a>
          <a href="#product">{copy.preview.tabs.agent.label}</a>
        </div>

        <div className="masteacon-footer-column">
          <strong>{copy.nav.explore}</strong>

          <a href="#solutions">{copy.nav.solutions}</a>
          <a href="#how-it-works">{copy.nav.howItWorks}</a>
          <a href="#architecture">{copy.nav.architecture}</a>
          <a href="#security">{copy.nav.security}</a>
        </div>

        <div className="masteacon-footer-column masteacon-footer-account">
          <strong>Masteacon</strong>

          <Link to="/login">{copy.footer.signIn}</Link>
          <Link to="/register">{copy.footer.create}</Link>

          <Link to="/register" className="masteacon-footer-primary">
            {copy.nav.getStarted}
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </footer>
    </main>
  );
}
