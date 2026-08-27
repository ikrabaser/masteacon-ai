"""Tool: semantically search a workspace's indexed knowledge for a query."""
from typing import Any

from pydantic import BaseModel, Field

from app.services.retrieval_service import RetrievalService
from app.services.workspace_service import WorkspaceService
from app.tools.base import BaseTool, ToolContext

_MAX_RESULTS = 5


class SearchKnowledgeArgs(BaseModel):
    workspace_id: int = Field(description="The workspace to search within.")
    query: str = Field(
        description="The search query — a question or set of keywords.", min_length=1, max_length=1000
    )


class SearchKnowledgeTool(BaseTool):
    """Searches a workspace's indexed document chunks for content relevant to a query.

    Unlike list_documents/get_document (metadata only), this actually surfaces
    matching passages — the same retrieval pipeline (vector/hybrid search plus
    reranking, whichever is configured) used by /ask — so the agent can look
    something up inside a document's content instead of only listing or
    summarizing whole documents.
    """

    name = "search_knowledge"
    description = (
        "Search the workspace's indexed documents for passages relevant to a query. "
        "Returns matching excerpts with their source document and a relevance score. "
        "Use this when you need specific information from inside a document, not just "
        "its filename or a whole-document summary."
    )
    args_model = SearchKnowledgeArgs

    def __init__(self, retrieval_service: RetrievalService, workspace_service: WorkspaceService) -> None:
        self._retrieval_service = retrieval_service
        self._workspace_service = workspace_service

    async def execute(self, args: SearchKnowledgeArgs, context: ToolContext) -> dict[str, Any]:
        await self._workspace_service.get_owned_workspace(args.workspace_id, context.user_id)

        chunks = await self._retrieval_service.search(args.query, workspace_id=args.workspace_id, limit=_MAX_RESULTS)
        return {
            "query": args.query,
            "results": [
                {
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "relevance_score": chunk.similarity_score,
                }
                for chunk in chunks
            ],
        }
