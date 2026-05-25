"""Assistant service — Meeting Organizer AI assistant.

Parses organizer messages, determines intent, proposes structured actions
(with preview text), and streams a response to the caller.

Streaming events (dicts with "type" key):
  {"type": "status",          "message": "..."}
  {"type": "text_chunk",      "text": "..."}
  {"type": "action_proposal", "action_id": "...", "action_type": "...",
   "preview_summary": "...",  "payload": {...}}
  {"type": "done"}
  {"type": "error",           "message": "..."}
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Generator

from assistant_actions import (
    build_create_occurrence_action,
    build_create_series_action,
    build_draft_material_action,
    build_generate_reminder_text_action,
    build_reschedule_occurrence_action,
    build_update_occurrence_action,
    build_update_occurrence_notes_action,
    build_update_room_action,
    build_update_series_action,
    save_pending_action,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_MAX_RETRIES = 2
_MAX_TOOL_ROUNDS = 15

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an AI assistant for a meeting organizer. Help organizers manage recurring
meetings, schedules, and materials through natural conversation.

The room's series are listed in the "Room context" section. To find specific occurrences,
use the list_occurrences tool with a series_id and optional date range. list_occurrences
already returns occurrence_id, scheduled_for, host, location, and notes — that is enough
to propose update_occurrence or reschedule_occurrence actions for any number of occurrences.
Only call get_occurrence when you specifically need the links field for a single occurrence.

Available actions:
  create_series            — create a new recurring meeting series
  create_occurrence        — create a single new occurrence in an existing series
  reschedule_occurrence    — reschedule a single meeting occurrence
  update_occurrence        — update fields (host, location, notes, links) on an existing occurrence
  update_room              — update room-level fields (title, timezone, description, links)
  update_series            — update series-level fields (title, description, time, duration, location, online link, links, etc.)
  draft_material           — draft meeting material (agenda, notes, announcement)
  generate_reminder_text   — generate a shareable reminder for participants
  general_question         — answer without performing any state change

For each message:
  1. If you need occurrence data, call list_occurrences first. Avoid get_occurrence unless you need the links field.
  2. Determine the INTENT (one of the actions above).
  3. Write a short, friendly RESPONSE (1-3 sentences).
  4. If the intent is state-changing, produce a structured ACTION PAYLOAD.
  5. If no action is needed, set "action" to null.

IMPORTANT: When the intent is state-changing, your response_text should describe what
you WILL do (e.g. "I'll update the agenda for..."), NOT what you HAVE done. The action
is only executed after the user confirms it. Never say "I have updated" or "Done" in
response_text — the action hasn't happened yet at that point.

Always reply in the same language as the user.

Respond with a single JSON object (no markdown fences):
{
  "intent": "<intent>",
  "response_text": "<conversational reply>",
  "action": {
    "action_type": "<same as intent, not applicable for general_question>",
    "preview_summary": "<1-sentence summary of what will happen>",
    "payload": {
      // create_series: title, kind, description, schedule_rule{frequency,weekdays,interval},
      //   default_time, default_duration_minutes, default_location, default_online_link
      // create_occurrence: series_id, scheduled_for (ISO 8601 UTC), host (optional),
      //   location (optional), notes (optional agenda/notes text)
      // reschedule_occurrence: occurrence_id, new_scheduled_for (ISO 8601 UTC)
      // update_occurrence: occurrence_id, host (optional), location (optional),
      //   notes (optional agenda/notes text),
      //   links (optional array of {label, url} resource links)
      // update_room: title (optional), timezone (optional), description (optional),
      //   links (optional array of {label, url} resource links)
      // update_series: series_id, title (optional), description (optional),
      //   default_time (optional), default_duration_minutes (optional),
      //   default_location (optional), default_online_link (optional),
      //   links (optional array of {label, url} resource links)
      // draft_material: title, material_kind, draft_text
      // generate_reminder_text: occurrence_id, series_id, reminder_text
    }
  }
}

When multiple occurrences need the same action type (e.g. updating notes for several
meetings at once), set "payload" to an ARRAY of payload objects:
  "payload": [
    {"occurrence_id": "...", "notes": "..."},
    {"occurrence_id": "...", "notes": "..."}
  ]
All items will be executed together when the user confirms.
"""


def _build_contents(
    message: str,
    room_context: dict[str, Any] | None,
    history: list[dict[str, str]] | None = None,
) -> list:
    from google.genai import types
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ctx = f"Today's date: {today}\n"
    if room_context:
        ctx += "\nRoom context:\n" + json.dumps(room_context, indent=2, default=str) + "\n"

    contents = []
    if history:
        for i, turn in enumerate(history):
            role = "model" if turn.get("role") == "assistant" else "user"
            text = turn.get("text", "")
            if i == 0 and role == "user":
                text = ctx + text
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    else:
        contents.append(types.Content(role="user", parts=[types.Part(text=ctx + message)]))

    return contents


# ---------------------------------------------------------------------------
# Query tools
# ---------------------------------------------------------------------------

def _execute_query_tool(name: str, args: dict, room_id: str) -> dict:
    """Execute a query tool call against series_storage and return a result dict."""
    import series_storage as _ss
    if name == "list_occurrences":
        series_id = args.get("series_id", "")
        occs = _ss.list_occurrences_for_series(series_id)
        after = args.get("scheduled_after")
        before = args.get("scheduled_before")
        if after:
            occs = [o for o in occs if o.scheduled_for >= after]
        if before:
            occs = [o for o in occs if o.scheduled_for < before]
        limit = min(int(args.get("limit", 10)), 50)
        return {
            "occurrences": [
                {
                    "occurrence_id": o.occurrence_id,
                    "series_id": o.series_id,
                    "scheduled_for": o.scheduled_for,
                    "status": o.status,
                    "host": o.host,
                    "location": o.location,
                    "notes": o.overrides.notes if o.overrides else None,
                }
                for o in occs[:limit]
            ]
        }
    if name == "get_occurrence":
        occ = _ss.get_occurrence(args.get("occurrence_id", ""))
        if occ is None:
            return {"error": f"Occurrence not found: {args.get('occurrence_id')}"}
        return {
            "occurrence_id": occ.occurrence_id,
            "series_id": occ.series_id,
            "scheduled_for": occ.scheduled_for,
            "status": occ.status,
            "host": occ.host,
            "location": occ.location,
            "notes": occ.overrides.notes if occ.overrides else None,
            "links": occ.links,
        }
    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Gemini call (function-calling loop + JSON final response)
# ---------------------------------------------------------------------------

def _extract_json_object(text: str) -> str:
    """Pull the first {...} block out of text that may have prose or markdown fences."""
    start = text.find("{")
    if start == -1:
        return text
    end = text.rfind("}")
    if end < start:
        return text[start:]
    return text[start : end + 1]


def _call_ai(contents: list, room_id: str) -> dict:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is required for assistant functionality. "
            "Please set it to your Google AI API key."
        )
    model = os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
    client = genai.Client(api_key=api_key)

    query_tools = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="list_occurrences",
                description="List occurrences for a series, filtered by optional date range.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "series_id": types.Schema(
                            type=types.Type.STRING,
                            description="Series ID to query",
                        ),
                        "scheduled_after": types.Schema(
                            type=types.Type.STRING,
                            description="ISO 8601 UTC lower bound (inclusive)",
                        ),
                        "scheduled_before": types.Schema(
                            type=types.Type.STRING,
                            description="ISO 8601 UTC upper bound (exclusive)",
                        ),
                        "limit": types.Schema(
                            type=types.Type.INTEGER,
                            description="Max results to return (default 10, max 50)",
                        ),
                    },
                    required=["series_id"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_occurrence",
                description="Get full details of a single occurrence by ID.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "occurrence_id": types.Schema(
                            type=types.Type.STRING,
                            description="Occurrence ID",
                        ),
                    },
                    required=["occurrence_id"],
                ),
            ),
        ]
    )

    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        tools=[query_tools],
    )

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        working_contents = list(contents)
        response = None
        text: str | None = None
        try:
            for _ in range(_MAX_TOOL_ROUNDS):
                response = client.models.generate_content(
                    model=model,
                    contents=working_contents,
                    config=config,
                )
                working_contents.append(response.candidates[0].content)

                fn_calls = [
                    p for p in (response.candidates[0].content.parts or [])
                    if p.function_call
                ]
                if not fn_calls:
                    break

                tool_parts = []
                for part in fn_calls:
                    result = _execute_query_tool(
                        part.function_call.name,
                        dict(part.function_call.args),
                        room_id,
                    )
                    logger.info(
                        "Tool %s args=%s → %d keys",
                        part.function_call.name,
                        dict(part.function_call.args),
                        len(result),
                    )
                    tool_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=part.function_call.name,
                                response=result,
                            )
                        )
                    )
                working_contents.append(types.Content(role="user", parts=tool_parts))
            else:
                # Loop exhausted all rounds without a clean text response.
                # Do one final call without tools so the model is forced to produce JSON.
                logger.warning(
                    "Tool call loop exhausted after %d rounds; doing final text-only call",
                    _MAX_TOOL_ROUNDS,
                )
                text_only_config = types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                )
                response = client.models.generate_content(
                    model=model,
                    contents=working_contents,
                    config=text_only_config,
                )

            if response is None:
                raise ValueError("No response from AI")

            text = response.text
            if not text or not text.strip():
                raise ValueError("Gemini returned an empty response")

            result = json.loads(_extract_json_object(text))
            if not isinstance(result, dict) or "intent" not in result:
                raise ValueError(f"Unexpected AI response shape: {result!r}")
            return result

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            last_exc = exc
            logger.warning(
                "assistant AI attempt %d failed: %s | raw response text: %r",
                attempt + 1, exc, text,
            )
            continue

    raise last_exc or ValueError("AI call failed after retries")


# ---------------------------------------------------------------------------
# Action builder dispatch
# ---------------------------------------------------------------------------

_ACTION_BUILDERS = {
    "create_series": build_create_series_action,
    "create_occurrence": build_create_occurrence_action,
    "reschedule_occurrence": build_reschedule_occurrence_action,
    "draft_material": build_draft_material_action,
    "generate_reminder_text": build_generate_reminder_text_action,
    "update_occurrence_notes": build_update_occurrence_notes_action,
    "update_occurrence": build_update_occurrence_action,
    "update_room": build_update_room_action,
    "update_series": build_update_series_action,
}


def _build_and_save_actions(
    intent: str, ai_action: dict, room_id: str, uid: str
) -> list:
    """Build and persist one or more PendingActions from an AI action dict.

    Returns a list of PendingAction objects (may be empty).
    """
    builder = _ACTION_BUILDERS.get(intent)
    if builder is None:
        return []
    raw_payload = ai_action.get("payload", {})
    preview_override = ai_action.get("preview_summary")

    payloads = raw_payload if isinstance(raw_payload, list) else [raw_payload]
    results = []
    for item in payloads:
        p = builder(room_id, uid, item if isinstance(item, dict) else {})
        if preview_override and not results:
            p.preview_summary = preview_override
        save_pending_action(p)
        results.append(p)
    # Link batch actions: store sibling IDs on the first action
    if len(results) > 1:
        results[0].payload["_batch_action_ids"] = [a.action_id for a in results[1:]]
        save_pending_action(results[0])  # re-save with batch IDs
    return results


# ---------------------------------------------------------------------------
# Public streaming entry point
# ---------------------------------------------------------------------------

def run_assistant_stream(
    message: str,
    room_id: str,
    uid: str,
    room_context: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> Generator[dict, None, None]:
    """Stream assistant events for an organizer message."""
    yield {"type": "status", "message": "Thinking\u2026"}

    contents = _build_contents(message, room_context, history)
    try:
        ai_result = _call_ai(contents, room_id)
    except Exception as exc:
        logger.exception("AI call failed in assistant stream")
        yield {"type": "error", "message": str(exc)}
        return

    intent = ai_result.get("intent", "general_question")
    response_text = ai_result.get("response_text", "")
    ai_action = ai_result.get("action")

    logger.info("AI result: intent=%s, has_action=%s, action=%s",
                intent, ai_action is not None, json.dumps(ai_action, default=str)[:500] if ai_action else None)

    if response_text:
        yield {"type": "text_chunk", "text": response_text}

    if ai_action and intent != "general_question":
        try:
            actions = _build_and_save_actions(intent, ai_action, room_id, uid)
            if actions:
                previews = [a.preview_summary for a in actions]
                yield {
                    "type": "action_proposal",
                    "action_id": actions[0].action_id,
                    "action_ids": [a.action_id for a in actions],
                    "action_type": actions[0].action_type,
                    "preview_summary": "\n".join(previews),
                    "payload": actions[0].payload,
                }
        except Exception as exc:
            logger.exception("Failed to build/save action proposal")
            yield {"type": "status", "message": f"Could not prepare action: {exc}"}

    yield {"type": "done"}
