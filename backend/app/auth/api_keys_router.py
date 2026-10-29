"""Institutional API Key Management Endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.auth import api_keys as service
from app.auth.api_keys import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyRotateResponse,
    to_api_key_response,
)
from app.auth.dependencies import (
    require_college_admin,
    require_college_staff,
    verify_institution_access,
)
from app.db import get_db
from app.models import User

router = APIRouter(tags=["Institutional API Keys"])


@router.get(
    "/institutions/{institution_id}/api-keys",
    response_model=ApiKeyListResponse,
    summary="List all integration API keys for an institution",
)
def list_institution_api_keys(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, require_college_staff],
    db: Annotated[Session, Depends(get_db)],
) -> ApiKeyListResponse:
    """Retrieve all API keys created for an institution, including revoked keys."""
    keys = service.list_api_keys(db=db, institution_id=institution_id)
    items = [to_api_key_response(k) for k in keys]
    return ApiKeyListResponse(items=items, total=len(items))


@router.post(
    "/institutions/{institution_id}/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new scoped integration API key",
)
def create_institution_api_key(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    request_data: ApiKeyCreateRequest,
    request: Request,
    current_user: Annotated[User, require_college_admin],
    db: Annotated[Session, Depends(get_db)],
) -> ApiKeyCreatedResponse:
    """Generate a new scoped API key. Returns the plaintext secret key ONLY ONCE."""
    client_ip = request.client.host if request.client else None
    api_key, raw_key = service.create_api_key(
        db=db,
        institution_id=institution_id,
        name=request_data.name,
        scopes=request_data.scopes,
        user=current_user,
        client_ip=client_ip,
    )
    base_dto = to_api_key_response(api_key)
    return ApiKeyCreatedResponse(
        **base_dto.model_dump(),
        raw_key=raw_key,
    )


@router.post(
    "/institutions/{institution_id}/api-keys/{key_id}/rotate",
    response_model=ApiKeyRotateResponse,
    summary="Rotate an existing active API key",
)
def rotate_institution_api_key(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    key_id: int,
    request: Request,
    current_user: Annotated[User, require_college_admin],
    db: Annotated[Session, Depends(get_db)],
) -> ApiKeyRotateResponse:
    """Rotate an existing key. Invalidates previous key and returns new secret key ONLY ONCE."""
    client_ip = request.client.host if request.client else None
    api_key, raw_key = service.rotate_api_key(
        db=db,
        institution_id=institution_id,
        key_id=key_id,
        user=current_user,
        client_ip=client_ip,
    )
    return ApiKeyRotateResponse(
        id=api_key.id,
        institution_id=api_key.institution_id,
        name=api_key.name,
        key_prefix=service.compute_key_prefix(raw_key),
        raw_key=raw_key,
        scopes=list(api_key.scopes) if isinstance(api_key.scopes, list) else [],
        updated_at=api_key.updated_at,
    )


@router.post(
    "/institutions/{institution_id}/api-keys/{key_id}/revoke",
    response_model=ApiKeyResponse,
    summary="Revoke an integration API key",
)
def revoke_institution_api_key(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    key_id: int,
    request: Request,
    current_user: Annotated[User, require_college_admin],
    db: Annotated[Session, Depends(get_db)],
) -> ApiKeyResponse:
    """Revoke an API key immediately. Systems using this key will lose access."""
    client_ip = request.client.host if request.client else None
    api_key = service.revoke_api_key(
        db=db,
        institution_id=institution_id,
        key_id=key_id,
        user=current_user,
        client_ip=client_ip,
    )
    return to_api_key_response(api_key)


@router.delete(
    "/institutions/{institution_id}/api-keys/{key_id}",
    response_model=ApiKeyResponse,
    summary="Delete/Revoke an integration API key",
)
def delete_institution_api_key(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    key_id: int,
    request: Request,
    current_user: Annotated[User, require_college_admin],
    db: Annotated[Session, Depends(get_db)],
) -> ApiKeyResponse:
    """Soft-delete/revoke an API key to preserve audit log integrity."""
    client_ip = request.client.host if request.client else None
    api_key = service.revoke_api_key(
        db=db,
        institution_id=institution_id,
        key_id=key_id,
        user=current_user,
        client_ip=client_ip,
    )
    return to_api_key_response(api_key)
