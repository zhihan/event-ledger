"""WeChat channel adapter stub.

WeChat integration requires an approved WeChat Official Account
or Mini Program. This is a placeholder implementation.

TODO: implement when a supported integration path is confirmed.

References:
  https://developers.weixin.qq.com/doc/offiaccount/en/
"""

from .base import ChannelAdapter, IncomingMessage, OutgoingMessage, ParsedCommand


class WeChatAdapter(ChannelAdapter):
    """Placeholder. Not yet implemented.

    Constraints:
      - Requires a WeChat Official Account with approval.
      - Mini Program messaging has strict policy constraints.
      - Evaluate feasibility before starting implementation.
    """

    def send_message(self, msg: OutgoingMessage) -> None:
        raise NotImplementedError("WeChat adapter is not yet implemented")

    def parse_incoming(self, raw: dict):
        raise NotImplementedError("WeChat adapter is not yet implemented")

    def handle_command(self, command, incoming):
        raise NotImplementedError("WeChat adapter is not yet implemented")
