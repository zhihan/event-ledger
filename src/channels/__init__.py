"""Channel adapter package for external messaging integrations.

Supported adapters:
  - telegram  -- Telegram Bot API (first integration)
  - whatsapp  -- placeholder (requires Business API approval)
  - wechat    -- placeholder (requires approved Mini Program or Official Account)
"""
from .base import ChannelAdapter
from .telegram import TelegramAdapter

__all__ = ["ChannelAdapter", "TelegramAdapter"]
