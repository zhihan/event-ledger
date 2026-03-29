import pytest
from unittest.mock import patch
from channels.base import ParsedCommand, IncomingMessage, OutgoingMessage
from channels.telegram import TelegramAdapter

def test_cmd_start():
    cmd = ParsedCommand.from_text("/start")
    assert cmd.command == "start" and cmd.args == []

def test_cmd_with_args():
    cmd = ParsedCommand.from_text("/confirm abc-123")
    assert cmd.command == "confirm" and cmd.args == ["abc-123"]

def test_cmd_not_command():
    assert ParsedCommand.from_text("hello") is None

def test_cmd_empty():
    assert ParsedCommand.from_text("") is None

def test_cmd_bot_suffix():
    cmd = ParsedCommand.from_text("/start@MyBot")
    assert cmd.command == "start"

def test_cmd_uppercase():
    cmd = ParsedCommand.from_text("/START")
    assert cmd.command == "start"

def test_parse_message():
    a = TelegramAdapter(token="fake")
    raw = {"message": {"text": "/start", "chat": {"id": 42}, "from": {"id": 42}}}
    msg = a.parse_incoming(raw)
    assert msg.channel == "telegram" and msg.sender_id == "42" and msg.text == "/start"

def test_parse_no_text():
    a = TelegramAdapter(token="fake")
    assert a.parse_incoming({"message": {"chat": {"id": 1}}}) is None

def test_parse_no_message():
    a = TelegramAdapter(token="fake")
    assert a.parse_incoming({"callback_query": {}}) is None

def test_parse_edited_message():
    a = TelegramAdapter(token="fake")
    raw = {"edited_message": {"text": "/next", "chat": {"id": 7}, "from": {"id": 7}}}
    msg = a.parse_incoming(raw)
    assert msg is not None and msg.text == "/next"

def _inc():
    return IncomingMessage(channel="telegram", sender_id="99", text="")

def test_handle_start():
    a = TelegramAdapter(token="fake")
    r = a.handle_command(ParsedCommand(command="start"), _inc())
    assert r is not None and "Welcome" in r.text and r.recipient_id == "99"

def test_handle_unknown():
    a = TelegramAdapter(token="fake")
    r = a.handle_command(ParsedCommand(command="foobar"), _inc())
    assert "Unknown" in r.text

def test_handle_meetings_empty():
    a = TelegramAdapter(token="fake")
    r = a.handle_command(ParsedCommand(command="meetings"), _inc())
    assert "No upcoming" in r.text

def test_handle_next_empty():
    a = TelegramAdapter(token="fake")
    r = a.handle_command(ParsedCommand(command="next"), _inc())
    assert "No upcoming" in r.text

def test_handle_confirm_no_args():
    a = TelegramAdapter(token="fake")
    r = a.handle_command(ParsedCommand(command="confirm", args=[]), _inc())
    assert "Usage" in r.text

def test_handle_confirm_stub():
    a = TelegramAdapter(token="fake")
    r = a.handle_command(ParsedCommand(command="confirm", args=["occ-abc"]), _inc())
    assert "occ-abc" in r.text

def test_dispatch_start_calls_send():
    a = TelegramAdapter(token="fake")
    raw = {"message": {"text": "/start", "chat": {"id": 5}, "from": {"id": 5}}}
    with patch.object(a, "send_message") as mock_send:
        reply = a.dispatch(raw)
        assert reply is not None
        mock_send.assert_called_once_with(reply)

def test_dispatch_non_command():
    a = TelegramAdapter(token="fake")
    raw = {"message": {"text": "hello", "chat": {"id": 5}, "from": {"id": 5}}}
    assert a.dispatch(raw) is None

def test_dispatch_no_message():
    a = TelegramAdapter(token="fake")
    assert a.dispatch({"callback_query": {}}) is None

def test_no_token_raises():
    import os
    orig = os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    try:
        with pytest.raises(ValueError):
            TelegramAdapter()
    finally:
        if orig is not None: os.environ["TELEGRAM_BOT_TOKEN"] = orig

def test_meetings_with_data():
    a = TelegramAdapter(token="fake")
    a._fetch_occurrences = lambda _: [{"occurrence_id": "o1", "title": "Stand-up", "scheduled_for": "2026-04-01"}]
    r = a.handle_command(ParsedCommand(command="meetings"), _inc())
    assert "Stand-up" in r.text

def test_next_with_data():
    a = TelegramAdapter(token="fake")
    a._fetch_occurrences = lambda _: [{"occurrence_id": "o1", "title": "Stand-up", "scheduled_for": "2026-04-01"}]
    r = a.handle_command(ParsedCommand(command="next"), _inc())
    assert "o1" in r.text
