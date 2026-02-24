"""Tests for the committer module."""

import sys
from datetime import date
from unittest.mock import MagicMock, patch

from memory import Memory
from committer import apply_user_urls, build_ai_request, extract_urls


def test_build_ai_request():
    memories = [
        Memory(target=date(2026, 3, 1), expires=date(2026, 4, 1),
               content="Planning", title="Standup", time="10:00", place="Room A"),
    ]
    prompt = build_ai_request("Team meeting next Thursday", memories, date(2026, 2, 18))

    assert "2026-02-18" in prompt
    assert "Team meeting next Thursday" in prompt
    assert "Standup" in prompt
    assert "10:00" in prompt
    assert "Room A" in prompt
    assert "slug" in prompt.lower()


def test_build_ai_request_ongoing_memory():
    memories = [
        Memory(target=None, expires=date(2026, 2, 22),
               content="Every week", title="Sunday Worship"),
    ]
    prompt = build_ai_request("What's happening?", memories, date(2026, 2, 18))
    assert "target=ongoing" in prompt
    assert "Sunday Worship" in prompt


def test_build_ai_request_no_memories():
    prompt = build_ai_request("New event Friday", [], date(2026, 2, 18))

    assert "(none)" in prompt
    assert "New event Friday" in prompt


def test_call_ai():
    mock_response = MagicMock()
    mock_response.text = '{"action": "create", "target": "2026-03-01", "expires": "2026-03-31", "title": "Meeting", "time": null, "place": null, "content": "Team sync"}'

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client

    mock_google = MagicMock()
    mock_google.genai = mock_genai

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
         patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
        from committer import call_ai
        result = call_ai("test prompt")

    assert result["action"] == "create"
    assert result["title"] == "Meeting"
    mock_genai.Client.assert_called_once_with(api_key="test-key")


def test_build_ai_request_with_attachments():
    prompt = build_ai_request(
        "Meeting with flyer", [], date(2026, 2, 18),
        attachment_urls=["https://storage.googleapis.com/bucket/flyer.pdf"],
    )
    assert "https://storage.googleapis.com/bucket/flyer.pdf" in prompt
    assert "Attached file URLs" in prompt


def test_build_ai_request_no_attachments():
    prompt = build_ai_request("Meeting", [], date(2026, 2, 18))
    assert "Attached file URLs" not in prompt


# --- URL preference tests ---


def test_extract_urls():
    text = "Check https://example.com/a and http://example.org/b please"
    assert extract_urls(text) == ["https://example.com/a", "http://example.org/b"]


def test_extract_urls_none():
    assert extract_urls("No links here") == []


def test_apply_user_urls_replaces_ai_link_in_title():
    title = "[Meeting](https://ai-generated.com/link)"
    content = "Some description"
    user_urls = ["https://user-provided.com/real"]
    new_title, new_content = apply_user_urls(title, content, user_urls)
    assert new_title == "[Meeting](https://user-provided.com/real)"
    assert "https://user-provided.com/real" in new_content


def test_apply_user_urls_wraps_plain_title():
    title = "Meeting"
    content = "Some description"
    user_urls = ["https://user-provided.com/real"]
    new_title, new_content = apply_user_urls(title, content, user_urls)
    assert new_title == "[Meeting](https://user-provided.com/real)"


def test_apply_user_urls_appends_missing_to_content():
    title = "Meeting"
    content = "Already has https://a.com here"
    user_urls = ["https://a.com", "https://b.com"]
    new_title, new_content = apply_user_urls(title, content, user_urls)
    # a.com already present, b.com should be appended
    assert "https://b.com" in new_content
    assert "Links:" in new_content
    # a.com should NOT be in the appended section (it was already present)
    links_section = new_content.split("Links:")[1]
    assert "https://a.com" not in links_section


def test_apply_user_urls_no_urls_is_noop():
    title, content = apply_user_urls("Title", "Content", [])
    assert title == "Title"
    assert content == "Content"
