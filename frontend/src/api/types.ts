// Types mirroring the backend Pydantic schemas (see app/schemas/*.py).

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceResponse {
  id: number;
  name: string;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export type DocumentStatus = "uploaded" | "processing" | "indexed" | "failed";

export interface DocumentResponse {
  id: number;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse extends DocumentResponse {
  chunk_count: number;
}

export interface SearchResultItem {
  document_id: number;
  filename: string;
  chunk_index: number;
  content: string;
  similarity_score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
}

export interface SourceItem {
  document_id: number;
  filename: string;
  chunk_index: number;
  similarity_score: number;
}

export interface AskResponse {
  answer: string;
  sources: SourceItem[];
}

export type MessageRole = "user" | "assistant";

export interface MessageResponse {
  id: number;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ConversationResponse {
  id: number;
  workspace_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
}

export interface MessageCreateResponse {
  user_message: MessageResponse;
  assistant_message: MessageResponse;
  sources: SourceItem[];
}

export interface ToolCallSummary {
  name: string;
  success: boolean;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface AgentAskResponse {
  answer: string;
  tool_calls: ToolCallSummary[];
}

export interface DailyCountItem {
  date: string;
  count: number;
}

export interface ToolUsageItem {
  tool_name: string;
  count: number;
}

export interface ObservabilitySummaryResponse {
  days: number;
  total_requests: number;
  success_rate: number;
  avg_duration_ms: number;
  events_by_type: Record<string, number>;
  daily_counts: DailyCountItem[];
  top_tools: ToolUsageItem[];
}
