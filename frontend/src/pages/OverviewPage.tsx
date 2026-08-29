import {
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";

import * as api from "../api/endpoints";
import type {
  AskResponse,
  ConversationResponse,
  DocumentResponse,
} from "../api/types";

import {
  BellIcon,
  ChatIcon,
  CheckIcon,
  ChevronRightIcon,
  ClockIcon,
  FileIcon,
  FolderIcon,
  RocketIcon,
  SearchIcon,
  SendIcon,
  SparkleIcon,
  UploadIcon,
  WarningIcon,
} from "../components/icons";
import { Logo } from "../components/Logo";

import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { useWorkspace } from "../context/WorkspaceContext";

interface ActivityItem {
  id: string;
  icon: ReactNode;
  label: string;
  detail: string;
  at: string;
}

function timeAgo(iso: string, locale: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);

  if (minutes < 1) {
    return locale === "tr" ? "az önce" : "just now";
  }

  if (minutes < 60) {
    return locale === "tr"
      ? `${minutes} dk önce`
      : `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);

  if (hours < 24) {
    return locale === "tr"
      ? `${hours} sa önce`
      : `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);

  return locale === "tr"
    ? `${days} gün önce`
    : `${days}d ago`;
}

function getDocumentType(document: DocumentResponse) {
  if (document.content_type.includes("pdf")) {
    return "PDF";
  }

  if (
    document.content_type.includes("word") ||
    document.content_type.includes("document")
  ) {
    return "DOCX";
  }

  return "TXT";
}

export function OverviewPage() {
  const { user } = useAuth();
  const { activeWorkspace, workspaces } = useWorkspace();
  const { t, locale } = useI18n();
  const navigate = useNavigate();

  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [conversations, setConversations] = useState<
    ConversationResponse[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [prompt, setPrompt] = useState("");
  const [asking, setAsking] = useState(false);

  const [thread, setThread] = useState<
    {
      question: string;
      response: AskResponse;
    }[]
  >([]);

  function loadOverviewData() {
    if (!activeWorkspace) {
      return;
    }

    setIsLoading(true);
    setLoadError(null);

    Promise.all([
      api.listDocuments(activeWorkspace.id),
      api.listConversations(activeWorkspace.id),
    ])
      .then(([docs, convos]) => {
        setDocuments(docs);
        setConversations(convos);
      })
      .catch(() => {
        // Most commonly a network failure (API unreachable, CORS, etc.) —
        // never let it surface as an unhandled rejection / raw "Failed to
        // fetch" past this page; show a retryable banner instead.
        setLoadError(
          locale === "tr"
            ? "Veriler yüklenemedi. Sunucuya ulaşılamıyor olabilir."
            : "Couldn't load your data. The server may be unreachable.",
        );
      })
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    loadOverviewData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeWorkspace]);

  const indexedCount = documents.filter(
    (document) => document.status === "indexed",
  ).length;

  const coveragePct =
    documents.length > 0
      ? Math.round((indexedCount / documents.length) * 100)
      : 0;

  const recentDocuments = [...documents]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime(),
    )
    .slice(0, 4);

  const activity: ActivityItem[] = [
    ...documents.map((document) => ({
      id: `doc-${document.id}`,
      icon:
        document.status === "indexed" ? (
          <CheckIcon
            width={14}
            height={14}
            className="activity-icon-success"
          />
        ) : document.status === "failed" ? (
          <WarningIcon
            width={14}
            height={14}
            className="activity-icon-danger"
          />
        ) : (
          <UploadIcon
            width={14}
            height={14}
            className="activity-icon-muted"
          />
        ),
      label: document.filename,
      detail:
        locale === "tr"
          ? "Doküman güncellendi"
          : "Document updated",
      at: document.created_at,
    })),
    ...conversations.map((conversation) => ({
      id: `conversation-${conversation.id}`,
      icon: (
        <ChatIcon
          width={14}
          height={14}
          className="activity-icon-brand"
        />
      ),
      label: conversation.title,
      detail:
        locale === "tr"
          ? "Konuşma başlatıldı"
          : "Conversation started",
      at: conversation.created_at,
    })),
  ]
    .sort(
      (a, b) =>
        new Date(b.at).getTime() -
        new Date(a.at).getTime(),
    )
    .slice(0, 5);

  const latestTurn =
    thread.length > 0 ? thread[thread.length - 1] : null;

  const initial = (user?.email || "M").charAt(0).toUpperCase();

  const username =
    user?.email?.split("@")[0] ||
    (locale === "tr" ? "kullanıcı" : "user");

  const copy =
    locale === "tr"
      ? {
          commandCenter: "Bilgi Komuta Merkezi",
          subtitle:
            "Yapay zekâ destekli bilgi zekâsı.",
          grounded: "Kaynaklı cevaplar.",
          proven: "Güvenilir kaynaklar.",
          search: "Bilgi genelinde ara...",
          notifications: "Bildirimler",
          ask: "Masteacon'a Sor",
          askDescription:
            "Güvenilir bilginizden kaynaklı yanıtlar alın.",
          askPlaceholder:
            "Bilginiz hakkında ne öğrenmek istiyorsunuz?",
          groundedAnswer: "Kaynaklı Yanıt",
          sourcesUsed: "Kullanılan Kaynaklar",
          noSourcesReturned:
            "Bu yanıtta kaynak eşleşmesi döndürülmedi.",
          deepResearch: "Derin Araştırma",
          summarize: "Özetle",
          compare: "Kaynakları Karşılaştır",
          recent: "Son Bilgiler",
          health: "Bilgi Sağlığı",
          indexedCoverage: "İndeks Kapsamı",
          indexedSources: "İndeksli Kaynak",
          totalSources: "Toplam Kaynak",
          conversations: "Konuşmalar",
          workspaces: "Çalışma Alanları",
          workspaceReady: "Çalışma alanı hazır",
          indexing: "İndeksleme devam ediyor",
          noSources: "Henüz kaynak yok",
          library: "Bilgi Kütüphanesi",
          viewAll: "Tümünü Gör",
          noDocuments: "Henüz doküman yok.",
          signals: "Bilgi İçgörüleri",
          signalDescription:
            "Aktif çalışma alanınızın gerçek verilerinden oluşturulan görünüm.",
          coverage: "Kapsam",
          conversationsMetric: "AI Konuşmaları",
          workspaceMetric: "Alanlar",
          quickAccess: "Hızlı Erişim",
          upload: "Bilgi Ekle",
          uploadSub: "Yeni doküman yükleyin",
          chat: "Masteacon'a Sor",
          chatSub: "Kaynaklı bir konuşma başlatın",
          workspace: "Alanları Yönet",
          workspaceSub: "Bilginizi düzenleyin",
          agent: "AI Ajanını Aç",
          agentSub: "Araç kullanan görevler çalıştırın",
          trace: "Agent Trace",
          traceDescription:
            "Masteacon'ın soruyu nasıl işlediğini şeffaf biçimde görün.",
          fullTrace: "Ajanı Aç",
          understand: "Anla",
          understandReady: "Soruyu ve amacı yorumlar.",
          retrieve: "Getir",
          retrieveReady: "İndeksli bilginizde arama yapar.",
          tools: "Kaynakla",
          toolsReady:
            "Yanıtı çalışma alanındaki kanıtlarla temellendirir.",
          synthesize: "Sentezle",
          synthesizeReady: "En alakalı bilgiyi bir araya getirir.",
          answer: "Yanıtla",
          answerReady: "Kaynaklı yanıtı oluşturur.",
          completed: "Tamamlandı",
          ready: "Hazır",
          activity: "Son Etkinlik",
          noActivity: "Henüz etkinlik yok.",
          welcome: `Hoş geldin, ${username}.`,
          loading: "Bilgi yükleniyor...",
        }
      : {
          commandCenter: "Knowledge Command Center",
          subtitle:
            "AI-powered knowledge intelligence.",
          grounded: "Grounded answers.",
          proven: "Proven sources.",
          search: "Search across knowledge...",
          notifications: "Notifications",
          ask: "Ask Masteacon",
          askDescription:
            "Get grounded answers from your trusted knowledge.",
          askPlaceholder:
            "What would you like to know about your knowledge?",
          groundedAnswer: "Grounded Answer",
          sourcesUsed: "Sources Used",
          noSourcesReturned:
            "No source match was returned for this answer.",
          deepResearch: "Deep Research",
          summarize: "Summarize",
          compare: "Compare Sources",
          recent: "Recent Knowledge",
          health: "Knowledge Health",
          indexedCoverage: "Indexed Coverage",
          indexedSources: "Sources Indexed",
          totalSources: "Total Sources",
          conversations: "Conversations",
          workspaces: "Workspaces",
          workspaceReady: "Workspace ready",
          indexing: "Indexing in progress",
          noSources: "No sources yet",
          library: "Knowledge Library",
          viewAll: "View all",
          noDocuments: "No documents yet.",
          signals: "Knowledge Insights",
          signalDescription:
            "A live view built from your active workspace data.",
          coverage: "Coverage",
          conversationsMetric: "AI Conversations",
          workspaceMetric: "Workspaces",
          quickAccess: "Quick Access",
          upload: "Add Knowledge",
          uploadSub: "Upload a new document",
          chat: "Ask Masteacon",
          chatSub: "Start a grounded conversation",
          workspace: "Manage Workspaces",
          workspaceSub: "Organize your knowledge",
          agent: "Open AI Agent",
          agentSub: "Run tool-enabled tasks",
          trace: "Agent Trace",
          traceDescription:
            "See how Masteacon moves from question to grounded answer.",
          fullTrace: "Open Agent",
          understand: "Understand",
          understandReady: "Interpret the question and intent.",
          retrieve: "Retrieve",
          retrieveReady: "Search across indexed knowledge.",
          tools: "Ground",
          toolsReady:
            "Ground the answer in evidence from this workspace.",
          synthesize: "Synthesize",
          synthesizeReady: "Connect the most relevant information.",
          answer: "Answer",
          answerReady: "Generate the grounded response.",
          completed: "Completed",
          ready: "Ready",
          activity: "Recent Activity",
          noActivity: "No activity yet.",
          welcome: `Welcome back, ${username}.`,
          loading: "Loading knowledge...",
        };

  const suggestions =
    locale === "tr"
      ? [
          "Son dokümanları özetle",
          "Kaynakları karşılaştır",
          "Çalışma alanımı analiz et",
        ]
      : [
          "Summarize recent documents",
          "Compare my sources",
          "Analyze this workspace",
        ];

  const healthLabel =
    documents.length === 0
      ? copy.noSources
      : coveragePct === 100
        ? copy.workspaceReady
        : copy.indexing;

  async function handleAsk(event: FormEvent) {
    event.preventDefault();

    if (
      !activeWorkspace ||
      !prompt.trim() ||
      asking
    ) {
      return;
    }

    const question = prompt.trim();

    setPrompt("");
    setAsking(true);

    try {
      const response = await api.ask(
        activeWorkspace.id,
        question,
      );

      setThread((previous) => [
        ...previous,
        {
          question,
          response,
        },
      ]);
    } catch {
      setThread((previous) => [
        ...previous,
        {
          question,
          response: {
            answer:
              locale === "tr"
                ? "Yanıt alınırken bir sorun oluştu."
                : "Something went wrong while retrieving the answer.",
            sources: [],
          },
        },
      ]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="kc-page">
      {loadError && (
        <div className="kc-error-banner" role="alert">
          <WarningIcon width={16} height={16} />
          <span>{loadError}</span>
          <button type="button" onClick={loadOverviewData}>
            {locale === "tr" ? "Tekrar dene" : "Retry"}
          </button>
        </div>
      )}

      <div className="kc-topbar">
        <div className="kc-workspace-chip">
          <FolderIcon width={15} height={15} />

          <div>
            <span>
              {locale === "tr"
                ? "AKTİF ÇALIŞMA ALANI"
                : "ACTIVE WORKSPACE"}
            </span>

            <strong>{activeWorkspace?.name ?? "—"}</strong>
          </div>
        </div>

        <div className="kc-search">
          <SearchIcon width={16} height={16} />

          <input
            aria-label={copy.search}
            placeholder={copy.search}
          />

          <kbd>⌘ K</kbd>
        </div>

        <div className="kc-topbar-actions">
          <button
            type="button"
            className="kc-icon-button"
            aria-label={copy.notifications}
            title={copy.notifications}
          >
            <BellIcon width={17} height={17} />
          </button>

          <div className="kc-avatar">
            {initial}
          </div>
        </div>
      </div>

      <header className="kc-heading">
        <div>
          <span className="kc-heading-eyebrow">
            MASTEACON INTELLIGENCE
          </span>

          <h1>{copy.commandCenter}</h1>

          <p>
            {copy.subtitle}{" "}
            <strong>{copy.grounded}</strong>{" "}
            {copy.proven}
          </p>
        </div>

        <div className="kc-heading-status">
          <span
            className={
              documents.length === 0
                ? "kc-status-dot kc-status-dot-muted"
                : coveragePct === 100
                  ? "kc-status-dot"
                  : "kc-status-dot kc-status-dot-warning"
            }
          />

          <div>
            <span>{copy.welcome}</span>
            <strong>{healthLabel}</strong>
          </div>
        </div>
      </header>

      <section className="kc-primary-grid">
        <article className="kc-ask-card">
          <div className="kc-ask-ambient" />

          <div className="kc-ask-content">
            <div className="kc-card-heading">
              <div className="kc-card-heading-icon">
                <SparkleIcon width={17} height={17} />
              </div>

              <div>
                <h2>{copy.ask}</h2>
                <p>{copy.askDescription}</p>
              </div>
            </div>

            <form
              className="kc-ask-form"
              onSubmit={handleAsk}
            >
              <input
                value={prompt}
                onChange={(event) =>
                  setPrompt(event.target.value)
                }
                placeholder={copy.askPlaceholder}
              />

              <button
                type="submit"
                disabled={
                  !activeWorkspace ||
                  asking ||
                  !prompt.trim()
                }
                aria-label={copy.ask}
              >
                {asking ? (
                  <ClockIcon width={17} height={17} />
                ) : (
                  <SendIcon width={17} height={17} />
                )}
              </button>
            </form>

            <div className="kc-suggestion-row">
              <button
                type="button"
                onClick={() =>
                  setPrompt(suggestions[0])
                }
              >
                <SparkleIcon width={13} height={13} />
                {copy.deepResearch}
              </button>

              <button
                type="button"
                onClick={() =>
                  setPrompt(suggestions[1])
                }
              >
                <FileIcon width={13} height={13} />
                {copy.compare}
              </button>

              <button
                type="button"
                onClick={() =>
                  setPrompt(suggestions[2])
                }
              >
                <ChatIcon width={13} height={13} />
                {copy.summarize}
              </button>
            </div>

            {latestTurn && (
              <div className="kc-answer-panel">
                <div className="kc-answer-heading">
                  <div>
                    <span className="kc-answer-kicker">
                      MASTEACON
                    </span>

                    <strong>{copy.groundedAnswer}</strong>
                  </div>

                  <span className="kc-answer-verified">
                    <CheckIcon width={11} height={11} />
                    GROUNDED
                  </span>
                </div>

                <p className="kc-answer-question">
                  {latestTurn.question}
                </p>

                <p className="kc-answer-copy">
                  {latestTurn.response.answer}
                </p>

                <div className="kc-answer-evidence">
                  <span className="kc-answer-evidence-label">
                    {copy.sourcesUsed}
                  </span>

                  {latestTurn.response.sources.length > 0 ? (
                    <div className="kc-source-list">
                      {latestTurn.response.sources
                        .slice(0, 4)
                        .map((source, index) => (
                          <div
                            className="kc-source-chip"
                            key={`${source.document_id}-${source.chunk_index}-${index}`}
                          >
                            <FileIcon
                              width={12}
                              height={12}
                            />

                            <span>
                              <strong>
                                {source.filename}
                              </strong>

                              <small>
                                chunk {source.chunk_index}
                              </small>
                            </span>

                            <em>
                              {Math.round(
                                source.similarity_score *
                                  100,
                              )}
                              %
                            </em>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <p className="kc-no-source-note">
                      {copy.noSourcesReturned}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          <div
            className="kc-beacon-visual"
            aria-hidden="true"
          >
            <div className="kc-beacon-ring kc-beacon-ring-one" />
            <div className="kc-beacon-ring kc-beacon-ring-two" />
            <div className="kc-beacon-ring kc-beacon-ring-three" />

            <div className="kc-beacon-ray" />
            <div className="kc-beacon-core" />

            <div className="kc-beacon-logo">
              <Logo size={112} />
            </div>
          </div>
        </article>

        <article className="kc-card kc-health-card">
          <div className="kc-section-heading">
            <div>
              <span className="kc-section-kicker">
                KNOWLEDGE SYSTEM
              </span>
              <h2>{copy.health}</h2>
            </div>

            <CheckIcon width={17} height={17} />
          </div>

          <div className="kc-health-main">
            <div className="kc-health-ring-wrap">
              <svg
                className="kc-health-ring"
                viewBox="0 0 120 120"
              >
                <circle
                  className="kc-health-ring-track"
                  cx="60"
                  cy="60"
                  r="49"
                />

                <circle
                  className="kc-health-ring-progress"
                  cx="60"
                  cy="60"
                  r="49"
                  style={{
                    strokeDasharray: `${(
                      (coveragePct / 100) *
                      308
                    ).toFixed(1)} 308`,
                  }}
                />
              </svg>

              <div className="kc-health-ring-label">
                <strong>{coveragePct}%</strong>
                <span>{copy.indexedCoverage}</span>
              </div>
            </div>

            <div className="kc-health-metrics">
              <div>
                <span>{copy.indexedSources}</span>
                <strong>
                  {indexedCount}
                  <small> / {documents.length}</small>
                </strong>
              </div>

              <div>
                <span>{copy.conversations}</span>
                <strong>{conversations.length}</strong>
              </div>

              <div>
                <span>{copy.workspaces}</span>
                <strong>{workspaces.length}</strong>
              </div>
            </div>
          </div>

          <div className="kc-health-footer">
            <span
              className={
                documents.length === 0
                  ? "kc-status-dot kc-status-dot-muted"
                  : coveragePct === 100
                    ? "kc-status-dot"
                    : "kc-status-dot kc-status-dot-warning"
              }
            />

            <span>{healthLabel}</span>

            <button
              type="button"
              onClick={() => navigate("/documents")}
            >
              {copy.viewAll}
              <ChevronRightIcon width={13} height={13} />
            </button>
          </div>
        </article>
      </section>

      <section className="kc-secondary-grid">
        <article className="kc-card kc-library-card">
          <div className="kc-section-heading">
            <div>
              <span className="kc-section-kicker">
                {copy.recent}
              </span>

              <h2>{copy.library}</h2>
            </div>

            <button
              type="button"
              className="kc-text-button"
              onClick={() => navigate("/documents")}
            >
              {copy.viewAll}
              <ChevronRightIcon width={13} height={13} />
            </button>
          </div>

          {isLoading && (
            <div className="kc-empty-state">
              {copy.loading}
            </div>
          )}

          {!isLoading &&
            recentDocuments.length === 0 && (
              <div className="kc-empty-state">
                {copy.noDocuments}
              </div>
            )}

          {!isLoading &&
            recentDocuments.length > 0 && (
              <div className="kc-document-grid">
                {recentDocuments.map((document) => {
                  const fileType =
                    getDocumentType(document);

                  return (
                    <button
                      type="button"
                      className="kc-document-card"
                      key={document.id}
                      onClick={() =>
                        navigate("/documents")
                      }
                    >
                      <div
                        className={`kc-file-icon kc-file-icon-${fileType.toLowerCase()}`}
                      >
                        <FileIcon
                          width={18}
                          height={18}
                        />
                      </div>

                      <div className="kc-document-copy">
                        <strong>{document.filename}</strong>

                        <span>
                          {fileType}
                          <i />
                          {timeAgo(
                            document.created_at,
                            locale,
                          )}
                        </span>
                      </div>

                      <span
                        className={`kc-document-status kc-document-status-${document.status}`}
                      >
                        {document.status}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
        </article>

        <article className="kc-card kc-insights-card">
          <div className="kc-section-heading">
            <div>
              <span className="kc-section-kicker">
                LIVE WORKSPACE
              </span>

              <h2>{copy.signals}</h2>
            </div>

            <SparkleIcon width={17} height={17} />
          </div>

          <p className="kc-insights-description">
            {copy.signalDescription}
          </p>

          <div className="kc-insight-metrics">
            <div>
              <span>{copy.coverage}</span>
              <strong>{coveragePct}%</strong>

              <div className="kc-metric-bar">
                <span
                  style={{
                    width: `${coveragePct}%`,
                  }}
                />
              </div>
            </div>

            <div>
              <span>
                {copy.conversationsMetric}
              </span>
              <strong>{conversations.length}</strong>
            </div>

            <div>
              <span>{copy.workspaceMetric}</span>
              <strong>{workspaces.length}</strong>
            </div>
          </div>

          <div className="kc-insights-signal">
            <svg
              viewBox="0 0 320 78"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <defs>
                <linearGradient
                  id="kc-signal-fill"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor="currentColor"
                    stopOpacity="0.22"
                  />
                  <stop
                    offset="100%"
                    stopColor="currentColor"
                    stopOpacity="0"
                  />
                </linearGradient>
              </defs>

              <path
                className="kc-signal-fill"
                d="M0 62 C25 55 35 36 60 43 C88 51 99 67 126 50 C152 34 159 29 181 42 C210 58 218 25 247 31 C275 36 290 24 320 18 L320 78 L0 78 Z"
                fill="url(#kc-signal-fill)"
              />

              <path
                className="kc-signal-line"
                d="M0 62 C25 55 35 36 60 43 C88 51 99 67 126 50 C152 34 159 29 181 42 C210 58 218 25 247 31 C275 36 290 24 320 18"
              />
            </svg>
          </div>
        </article>
      </section>

      <section className="kc-quick-access">
        <div className="kc-quick-heading">
          <span>{copy.quickAccess}</span>
        </div>

        <button
          type="button"
          onClick={() => navigate("/documents")}
        >
          <span className="kc-quick-icon">
            <UploadIcon width={17} height={17} />
          </span>

          <span>
            <strong>{copy.upload}</strong>
            <small>{copy.uploadSub}</small>
          </span>

          <ChevronRightIcon width={14} height={14} />
        </button>

        <button
          type="button"
          onClick={() => navigate("/chat")}
        >
          <span className="kc-quick-icon">
            <ChatIcon width={17} height={17} />
          </span>

          <span>
            <strong>{copy.chat}</strong>
            <small>{copy.chatSub}</small>
          </span>

          <ChevronRightIcon width={14} height={14} />
        </button>

        <button
          type="button"
          onClick={() => navigate("/workspaces")}
        >
          <span className="kc-quick-icon">
            <FolderIcon width={17} height={17} />
          </span>

          <span>
            <strong>{copy.workspace}</strong>
            <small>{copy.workspaceSub}</small>
          </span>

          <ChevronRightIcon width={14} height={14} />
        </button>

        <button
          type="button"
          onClick={() => navigate("/agent")}
        >
          <span className="kc-quick-icon">
            <RocketIcon width={17} height={17} />
          </span>

          <span>
            <strong>{copy.agent}</strong>
            <small>{copy.agentSub}</small>
          </span>

          <ChevronRightIcon width={14} height={14} />
        </button>
      </section>

      <section className="kc-bottom-grid">
        <article className="kc-card kc-trace-card">
          <div className="kc-section-heading">
            <div>
              <span className="kc-section-kicker">
                TRANSPARENT BY DESIGN
              </span>

              <h2>{copy.trace}</h2>
              <p>{copy.traceDescription}</p>
            </div>

            <div className="kc-trace-actions">
              <span
                className={
                  latestTurn
                    ? "kc-trace-status kc-trace-status-complete"
                    : "kc-trace-status"
                }
              >
                <span className="kc-status-dot" />

                {latestTurn
                  ? copy.completed
                  : copy.ready}
              </span>

              <button
                type="button"
                className="kc-text-button"
                onClick={() => navigate("/agent")}
              >
                {copy.fullTrace}
                <ChevronRightIcon
                  width={13}
                  height={13}
                />
              </button>
            </div>
          </div>

          {latestTurn && (
            <div className="kc-last-query">
              <span>
                {locale === "tr"
                  ? "SON SORU"
                  : "LATEST QUERY"}
              </span>

              <p>{latestTurn.question}</p>
            </div>
          )}

          <div className="kc-trace-flow">
            <div className="kc-trace-step">
              <div className="kc-trace-node">
                <SearchIcon width={18} height={18} />
              </div>

              <div>
                <strong>1. {copy.understand}</strong>
                <p>
                  {latestTurn
                    ? latestTurn.question
                    : copy.understandReady}
                </p>
              </div>
            </div>

            <div className="kc-trace-connector" />

            <div className="kc-trace-step">
              <div className="kc-trace-node">
                <FileIcon width={18} height={18} />
              </div>

              <div>
                <strong>2. {copy.retrieve}</strong>
                <p>
                  {indexedCount > 0
                    ? locale === "tr"
                      ? `${indexedCount} indeksli kaynak kullanılabilir.`
                      : `${indexedCount} indexed sources available.`
                    : copy.retrieveReady}
                </p>
              </div>
            </div>

            <div className="kc-trace-connector" />

            <div className="kc-trace-step">
              <div className="kc-trace-node">
                <CheckIcon width={18} height={18} />
              </div>

              <div>
                <strong>3. {copy.tools}</strong>
                <p>
                  {latestTurn &&
                  latestTurn.response.sources.length > 0
                    ? locale === "tr"
                      ? `${latestTurn.response.sources.length} kaynak parçası yanıtı destekliyor.`
                      : `${latestTurn.response.sources.length} source passages support the answer.`
                    : copy.toolsReady}
                </p>
              </div>
            </div>

            <div className="kc-trace-connector" />

            <div className="kc-trace-step">
              <div className="kc-trace-node">
                <SparkleIcon width={18} height={18} />
              </div>

              <div>
                <strong>4. {copy.synthesize}</strong>
                <p>{copy.synthesizeReady}</p>
              </div>
            </div>

            <div className="kc-trace-connector" />

            <div className="kc-trace-step">
              <div className="kc-trace-node">
                <CheckIcon width={18} height={18} />
              </div>

              <div>
                <strong>5. {copy.answer}</strong>
                <p>
                  {latestTurn
                    ? latestTurn.response.answer
                    : copy.answerReady}
                </p>
              </div>
            </div>
          </div>

          {latestTurn &&
            latestTurn.response.sources.length > 0 && (
              <div className="kc-tool-strip">
                {latestTurn.response.sources
                  .slice(0, 5)
                  .map((source, index) => (
                    <span
                      key={`${source.document_id}-${source.chunk_index}-${index}`}
                      className="kc-tool-pill kc-tool-pill-success"
                    >
                      <CheckIcon
                        width={11}
                        height={11}
                      />

                      {source.filename}
                      {" · "}
                      {Math.round(
                        source.similarity_score * 100,
                      )}
                      %
                    </span>
                  ))}
              </div>
            )}
        </article>

        <article className="kc-card kc-activity-card">
          <div className="kc-section-heading">
            <div>
              <span className="kc-section-kicker">
                TIMELINE
              </span>

              <h2>{copy.activity}</h2>
            </div>

            <ClockIcon width={17} height={17} />
          </div>

          {activity.length === 0 && (
            <div className="kc-empty-state">
              {copy.noActivity}
            </div>
          )}

          {activity.map((item) => (
            <div
              className="kc-activity-row"
              key={item.id}
            >
              <span className="kc-activity-icon">
                {item.icon}
              </span>

              <div>
                <strong>{item.label}</strong>

                <span>
                  {item.detail}
                  <i />
                  {timeAgo(item.at, locale)}
                </span>
              </div>
            </div>
          ))}
        </article>
      </section>
    </div>
  );
}
