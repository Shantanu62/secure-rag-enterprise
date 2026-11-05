
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth.dependencies import require_permission
from backend.rag.answer_service import answer_question


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=5000,
        description="Question about accessible documents",
    )


class SourceResponse(BaseModel):
    source_number: int
    document_id: str
    filename: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    model: str | None
    pii_masking_enabled: bool


@router.post(
    "/ask",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def ask_question(
    request: ChatRequest,
    current_user: Annotated[
        dict,
        Depends(require_permission("document:read")),
    ],
):
    """Answer a question using documents accessible to the user."""

    try:
        result = answer_question(
            question=request.question,
            department=current_user["department"],
            role=current_user["role"],
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Keep internal errors and provider details out of API responses.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to generate an answer. Please try again later.",
        ) from exc
