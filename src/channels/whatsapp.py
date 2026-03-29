"""WhatsApp channel adapter stub.

WhatsApp requires a Meta Business Account and access to the
WhatsApp Business API. This is a placeholder implementation.

TODO: implement when Business API access is approved.

References:
  https://developers.facebook.com/docs/whatsapp/api/
  https://business.whatsapp.com/api
"""

from .base import ChannelAdapter, IncomingMessage, OutgoingMessage, ParsedCommand


class WhatsAppAdapter(ChannelAdapter):
    """Placeholder. Not yet implemented.

    Constraints:
      - Requires Meta Business API approval.
      - Message templates must be pre-approved.
      - 24-hour session window applies.
    """

    def send_message(self, msg: OutgoingMessage) -> None:
        raise NotImplementedError("WhatsApp adapter is not yet implemented")

    def parse_incoming(self, raw: dict):
        raise NotImplementedError("WhatsApp adapter is not yet implemented")

    def handle_command(self, command, incoming):
        raise NotImplementedError("WhatsApp adapter is not yet implemented")
