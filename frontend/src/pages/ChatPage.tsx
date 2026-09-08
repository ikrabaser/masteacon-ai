import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import * as api from "../api/endpoints";

import type {
  ConversationDetailResponse,
  ConversationResponse,
  MessageResponse,
  SourceItem,
} from "../api/types";

import {
  ChatIcon,
  CheckIcon,
  ClockIcon,
  FileIcon,
  PlusIcon,
  SearchIcon,
  SendIcon,
  SparkleIcon,
  WarningIcon,
} from "../components/icons";

import { Logo } from "../components/Logo";

import { useAuth } from "../context/AuthContext";
import { useI18n } from "../context/I18nContext";
import { useWorkspace } from "../context/WorkspaceContext";

function formatConversationDate(
  iso: string,
  locale: string,
) {
  const date = new Date(iso);

  return new Intl.DateTimeFormat(
    locale === "tr" ? "tr-TR" : "en-US",
    {
      month: "short",
      day: "numeric",
    },
  ).format(date);
}

function formatMessageTime(
  iso: string,
  locale: string,
) {
  const date = new Date(iso);

  return new Intl.DateTimeFormat(
    locale === "tr" ? "tr-TR" : "en-US",
    {
      hour: "2-digit",
      minute: "2-digit",
    },
  ).format(date);
}

export function ChatPage() {
  const { user } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const { locale } = useI18n();

  const userInitial = (user?.email || "U")
    .charAt(0)
    .toUpperCase();

  const [conversations, setConversations] =
    useState<ConversationResponse[]>([]);

  const [
    activeConversation,
    setActiveConversation,
  ] =
    useState<ConversationDetailResponse | null>(
      null,
    );

  const [conversationSearch, setConversationSearch] =
    useState("");

  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] =
    useState(false);

  const [isCreating, setIsCreating] =
    useState(false);

  const [isOpening, setIsOpening] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [lastSources, setLastSources] =
    useState<Record<number, SourceItem[]>>({});

  const messagesEndRef =
    useRef<HTMLDivElement>(null);

  const copy =
    locale === "tr"
      ? {
          eyebrow: "GROUNDED INTELLIGENCE",
          title: "Masteacon'a Sor",
          subtitle:
            "Çalışma alanınızdaki güvenilir bilgiyle konuşun ve kaynaklı yanıtlar alın.",
          conversations: "KONUŞMALAR",
          search: "Konuşmalarda ara...",
          newConversation: "Yeni konuşma",
          creating: "Oluşturuluyor...",
          noConversations:
            "Henüz konuşma yok.",
          workspace: "AKTİF ÇALIŞMA ALANI",
          ready: "Knowledge ready",
          conversation: "Conversation",
          emptyEyebrow: "MASTEACON INTELLIGENCE",
          emptyTitle:
            "Bilginizle bir konuşma başlatın.",
          emptyDescription:
            "Masteacon, aktif çalışma alanınızdaki indeksli kaynakları kullanarak yanıt üretir.",
          emptyAction: "Yeni konuşma başlat",
          emptyMessages:
            "İlk sorunuzu sorarak bu konuşmayı başlatın.",
          you: "SİZ",
          assistant: "MASTEACON",
          grounded: "GROUNDED",
          sourcesUsed: "KULLANILAN KAYNAKLAR",
          chunk: "parça",
          placeholder:
            "Bilginiz hakkında bir soru sorun...",
          send: "Gönder",
          thinking: "Masteacon düşünüyor...",
          helper:
            "Enter ile gönder · Shift + Enter ile yeni satır",
          sourceNote:
            "Yanıtlar indekslenmiş çalışma alanı bilgisinden temellendirilir.",
          noWorkspaceTitle:
            "Önce bir çalışma alanı oluşturun",
          noWorkspaceDescription:
            "Masteacon ile konuşmak için aktif bir çalışma alanına ihtiyacınız var.",
          openFailed:
            "Konuşma açılamadı.",
          createFailed:
            "Konuşma oluşturulamadı.",
          sendFailed:
            "Mesaj gönderilemedi.",
        }
      : {
          eyebrow: "GROUNDED INTELLIGENCE",
          title: "Ask Masteacon",
          subtitle:
            "Talk to your trusted workspace knowledge and receive grounded answers with evidence.",
          conversations: "CONVERSATIONS",
          search: "Search conversations...",
          newConversation: "New conversation",
          creating: "Creating...",
          noConversations:
            "No conversations yet.",
          workspace: "ACTIVE WORKSPACE",
          ready: "Knowledge ready",
          conversation: "Conversation",
          emptyEyebrow: "MASTEACON INTELLIGENCE",
          emptyTitle:
            "Start a conversation with your knowledge.",
          emptyDescription:
            "Masteacon answers using indexed sources from your active workspace.",
          emptyAction: "Start new conversation",
          emptyMessages:
            "Ask your first question to begin this conversation.",
          you: "YOU",
          assistant: "MASTEACON",
          grounded: "GROUNDED",
          sourcesUsed: "SOURCES USED",
          chunk: "chunk",
          placeholder:
            "Ask a question about your knowledge...",
          send: "Send",
          thinking: "Masteacon is thinking...",
          helper:
            "Enter to send · Shift + Enter for a new line",
          sourceNote:
            "Answers are grounded in indexed workspace knowledge.",
          noWorkspaceTitle:
            "Create a workspace first",
          noWorkspaceDescription:
            "You need an active workspace before starting a conversation with Masteacon.",
          openFailed:
            "Failed to open conversation.",
          createFailed:
            "Failed to create conversation.",
          sendFailed:
            "Failed to send message.",
        };

  const loadConversations =
    useCallback(async () => {
      if (!activeWorkspace) {
        setConversations([]);
        return [];
      }

      const list =
        await api.listConversations(
          activeWorkspace.id,
        );

      const sorted = [...list].sort(
        (a, b) =>
          new Date(b.updated_at).getTime() -
          new Date(a.updated_at).getTime(),
      );

      setConversations(sorted);

      return sorted;
    }, [activeWorkspace]);

  const openConversation =
    useCallback(
      async (id: number) => {
        setError(null);
        setIsOpening(true);

        try {
          const detail =
            await api.getConversation(id);

          setActiveConversation(detail);
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : copy.openFailed,
          );
        } finally {
          setIsOpening(false);
        }
      },
      [copy.openFailed],
    );

  useEffect(() => {
    let cancelled = false;

    setActiveConversation(null);
    setLastSources({});
    setError(null);

    if (!activeWorkspace) {
      setConversations([]);
      return;
    }

    loadConversations()
      .then(async (list) => {
        if (
          cancelled ||
          list.length === 0
        ) {
          return;
        }

        const detail =
          await api.getConversation(
            list[0].id,
          );

        if (!cancelled) {
          setActiveConversation(detail);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : copy.openFailed,
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    activeWorkspace,
    copy.openFailed,
    loadConversations,
  ]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [
    activeConversation?.messages.length,
    isSending,
  ]);

  const visibleConversations =
    useMemo(() => {
      const query = conversationSearch
        .trim()
        .toLowerCase();

      if (!query) {
        return conversations;
      }

      return conversations.filter(
        (conversation) =>
          conversation.title
            .toLowerCase()
            .includes(query),
      );
    }, [
      conversationSearch,
      conversations,
    ]);

  async function startNewConversation() {
    if (
      !activeWorkspace ||
      isCreating
    ) {
      return;
    }

    setError(null);
    setIsCreating(true);

    try {
      const conversation =
        await api.createConversation(
          activeWorkspace.id,
          "New Conversation",
        );

      await loadConversations();
      await openConversation(
        conversation.id,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : copy.createFailed,
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSend(
    event: React.FormEvent,
  ) {
    event.preventDefault();

    if (
      !draft.trim() ||
      !activeConversation ||
      isSending
    ) {
      return;
    }

    const content = draft.trim();

    setDraft("");
    setIsSending(true);
    setError(null);

    const optimisticUser: MessageResponse = {
      id: -Date.now(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setActiveConversation((previous) =>
      previous
        ? {
            ...previous,
            messages: [
              ...previous.messages,
              optimisticUser,
            ],
          }
        : previous,
    );

    try {
      const response =
        await api.postMessage(
          activeConversation.id,
          content,
        );

      setActiveConversation((previous) => {
        if (!previous) {
          return previous;
        }

        const withoutOptimistic =
          previous.messages.filter(
            (message) =>
              message.id !==
              optimisticUser.id,
          );

        return {
          ...previous,
          updated_at:
            response.assistant_message
              .created_at,
          messages: [
            ...withoutOptimistic,
            response.user_message,
            response.assistant_message,
          ],
        };
      });

      setLastSources((previous) => ({
        ...previous,
        [response.assistant_message.id]:
          response.sources,
      }));

      await loadConversations();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : copy.sendFailed,
      );

      setActiveConversation((previous) =>
        previous
          ? {
              ...previous,
              messages:
                previous.messages.filter(
                  (message) =>
                    message.id !==
                    optimisticUser.id,
                ),
            }
          : previous,
      );
    } finally {
      setIsSending(false);
    }
  }

  if (!activeWorkspace) {
    return (
      <div className="ask-page">
        <header className="ask-page-header">
          <div>
            <span className="ask-page-eyebrow">
              {copy.eyebrow}
            </span>

            <h1>{copy.title}</h1>

            <p>{copy.subtitle}</p>
          </div>
        </header>

        <section className="ask-no-workspace">
          <div className="ask-no-workspace-mark">
            <Logo size={66} />
          </div>

          <span>
            MASTEACON KNOWLEDGE
          </span>

          <h2>
            {copy.noWorkspaceTitle}
          </h2>

          <p>
            {copy.noWorkspaceDescription}
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="ask-page">
      <header className="ask-page-header">
        <div>
          <span className="ask-page-eyebrow">
            {copy.eyebrow}
          </span>

          <h1>{copy.title}</h1>

          <p>{copy.subtitle}</p>
        </div>

        <div className="ask-workspace-context">
          <span>{copy.workspace}</span>

          <strong>
            {activeWorkspace.name}
          </strong>

          <small>
            <span className="ask-ready-dot" />
            {copy.ready}
          </small>
        </div>
      </header>

      {error && (
        <div className="error-banner ask-error">
          <WarningIcon
            width={15}
            height={15}
          />
          <span>{error}</span>
        </div>
      )}

      <section className="ask-shell">
        <aside className="ask-conversations">
          <div className="ask-conversation-header">
            <div>
              <span>
                {copy.conversations}
              </span>

              <strong>
                {conversations.length}
              </strong>
            </div>

            <button
              type="button"
              className="ask-new-conversation"
              onClick={
                startNewConversation
              }
              disabled={isCreating}
              title={
                copy.newConversation
              }
            >
              {isCreating ? (
                <ClockIcon
                  width={15}
                  height={15}
                />
              ) : (
                <PlusIcon
                  width={15}
                  height={15}
                />
              )}
            </button>
          </div>

          <button
            type="button"
            className="ask-new-conversation-wide"
            onClick={
              startNewConversation
            }
            disabled={isCreating}
          >
            {isCreating ? (
              <ClockIcon
                width={14}
                height={14}
              />
            ) : (
              <PlusIcon
                width={14}
                height={14}
              />
            )}

            {isCreating
              ? copy.creating
              : copy.newConversation}
          </button>

          <div className="ask-conversation-search">
            <SearchIcon
              width={14}
              height={14}
            />

            <input
              value={
                conversationSearch
              }
              onChange={(event) =>
                setConversationSearch(
                  event.target.value,
                )
              }
              placeholder={copy.search}
            />
          </div>

          <div className="ask-conversation-list">
            {visibleConversations.length ===
              0 && (
              <div className="ask-conversation-empty">
                <ChatIcon
                  width={19}
                  height={19}
                />

                <span>
                  {copy.noConversations}
                </span>
              </div>
            )}

            {visibleConversations.map(
              (conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  className={
                    activeConversation?.id ===
                    conversation.id
                      ? "ask-conversation-item active"
                      : "ask-conversation-item"
                  }
                  onClick={() =>
                    openConversation(
                      conversation.id,
                    )
                  }
                >
                  <span className="ask-conversation-icon">
                    <ChatIcon
                      width={14}
                      height={14}
                    />
                  </span>

                  <span className="ask-conversation-copy">
                    <strong>
                      {
                        conversation.title
                      }
                    </strong>

                    <small>
                      {formatConversationDate(
                        conversation.updated_at,
                        locale,
                      )}
                    </small>
                  </span>

                  {activeConversation?.id ===
                    conversation.id && (
                    <span className="ask-conversation-active-dot" />
                  )}
                </button>
              ),
            )}
          </div>

          <div className="ask-conversation-footer">
            <SparkleIcon
              width={13}
              height={13}
            />

            <span>
              {copy.sourceNote}
            </span>
          </div>
        </aside>

        <main className="ask-thread">
          {!activeConversation && (
            <div className="ask-thread-empty">
              <div className="ask-empty-mark">
                <Logo size={88} />
              </div>

              <span>
                {copy.emptyEyebrow}
              </span>

              <h2>
                {copy.emptyTitle}
              </h2>

              <p>
                {copy.emptyDescription}
              </p>

              <button
                type="button"
                onClick={
                  startNewConversation
                }
                disabled={isCreating}
              >
                <PlusIcon
                  width={14}
                  height={14}
                />

                {copy.emptyAction}
              </button>
            </div>
          )}

          {activeConversation && (
            <>
              <div className="ask-thread-header">
                <div>
                  <span>
                    {copy.conversation}
                  </span>

                  <h2>
                    {
                      activeConversation.title
                    }
                  </h2>
                </div>

                <div className="ask-thread-status">
                  <span className="ask-ready-dot" />

                  <span>
                    {copy.ready}
                  </span>
                </div>
              </div>

              <div className="ask-messages">
                {activeConversation.messages
                  .length === 0 && (
                  <div className="ask-messages-empty">
                    <SparkleIcon
                      width={20}
                      height={20}
                    />

                    <span>
                      {copy.emptyMessages}
                    </span>
                  </div>
                )}

                {activeConversation.messages.map(
                  (message) => {
                    const sources =
                      message.role ===
                      "assistant"
                        ? lastSources[
                            message.id
                          ] ?? []
                        : [];

                    return (
                      <article
                        key={message.id}
                        className={`ask-message ask-message-${message.role}`}
                      >
                        <div className="ask-message-rail">
                          {message.role ===
                          "assistant" ? (
                            <div className="ask-assistant-avatar">
                              <Logo
                                size={29}
                              />
                            </div>
                          ) : (
                            <div className="ask-user-avatar">
                              {userInitial}
                            </div>
                          )}
                        </div>

                        <div className="ask-message-body">
                          <div className="ask-message-meta">
                            <strong>
                              {message.role ===
                              "assistant"
                                ? copy.assistant
                                : copy.you}
                            </strong>

                            <span>
                              {formatMessageTime(
                                message.created_at,
                                locale,
                              )}
                            </span>

                            {message.role ===
                              "assistant" &&
                              sources.length >
                                0 && (
                                <em>
                                  <CheckIcon
                                    width={
                                      10
                                    }
                                    height={
                                      10
                                    }
                                  />
                                  {
                                    copy.grounded
                                  }
                                </em>
                              )}
                          </div>

                          <div className="ask-message-content">
                            {message.content}
                          </div>

                          {message.role ===
                            "assistant" &&
                            sources.length >
                              0 && (
                              <div className="ask-message-sources">
                                <div className="ask-source-heading">
                                  <span>
                                    {
                                      copy.sourcesUsed
                                    }
                                  </span>

                                  <strong>
                                    {
                                      sources.length
                                    }
                                  </strong>
                                </div>

                                <div className="ask-source-grid">
                                  {sources.map(
                                    (
                                      source,
                                      index,
                                    ) => (
                                      <div
                                        className="ask-source-card"
                                        key={`${source.document_id}-${source.chunk_index}-${index}`}
                                      >
                                        <span className="ask-source-icon">
                                          <FileIcon
                                            width={
                                              14
                                            }
                                            height={
                                              14
                                            }
                                          />
                                        </span>

                                        <span className="ask-source-copy">
                                          <strong>
                                            {
                                              source.filename
                                            }
                                          </strong>

                                          <small>
                                            {
                                              copy.chunk
                                            }{" "}
                                            {
                                              source.chunk_index
                                            }
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
                                    ),
                                  )}
                                </div>
                              </div>
                            )}
                        </div>
                      </article>
                    );
                  },
                )}

                {isSending && (
                  <article className="ask-message ask-message-assistant">
                    <div className="ask-message-rail">
                      <div className="ask-assistant-avatar">
                        <Logo size={29} />
                      </div>
                    </div>

                    <div className="ask-message-body">
                      <div className="ask-message-meta">
                        <strong>
                          {copy.assistant}
                        </strong>
                      </div>

                      <div className="ask-thinking">
                        <span />
                        <span />
                        <span />

                        <em>
                          {copy.thinking}
                        </em>
                      </div>
                    </div>
                  </article>
                )}

                <div
                  ref={messagesEndRef}
                />
              </div>

              <form
                className="ask-composer"
                onSubmit={handleSend}
              >
                <div className="ask-composer-field">
                  <SparkleIcon
                    width={16}
                    height={16}
                  />

                  <textarea
                    rows={1}
                    placeholder={
                      copy.placeholder
                    }
                    value={draft}
                    onChange={(event) =>
                      setDraft(
                        event.target.value,
                      )
                    }
                    onKeyDown={(
                      event,
                    ) => {
                      if (
                        event.key ===
                          "Enter" &&
                        !event.shiftKey
                      ) {
                        event.preventDefault();

                        handleSend(
                          event,
                        );
                      }
                    }}
                  />

                  <button
                    type="submit"
                    disabled={
                      isSending ||
                      !draft.trim()
                    }
                    aria-label={copy.send}
                  >
                    {isSending ? (
                      <ClockIcon
                        width={16}
                        height={16}
                      />
                    ) : (
                      <SendIcon
                        width={16}
                        height={16}
                      />
                    )}
                  </button>
                </div>

                <div className="ask-composer-footer">
                  <span>
                    {copy.helper}
                  </span>

                  <span>
                    <CheckIcon
                      width={10}
                      height={10}
                    />
                    {copy.sourceNote}
                  </span>
                </div>
              </form>
            </>
          )}

          {isOpening && (
            <div className="ask-opening-overlay">
              <span />
            </div>
          )}
        </main>
      </section>
    </div>
  );
}
