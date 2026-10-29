"""FastAPI routes for AICTE Review Queue and College Clarification Queries."""

from __future__ import annotations

from typing import Annotated

import redis
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_aicte_user,
    require_college_staff,
    require_college_user,
    verify_institution_access,
)
from app.db import get_db, get_redis
from app.models import User
from app.review import service
from app.review.schemas import (
    CollegeQueryListResponse,
    CollegeQueryResponse,
    ReviewDecisionRequest,
    ReviewItemDetailResponse,
    ReviewItemListResponse,
)

# AICTE Review Queue Endpoints (AICTE Officers & Admins only)
router = APIRouter(prefix="/review", tags=["AICTE Review Queue"])


@router.get(
    "/items",
    response_model=ReviewItemListResponse,
    summary="List submission review items with filters and statistical counts (AICTE only)",
)
def list_review_items(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str | None, Query(description="Filter by academic year")] = None,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            description="Filter: pending | under_review | accepted | query_raised | escalated",
        ),
    ] = None,
    institution_id: Annotated[int | None, Query(description="Filter by institution ID")] = None,
    search: Annotated[
        str | None,
        Query(description="Search by institution name, AICTE ID, state, or receipt number"),
    ] = None,
) -> ReviewItemListResponse:
    """Retrieve review items waiting in the AICTE officer queue."""
    return service.list_review_items(
        db=db,
        status_filter=status_filter,
        academic_year=academic_year,
        institution_id=institution_id,
        search=search,
    )


@router.get(
    "/items/{item_id}",
    response_model=ReviewItemDetailResponse,
    summary="Get complete review item detail with flags, justifications, and queries (AICTE only)",
)
def get_review_item_detail(
    item_id: int,
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
) -> ReviewItemDetailResponse:
    """Retrieve deep context for evaluating an exception item."""
    return service.get_review_item_detail(db=db, review_item_id=item_id)


@router.post(
    "/items/{item_id}/decision",
    response_model=ReviewItemDetailResponse,
    summary="Record review decision: Accept, Raise query, or Escalate (AICTE only)",
)
def record_review_decision(
    item_id: int,
    payload: ReviewDecisionRequest,
    request: Request,
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> ReviewItemDetailResponse:
    """Record an official decision on a review queue item with an audit log entry."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    return service.decide_review_item(
        db=db,
        review_item_id=item_id,
        user=current_user,
        decision=payload.decision,
        note=payload.note,
        redis_client=redis_client,
        client_ip=client_ip,
    )


@router.get(
    "/items/{item_id}/documents/{justification_id}",
    summary="Download supporting evidence document attached to a justification (AICTE only)",
)
def download_review_document(
    item_id: int,
    justification_id: int,
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Stream supporting document from the storage interface for AICTE review."""
    content, filename, media_type = service.get_review_justification_document(
        db=db,
        review_item_id=item_id,
        justification_id=justification_id,
        user=current_user,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# College Clarification Queries Endpoints (Institution Scoped)
college_queries_router = APIRouter(
    prefix="/institutions/{institution_id}/queries", tags=["College Clarification Queries"]
)


@college_queries_router.get(
    "",
    response_model=CollegeQueryListResponse,
    summary="List AICTE clarification queries for this institution",
)
def list_institution_queries(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str | None, Query(description="Filter by academic year")] = None,
    state_filter: Annotated[
        str | None,
        Query(
            alias="state",
            description="Filter by query state: pending | answered | closed",
        ),
    ] = None,
) -> CollegeQueryListResponse:
    """Retrieve all clarification inquiries issued to this college by AICTE."""
    return service.list_institution_queries(
        db=db,
        institution_id=institution_id,
        state_filter=state_filter,
        academic_year=academic_year,
    )


@college_queries_router.get(
    "/{query_id}",
    response_model=CollegeQueryResponse,
    summary="Get single clarification query detail with related flags",
)
def get_institution_query(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    query_id: int,
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
) -> CollegeQueryResponse:
    """Retrieve details for a specific clarification inquiry."""
    return service.get_institution_query_detail(
        db=db,
        institution_id=institution_id,
        query_id=query_id,
    )


@college_queries_router.post(
    "/{query_id}/respond",
    response_model=CollegeQueryResponse,
    summary="Submit written clarification and optional evidence document to AICTE",
)
async def respond_to_query(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    query_id: int,
    request: Request,
    current_user: Annotated[User, require_college_staff],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    response: Annotated[str | None, Form()] = None,
    document: Annotated[UploadFile | None, File()] = None,
) -> CollegeQueryResponse:
    """Answer an AICTE clarification inquiry and return the submission to under_review."""
    final_response: str | None = response
    doc_ref: str | None = None

    # Handle application/json payload fallback for API and test clients
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            final_response = body.get("response")
            doc_ref = body.get("document_ref")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from None

    if not final_response or len(final_response.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Response text must be at least 5 characters long.",
        )

    client_ip = request.client.host if request.client else "127.0.0.1"
    return await service.respond_to_query(
        db=db,
        institution_id=institution_id,
        query_id=query_id,
        user=current_user,
        response_text=final_response,
        document_ref=doc_ref,
        document_file=document,
        redis_client=redis_client,
        client_ip=client_ip,
    )
