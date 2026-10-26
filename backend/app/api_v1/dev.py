"""Dev-only management routes for simulation outbox and inspection."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.integrations.mock.otp import MockOtpSender
from app.models import DevOutbox

router = APIRouter(prefix="/dev", tags=["dev"])


def verify_dev_mode() -> None:
    """Ensure dev-only routes are never accessible in production."""
    settings = get_settings()
    if settings.ENV == "production" and not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev endpoints are disabled in production environment.",
        )


class OutboxItemResponse(BaseModel):
    id: int
    channel: str
    recipient: str
    body: str
    created_at: datetime


class SendOtpRequest(BaseModel):
    channel: str = "otp"
    recipient: str
    code: str
    context: str = ""


@router.get("/outbox", response_model=list[OutboxItemResponse])
def list_dev_outbox(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_dev_mode)],
    channel: Annotated[str | None, Query(description="Filter by message channel")] = None,
    recipient: Annotated[str | None, Query(description="Filter by recipient")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[OutboxItemResponse]:
    """List simulated OTP and notification messages from dev_outbox."""
    stmt = select(DevOutbox).order_by(desc(DevOutbox.created_at))
    if channel:
        stmt = stmt.where(DevOutbox.channel == channel)
    if recipient:
        stmt = stmt.where(DevOutbox.recipient == recipient)
    stmt = stmt.limit(limit)

    rows = db.scalars(stmt).all()
    return [
        OutboxItemResponse(
            id=r.id,
            channel=r.channel,
            recipient=r.recipient,
            body=r.body,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/otp/send", status_code=status.HTTP_201_CREATED)
def trigger_dev_otp(
    payload: SendOtpRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_dev_mode)],
) -> dict[str, str]:
    """Helper dev endpoint to simulate sending an OTP directly."""
    sender = MockOtpSender(session=db)
    sender.send_otp(
        channel=payload.channel,
        recipient=payload.recipient,
        code=payload.code,
        context=payload.context,
    )
    db.commit()
    return {"message": "OTP delivered to dev_outbox"}


@router.delete("/outbox", status_code=status.HTTP_200_OK)
def clear_dev_outbox(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_dev_mode)],
) -> dict[str, int]:
    """Clear all records from dev_outbox."""
    result = db.execute(delete(DevOutbox))
    db.commit()
    return {"cleared": result.rowcount or 0}
