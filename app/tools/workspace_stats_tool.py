"""Tool: aggregate document/indexing stats for a workspace."""
from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from app.services.document_service import DocumentService
from app.services.workspace_service import WorkspaceService
from app.tools.base import BaseTool, ToolContext


class WorkspaceStatsArgs(BaseModel):
    workspace_id: int = Field(description="The workspace to summarize.")


class WorkspaceStatsTool(BaseTool):
    """Reports document counts by indexing status for a workspace.

    Lets the agent answer questions like "how many documents do I have" or
    "are all my uploads indexed yet" without enumerating and counting the
    full document list itself.
    """

    name = "workspace_stats"
    description = (
        "Get aggregate stats for a workspace: total document count and how many are "
        "indexed, still processing, uploaded (not yet processed), or failed."
    )
    args_model = WorkspaceStatsArgs

    def __init__(self, document_service: DocumentService, workspace_service: WorkspaceService) -> None:
        self._document_service = document_service
        self._workspace_service = workspace_service

    async def execute(self, args: WorkspaceStatsArgs, context: ToolContext) -> dict[str, Any]:
        await self._workspace_service.get_owned_workspace(args.workspace_id, context.user_id)
        documents = await self._document_service.list_documents(args.workspace_id)

        by_status = Counter(document.status.value for document in documents)
        return {
            "workspace_id": args.workspace_id,
            "total_documents": len(documents),
            "by_status": dict(by_status),
        }
