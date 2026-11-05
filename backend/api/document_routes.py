
import logging
from pathlib import Path, PurePosixPath
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_permission, get_current_user
from backend.auth.document_permissions import (
    get_accessible_documents,
    can_access_document,
)
from backend.core.config import settings
from backend.database.connection import get_db
from backend.models.document import Document
from backend.rag.retrieval_service import (
    index_document,
    remove_document_from_index,
)
from backend.security.audit_service import record_audit_event


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Document Management"],
)


ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}

ALLOWED_ROLES = {"Admin", "Manager", "Employee"}


class DocumentUploadResponse(BaseModel):
    id: int
    title: str
    filename: str
    content_type: str
    department: str
    allowed_roles: str
    message: str


class DocumentListItem(BaseModel):
    id: int
    title: str
    filename: str
    content_type: str
    department: str
    allowed_roles: str
    description: str | None
    created_at: str


class DocumentDeleteResponse(BaseModel):
    id: int
    is_active: bool
    message: str


def get_client_ip(request: Request) -> str | None:
    """Return the direct client IP when available."""
    if request.client is None:
        return None

    return request.client.host


def build_index_metadata(document: Document) -> dict:
    """Build Qdrant metadata from the persisted document record."""
    return {
        "document_id": str(document.id),
        "document_title": document.title,
        "department": document.department,
        "allowed_roles": [
            role.strip()
            for role in document.allowed_roles.split(",")
            if role.strip()
        ],
        "source_name": document.filename,
    }


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str, Form(min_length=1, max_length=255)],
    current_user: Annotated[
        dict,
        Depends(require_permission("document:upload")),
    ],
    db: Annotated[Session, Depends(get_db)],
    description: Annotated[
        str | None,
        Form(max_length=2000),
    ] = None,
    department: Annotated[
        str | None,
        Form(max_length=100),
    ] = None,
    allowed_roles: Annotated[
        str,
        Form(),
    ] = "Manager,Employee",
):
    original_filename = PurePosixPath(
        (file.filename or "").replace("\\", "/")
    ).name

    if not original_filename:
        raise HTTPException(400, "Invalid filename")

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Unsupported file type")

    if len(original_filename) > 255:
        raise HTTPException(400, "Filename is too long")

    user_role = current_user["role"]
    user_department = current_user["department"]

    if user_role == "Admin":
        target_department = (
            department or user_department
        ).strip()
    else:
        target_department = user_department

    if not target_department or len(target_department) > 100:
        raise HTTPException(400, "A valid department is required")

    selected_roles = {
        role.strip()
        for role in allowed_roles.split(",")
        if role.strip()
    }

    if (
        not selected_roles
        or not selected_roles.issubset(ALLOWED_ROLES)
    ):
        raise HTTPException(400, "Invalid allowed roles")

    if user_role != "Admin" and "Admin" in selected_roles:
        raise HTTPException(
            403,
            "Only Admin can assign Admin document access",
        )

    normalized_roles = ",".join(
        role
        for role in ("Admin", "Manager", "Employee")
        if role in selected_roles
    )

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    upload_dir = Path(settings.UPLOAD_DIR)

    storage_name = f"{uuid4().hex}{extension}"
    storage_path = upload_dir / storage_name

    total_size = 0
    first_chunk = True
    file_created = False
    db_committed = False
    index_attempted = False
    document = None

    try:
        upload_dir.mkdir(parents=True, exist_ok=True)

        with storage_path.open("xb") as destination:
            file_created = True

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > max_size:
                    raise HTTPException(
                        413,
                        "File exceeds the maximum upload size",
                    )

                if first_chunk:
                    if (
                        extension == ".pdf"
                        and not chunk.startswith(b"%PDF-")
                    ):
                        raise HTTPException(
                            415,
                            "Invalid PDF file signature",
                        )

                    if (
                        extension == ".docx"
                        and not chunk.startswith(b"PK")
                    ):
                        raise HTTPException(
                            415,
                            "Invalid DOCX file signature",
                        )

                    if extension == ".txt" and b"\x00" in chunk:
                        raise HTTPException(
                            415,
                            "Invalid TXT file content",
                        )

                    first_chunk = False

                destination.write(chunk)

        if total_size == 0:
            raise HTTPException(400, "Uploaded file is empty")

        document = Document(
            title=title.strip(),
            filename=original_filename,
            file_path=str(storage_path),
            content_type=ALLOWED_EXTENSIONS[extension],
            owner_id=int(current_user["user_id"]),
            department=target_department,
            allowed_roles=normalized_roles,
            is_active=True,
            description=description.strip() if description else None,
        )

        db.add(document)
        db.flush()

        # Index the document before committing its database record.
        index_attempted = True

        indexed_chunks = index_document(
            file_path=storage_path,
            metadata=build_index_metadata(document),
        )

        record_audit_event(
            db=db,
            current_user=current_user,
            action="DOCUMENT_UPLOAD",
            resource_type="Document",
            resource_id=document.id,
            details="Document uploaded successfully",
            ip_address=get_client_ip(request),
        )

        db.commit()
        db_committed = True
        db.refresh(document)

        return DocumentUploadResponse(
            id=document.id,
            title=document.title,
            filename=document.filename,
            content_type=document.content_type,
            department=document.department,
            allowed_roles=document.allowed_roles,
            message=(
                f"Document uploaded and indexed successfully "
                f"({indexed_chunks} chunks)"
            ),
        )

    except Exception:
        db.rollback()

        if index_attempted and document is not None and not db_committed:
            try:
                remove_document_from_index(str(document.id))
            except Exception:
                logger.exception(
                    "Failed to clean up Qdrant chunks after upload failure"
                )

        if file_created and not db_committed:
            storage_path.unlink(missing_ok=True)

        raise

    finally:
        await file.close()


@router.get(
    "",
    response_model=list[DocumentListItem],
)
def list_documents(
    current_user: Annotated[
        dict,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    documents = get_accessible_documents(
        db=db,
        current_user=current_user,
    )

    return [
        DocumentListItem(
            id=document.id,
            title=document.title,
            filename=document.filename,
            content_type=document.content_type,
            department=document.department,
            allowed_roles=document.allowed_roles,
            description=document.description,
            created_at=document.created_at.isoformat(),
        )
        for document in documents
    ]


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    current_user: Annotated[
        dict,
        Depends(get_current_user),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    if not can_access_document(
        db=db,
        current_user=current_user,
        document_id=document_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.is_active.is_(True),
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    file_path = Path(document.file_path).resolve()
    upload_root = Path(settings.UPLOAD_DIR).resolve()

    if not file_path.is_relative_to(upload_root):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file is unavailable",
        )

    return FileResponse(
        path=file_path,
        media_type=document.content_type,
        filename=document.filename,
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
)
def delete_document(
    document_id: int,
    request: Request,
    current_user: Annotated[
        dict,
        Depends(require_permission("document:delete")),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.is_active.is_(True),
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    document_file_path = Path(document.file_path)
    document_metadata = build_index_metadata(document)
    index_removed = False

    try:
        document.is_active = False

        record_audit_event(
            db=db,
            current_user=current_user,
            action="DOCUMENT_DELETE",
            resource_type="Document",
            resource_id=document.id,
            details="Document soft-deleted successfully",
            ip_address=get_client_ip(request),
        )

        remove_document_from_index(str(document.id))
        index_removed = True

        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()

        if index_removed and document_file_path.is_file():
            try:
                index_document(
                    file_path=document_file_path,
                    metadata=document_metadata,
                )
            except Exception:
                logger.exception(
                    "Failed to restore Qdrant index after delete rollback"
                )

        raise

    return DocumentDeleteResponse(
        id=document.id,
        is_active=document.is_active,
        message="Document soft-deleted successfully",
    )
