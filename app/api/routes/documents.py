"""Document upload and retrieval endpoints — scoped to a workspace owned by the caller."""
from fastapi import APIRouter, Depends, Form, UploadFile

from app.api.dependencies import (
    enforce_upload_usage_limit,
    get_current_user,
    get_document_service,
    get_workspace_service,
)
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentStatusResponse, DocumentUploadResponse
from app.services.document_service import DocumentService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    workspace_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    _usage_limit: None = Depends(enforce_upload_usage_limit),
) -> DocumentUploadResponse:
    """Upload a PDF, DOCX or TXT file into a workspace and run it through the ingestion pipeline."""
    await workspace_service.get_owned_workspace(workspace_id, current_user.id)

    content = await file.read()
    document = await document_service.upload_and_process(
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        workspace_id=workspace_id,
    )
    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        status=document.status,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_count=await document_service.count_chunks(document.id),
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> list[DocumentResponse]:
    """List all documents in a workspace owned by the current user."""
    await workspace_service.get_owned_workspace(workspace_id, current_user.id)

    documents = await document_service.list_documents(workspace_id)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> DocumentResponse:
    """Fetch a single document by id, scoped to a workspace owned by the current user."""
    await workspace_service.get_owned_workspace(workspace_id, current_user.id)

    document = await document_service.get_document(document_id, workspace_id)
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> DocumentStatusResponse:
    """Lightweight endpoint for polling indexing progress (uploaded -> processing -> indexed|failed)."""
    await workspace_service.get_owned_workspace(workspace_id, current_user.id)

    document = await document_service.get_document(document_id, workspace_id)
    return DocumentStatusResponse.model_validate(document)
