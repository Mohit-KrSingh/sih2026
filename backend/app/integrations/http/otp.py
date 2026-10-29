"""HTTP stub for external SMS/Email/OTP Gateway."""

from app.integrations.interfaces import OtpSender


class HttpOtpSender(OtpSender):
    """Production HTTP client for the official SMS and email gateway.

    Stub raising NotImplementedError per SPEC.md section 2.5 and 18.
    """

    def __init__(self, gateway_url: str | None = None, api_key: str | None = None) -> None:
        self.gateway_url = gateway_url
        self.api_key = api_key

    def send_otp(self, channel: str, recipient: str, code: str, context: str = "") -> bool:
        raise NotImplementedError(
            "Real OtpSender HTTP gateway is not implemented in demo mode. "
            "Set OTP_SENDER_TYPE='mock' in configuration or environment."
        )

    def send_notification(self, channel: str, recipient: str, body: str) -> bool:
        raise NotImplementedError(
            "Real OtpSender HTTP gateway is not implemented in demo mode. "
            "Set OTP_SENDER_TYPE='mock' in configuration or environment."
        )
