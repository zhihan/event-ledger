"""Tests for the publisher module."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory import Memory
from publisher import build_prompt, generate_site, load_memories, main


def _write_memory(path: Path, target: str, expires: str, content: str, title: str | None = None) -> None:
    mem = Memory(
        target=date.fromisoformat(target),
        expires=date.fromisoformat(expires),
        content=content,
        title=title,
    )
    mem.dump(path)


def test_load_memories_filters_expired(tmp_path: Path):
    _write_memory(tmp_path / "a.md", "2026-01-01", "2026-01-31", "January event")
    _write_memory(tmp_path / "b.md", "2026-03-01", "2026-06-01", "March event")
    _write_memory(tmp_path / "c.md", "2026-02-15", "2026-05-01", "February event")

    today = date(2026, 2, 18)
    memories = load_memories(tmp_path, today)

    assert len(memories) == 2
    assert memories[0].content == "February event"
    assert memories[1].content == "March event"


def test_load_memories_sorted_by_target(tmp_path: Path):
    _write_memory(tmp_path / "z.md", "2026-06-01", "2026-12-01", "June")
    _write_memory(tmp_path / "a.md", "2026-03-01", "2026-12-01", "March")

    memories = load_memories(tmp_path, date(2026, 1, 1))
    assert [m.content for m in memories] == ["March", "June"]


def test_build_prompt():
    memories = [
        Memory(target=date(2026, 3, 1), expires=date(2026, 6, 1), content="Event A", title="Title A"),
        Memory(target=date(2026, 4, 1), expires=date(2026, 7, 1), content="Event B"),
    ]
    prompt = build_prompt(memories, "Blog template instructions")

    assert "Blog template instructions" in prompt
    assert "Event A" in prompt
    assert "Title A" in prompt
    assert "Event B" in prompt


@patch("publisher.genai")
def test_generate_site(mock_genai):
    mock_response = MagicMock()
    mock_response.text = "<html><body>Hello</body></html>"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
        html = generate_site("test prompt")

    assert "<html>" in html
    mock_client.models.generate_content.assert_called_once()


@patch("publisher.generate_site", return_value="<html><body>Generated</body></html>")
def test_main_end_to_end(mock_gen, tmp_path: Path):
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    _write_memory(mem_dir / "event.md", "2026-03-01", "2026-06-01", "Spring event", "Spring")

    tpl = tmp_path / "template.md"
    tpl.write_text("Blog template")

    out_dir = tmp_path / "site"

    main(["--memories-dir", str(mem_dir), "--template", str(tpl), "--output-dir", str(out_dir)])

    index = out_dir / "index.html"
    assert index.exists()
    assert index.read_text() == "<html><body>Generated</body></html>"
    mock_gen.assert_called_once()
