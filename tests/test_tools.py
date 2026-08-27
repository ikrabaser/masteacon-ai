"""Tests for individual tools, the registry, and ToolExecutionService's safety net."""
import pytest

from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.tool_execution_service import ToolExecutionService
from app.services.workspace_service import WorkspaceService
from app.tools.base import ToolContext
from app.tools.get_document_tool import GetDocumentTool
from app.tools.list_documents_tool import ListDocumentsTool
from app.tools.list_workspaces_tool import ListWorkspacesTool
from app.tools.registry import ToolRegistry
from app.tools.search_knowledge_tool import SearchKnowledgeTool
from tests.fakes import (
    FakeChunkRepository,
    FakeDocumentRepository,
    FakeEmbeddingProvider,
    FakeWorkspaceRepository,
)

OWNER_ID = 1
OTHER_USER_ID = 2


async def _seed() -> tuple[WorkspaceService, DocumentService, int]:
    workspace_repository = FakeWorkspaceRepository()
    workspace_service = WorkspaceService(workspace_repository)
    workspace = await workspace_service.create(name="Mine", owner_id=OWNER_ID)

    document_repository = FakeDocumentRepository()
    from app.services.chunking_service import ChunkingService
    from app.services.document_indexing_service import DocumentIndexingService
    from app.services.embedding_service import EmbeddingService
    from app.services.parsing_service import ParsingService
    from tests.fakes import FakeChunkRepository, FakeEmbeddingProvider, FakeIndexingDispatcher

    chunk_repository = FakeChunkRepository()
    indexing_service = DocumentIndexingService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        parsing_service=ParsingService(),
        chunking_service=ChunkingService(chunk_size=50, chunk_overlap=10),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        upload_directory="/tmp/tool-test-uploads",
    )
    document_service = DocumentService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        indexing_dispatcher=FakeIndexingDispatcher(indexing_service),
        upload_directory="/tmp/tool-test-uploads",
        max_upload_size_mb=1,
    )
    return workspace_service, document_service, workspace.id


@pytest.mark.asyncio
async def test_list_workspaces_tool_only_returns_the_callers_workspaces() -> None:
    workspace_service, _, _ = await _seed()
    await workspace_service.create(name="Someone else's", owner_id=OTHER_USER_ID)
    tool = ListWorkspacesTool(workspace_service)

    result = await tool.execute(tool.args_model(), ToolContext(user_id=OWNER_ID))

    assert len(result["workspaces"]) == 1
    assert result["workspaces"][0]["name"] == "Mine"


@pytest.mark.asyncio
async def test_list_documents_tool_rejects_a_non_owner(tmp_path) -> None:
    workspace_service, document_service, workspace_id = await _seed()
    tool = ListDocumentsTool(document_service, workspace_service)

    from app.core.exceptions import WorkspaceNotFoundError

    with pytest.raises(WorkspaceNotFoundError):
        await tool.execute(tool.args_model(workspace_id=workspace_id), ToolContext(user_id=OTHER_USER_ID))


@pytest.mark.asyncio
async def test_get_document_tool_rejects_a_non_owner() -> None:
    workspace_service, document_service, workspace_id = await _seed()
    document = await document_service._documents.create(
        filename="a.txt", stored_filename="x.txt", content_type="text/plain", workspace_id=workspace_id
    )
    tool = GetDocumentTool(document_service, workspace_service)

    from app.core.exceptions import WorkspaceNotFoundError

    with pytest.raises(WorkspaceNotFoundError):
        await tool.execute(
            tool.args_model(workspace_id=workspace_id, document_id=document.id),
            ToolContext(user_id=OTHER_USER_ID),
        )


@pytest.mark.asyncio
async def test_workspace_stats_tool_reports_counts_by_status() -> None:
    workspace_service, document_service, workspace_id = await _seed()
    await document_service._documents.create(
        filename="a.txt", stored_filename="a1.txt", content_type="text/plain", workspace_id=workspace_id
    )
    doc2 = await document_service._documents.create(
        filename="b.txt", stored_filename="b1.txt", content_type="text/plain", workspace_id=workspace_id
    )
    from app.models.document import DocumentStatus

    await document_service._documents.update_status(doc2, DocumentStatus.INDEXED)

    from app.tools.workspace_stats_tool import WorkspaceStatsTool

    tool = WorkspaceStatsTool(document_service, workspace_service)
    result = await tool.execute(tool.args_model(workspace_id=workspace_id), ToolContext(user_id=OWNER_ID))

    assert result["total_documents"] == 2
    assert result["by_status"]["indexed"] == 1
    assert result["by_status"]["uploaded"] == 1


@pytest.mark.asyncio
async def test_workspace_stats_tool_rejects_a_non_owner() -> None:
    workspace_service, document_service, workspace_id = await _seed()
    from app.core.exceptions import WorkspaceNotFoundError
    from app.tools.workspace_stats_tool import WorkspaceStatsTool

    tool = WorkspaceStatsTool(document_service, workspace_service)

    with pytest.raises(WorkspaceNotFoundError):
        await tool.execute(tool.args_model(workspace_id=workspace_id), ToolContext(user_id=OTHER_USER_ID))


@pytest.mark.asyncio
async def test_search_knowledge_tool_returns_matching_chunks() -> None:
    from tests.fakes import FakeChunkRow

    workspace_service, _, workspace_id = await _seed()
    chunk_repository = FakeChunkRepository(
        [FakeChunkRow(1, "handbook.txt", 0, "Annual leave is 14 days.", 0.9, workspace_id=workspace_id)]
    )
    embedding_service = EmbeddingService(FakeEmbeddingProvider())
    retrieval_service = RetrievalService(
        chunk_repository=chunk_repository,
        embedding_service=embedding_service,
        default_top_k=5,
        similarity_threshold=0.1,
    )

    tool = SearchKnowledgeTool(retrieval_service, workspace_service)
    result = await tool.execute(
        tool.args_model(workspace_id=workspace_id, query="How many vacation days?"),
        ToolContext(user_id=OWNER_ID),
    )

    assert result["results"][0]["filename"] == "handbook.txt"
    assert "leave" in result["results"][0]["content"]


@pytest.mark.asyncio
async def test_search_knowledge_tool_rejects_a_non_owner() -> None:
    workspace_service, _, workspace_id = await _seed()
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.1,
    )
    tool = SearchKnowledgeTool(retrieval_service, workspace_service)

    from app.core.exceptions import WorkspaceNotFoundError

    with pytest.raises(WorkspaceNotFoundError):
        await tool.execute(
            tool.args_model(workspace_id=workspace_id, query="anything"),
            ToolContext(user_id=OTHER_USER_ID),
        )


@pytest.mark.asyncio
async def test_tool_registry_produces_json_schema_specs() -> None:
    workspace_service, document_service, _ = await _seed()
    registry = ToolRegistry([ListWorkspacesTool(workspace_service), ListDocumentsTool(document_service, workspace_service)])

    specs = registry.specs()

    names = {s.name for s in specs}
    assert names == {"list_workspaces", "list_documents"}
    assert all(isinstance(s.parameters, dict) for s in specs)


@pytest.mark.asyncio
async def test_tool_execution_service_rejects_unknown_tool() -> None:
    registry = ToolRegistry([])
    service = ToolExecutionService(registry)

    result = await service.execute("call-1", "delete_everything", {}, ToolContext(user_id=OWNER_ID))

    assert result.success is False
    assert "Unknown tool" in result.error


@pytest.mark.asyncio
async def test_tool_execution_service_rejects_invalid_arguments() -> None:
    workspace_service, document_service, _ = await _seed()
    registry = ToolRegistry([ListDocumentsTool(document_service, workspace_service)])
    service = ToolExecutionService(registry)

    result = await service.execute("call-1", "list_documents", {"workspace_id": "not-a-number"}, ToolContext(user_id=OWNER_ID))

    assert result.success is False
    assert "Invalid arguments" in result.error


@pytest.mark.asyncio
async def test_tool_execution_service_never_raises_on_authorization_failure() -> None:
    workspace_service, document_service, workspace_id = await _seed()
    registry = ToolRegistry([ListDocumentsTool(document_service, workspace_service)])
    service = ToolExecutionService(registry)

    result = await service.execute(
        "call-1", "list_documents", {"workspace_id": workspace_id}, ToolContext(user_id=OTHER_USER_ID)
    )

    assert result.success is False
    assert result.result is None


@pytest.mark.asyncio
async def test_tool_execution_service_returns_structured_result_on_success() -> None:
    workspace_service, document_service, workspace_id = await _seed()
    registry = ToolRegistry([ListDocumentsTool(document_service, workspace_service)])
    service = ToolExecutionService(registry)

    result = await service.execute(
        "call-1", "list_documents", {"workspace_id": workspace_id}, ToolContext(user_id=OWNER_ID)
    )

    assert result.success is True
    assert result.result == {"documents": []}
