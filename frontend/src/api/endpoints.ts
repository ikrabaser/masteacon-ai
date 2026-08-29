import { apiRequest } from "./client";
import type {
  AgentAskResponse,
  AskResponse,
  ConversationDetailResponse,
  ConversationResponse,
  DocumentResponse,
  DocumentUploadResponse,
  MessageCreateResponse,
  ObservabilitySummaryResponse,
  SearchResponse,
  TokenResponse,
  UserResponse,
  WorkspaceResponse,
} from "./types";

// --- Auth ---

export function register(
  email: string,
  password: string,
  website = "",
  turnstileToken = "",
): Promise<TokenResponse> {
  return apiRequest("/api/v1/auth/register", {
    method: "POST",
    json: {
      email,
      password,
      website,
      turnstile_token: turnstileToken,
    },
  });
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiRequest("/api/v1/auth/login", { method: "POST", json: { email, password } });
}

export function getCurrentUser(): Promise<UserResponse> {
  return apiRequest("/api/v1/auth/me");
}

// --- Workspaces ---

export function listWorkspaces(): Promise<WorkspaceResponse[]> {
  return apiRequest("/api/v1/workspaces");
}

export function createWorkspace(name: string): Promise<WorkspaceResponse> {
  return apiRequest("/api/v1/workspaces", { method: "POST", json: { name } });
}

export function getWorkspace(workspaceId: number): Promise<WorkspaceResponse> {
  return apiRequest(`/api/v1/workspaces/${workspaceId}`);
}

// --- Documents ---

export function listDocuments(workspaceId: number): Promise<DocumentResponse[]> {
  return apiRequest("/api/v1/documents", { query: { workspace_id: workspaceId } });
}

export function getDocument(documentId: number, workspaceId: number): Promise<DocumentResponse> {
  return apiRequest(`/api/v1/documents/${documentId}`, { query: { workspace_id: workspaceId } });
}

export function uploadDocument(file: File, workspaceId: number): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("workspace_id", String(workspaceId));
  return apiRequest("/api/v1/documents", { method: "POST", formData });
}

// --- Search & Ask ---

export function search(
  workspaceId: number,
  query: string,
  limit = 5,
  documentId?: number,
): Promise<SearchResponse> {
  return apiRequest("/api/v1/search", {
    method: "POST",
    json: { workspace_id: workspaceId, query, limit, document_id: documentId },
  });
}

export function ask(workspaceId: number, question: string): Promise<AskResponse> {
  return apiRequest("/api/v1/ask", { method: "POST", json: { workspace_id: workspaceId, question } });
}

// --- Conversations ---

export function listConversations(workspaceId: number): Promise<ConversationResponse[]> {
  return apiRequest("/api/v1/conversations", { query: { workspace_id: workspaceId } });
}

export function createConversation(workspaceId: number, title: string): Promise<ConversationResponse> {
  return apiRequest("/api/v1/conversations", { method: "POST", json: { workspace_id: workspaceId, title } });
}

export function getConversation(conversationId: number): Promise<ConversationDetailResponse> {
  return apiRequest(`/api/v1/conversations/${conversationId}`);
}

export function postMessage(conversationId: number, content: string): Promise<MessageCreateResponse> {
  return apiRequest(`/api/v1/conversations/${conversationId}/messages`, { method: "POST", json: { content } });
}

// --- Agent ---

export function agentAsk(question: string): Promise<AgentAskResponse> {
  return apiRequest("/api/v1/agent/ask", { method: "POST", json: { question } });
}


export interface EmailVerificationResponse {
  verified: boolean;
  message: string;
}

export interface ResendVerificationResponse {
  message: string;
}

export function verifyEmail(
  token: string,
): Promise<EmailVerificationResponse> {
  return apiRequest("/api/v1/auth/verify-email", {
    method: "POST",
    json: { token },
  });
}

export function resendVerification(
  email: string,
): Promise<ResendVerificationResponse> {
  return apiRequest("/api/v1/auth/resend-verification", {
    method: "POST",
    json: { email },
  });
}

// --- Observability ---

export function getObservabilitySummary(
  days = 7,
): Promise<ObservabilitySummaryResponse> {
  return apiRequest("/api/v1/observability/summary", {
    query: { days },
  });
}
