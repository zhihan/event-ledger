"""Abstract base class for channel adapters."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class IncomingMessage:
    channel: str
    sender_id: str
    text: str
    raw: dict = field(default_factory=dict)

@dataclass
class OutgoingMessage:
    recipient_id: str
    text: str
    extra: dict = field(default_factory=dict)

@dataclass
class ParsedCommand:
    command: str
    args: list[str] = field(default_factory=list)
    raw_text: str = ""

    @classmethod
    def from_text(cls, text: str):
        text = text.strip()
        if not text.startswith("/"):
            return None
        parts = text.split()
        command = parts[0].lstrip("/").split("@")[0].lower()
        return cls(command=command, args=parts[1:], raw_text=text)

class ChannelAdapter(ABC):
    @abstractmethod
    def send_message(self, msg: OutgoingMessage) -> None: ...

    @abstractmethod
    def parse_incoming(self, raw: dict): ...

    @abstractmethod
    def handle_command(self, command: ParsedCommand, incoming: IncomingMessage): ...

    def dispatch(self, raw: dict):
        incoming = self.parse_incoming(raw)
        if incoming is None: return None
        cmd = ParsedCommand.from_text(incoming.text)
        if cmd is None: return None
        reply = self.handle_command(cmd, incoming)
        if reply is not None: self.send_message(reply)
        return reply
