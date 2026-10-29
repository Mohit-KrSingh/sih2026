"""Mock implementation of OtpSender."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.brand import PRODUCT_NAME
from app.integrations.interfaces import OtpSender, OutboxMessage
from app.models import DevOutbox


class MockOtpSender(OtpSender):
    """Simulated OTP & notification sender that persists messages to dev_outbox."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self._in_memory_outbox: list[OutboxMessage] = []

    def send_otp(self, channel: str, recipient: str, code: str, context: str = "") -> bool:
        """Deliver mock OTP code to dev_outbox."""
        context_str = f" Context: {context}" if context else ""
        body = (
            f"Your {PRODUCT_NAME} verification OTP code is: {code}. "
            f"Valid for 5 minutes.{context_str}"
        )
        return self._record_message(channel=channel, recipient=recipient, body=body)

    def send_notification(self, channel: str, recipient: str, body: str) -> bool:
        """Deliver mock notification message to dev_outbox."""
        return self._record_message(channel=channel, recipient=recipient, body=body)

    def _record_message(self, channel: str, recipient: str, body: str) -> bool:
        """Internal helper to write message to database and in-memory log."""
        msg_id: int | None = None
        if self.session is not None:
            entry = DevOutbox(
                channel=channel,
                recipient=recipient,
                body=body,
            )
            self.session.add(entry)
            self.session.flush()
            msg_id = entry.id

        message = OutboxMessage(
            id=msg_id,
            channel=channel,
            recipient=recipient,
            body=body,
        )
        self._in_memory_outbox.append(message)
        return True

    def get_messages(
        self,
        recipient: str | None = None,
        channel: str | None = None,
    ) -> list[OutboxMessage]:
        """Fetch recorded outbox messages with optional filtering."""
        if self.session is not None:
            stmt = select(DevOutbox).order_by(DevOutbox.id.asc())
            if recipient:
                stmt = stmt.where(DevOutbox.recipient == recipient)
            if channel:
                stmt = stmt.where(DevOutbox.channel == channel)
            entries = self.session.scalars(stmt).all()
            return [
                OutboxMessage(
                    id=e.id,
                    channel=e.channel,
                    recipient=e.recipient,
                    body=e.body,
                )
                for e in entries
            ]

        results = self._in_memory_outbox
        if recipient:
            results = [m for m in results if m.recipient == recipient]
        if channel:
            results = [m for m in results if m.channel == channel]
        return results

    def clear(self) -> None:
        """Clear recorded outbox messages."""
        if self.session is not None:
            self.session.execute(delete(DevOutbox))
            self.session.flush()
        self._in_memory_outbox.clear()
