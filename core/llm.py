"""Provider-agnostic JSON completion with Pydantic validation and retries."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class LLMError(Exception):
    pass


def extract_json_object(text: str) -> str:
    if not text:
        raise LLMError("Empty model response.")
    fence = JSON_FENCE_RE.search(text)
    if fence:
        return fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise LLMError("No JSON object found in model response.")


def _schema_hint(schema: type[BaseModel]) -> str:
    return json.dumps(schema.model_json_schema(), indent=2)


CompleteFn = Callable[[str, str, type[BaseModel]], BaseModel]


def complete_json(
    system: str,
    user: str,
    schema: type[T],
    *,
    provider: str = "anthropic",
    model: str | None = None,
    api_key: str | None = None,
    max_retries: int = 2,
    complete_raw: Callable[[str, str], str] | None = None,
) -> T:
    """Return a validated Pydantic object. Retries when JSON is malformed.

    `complete_raw(system, user) -> str` may be injected (tests / demo).
    Default provider is Anthropic via the official SDK.
    """
    last_err = "unknown"
    hint = _schema_hint(schema)
    extra = ""
    for attempt in range(max_retries + 1):
        prompt = (
            f"{user}\n\n"
            "Return ONLY a JSON object that validates against this JSON Schema. "
            "Do not invent papers, URLs, authors, dates, or deadlines. "
            "Cite only source IDs that appear in the evidence list.\n"
            f"JSON Schema:\n{hint}\n"
            f"{extra}"
        )
        try:
            if complete_raw is not None:
                raw = complete_raw(system, prompt)
            elif provider == "anthropic":
                raw = _anthropic_complete(system, prompt, api_key=api_key, model=model)
            else:
                raise LLMError(f"Unknown LLM provider: {provider}")
            blob = extract_json_object(raw)
            data = json.loads(blob)
            return schema.model_validate(data)
        except (json.JSONDecodeError, LLMError, ValidationError, ValueError) as exc:
            last_err = str(exc)
            extra = (
                f"\nYour previous output failed validation: {last_err}\n"
                "Reply with corrected JSON only."
            )
    raise LLMError(f"Model did not return valid JSON after retries: {last_err}")


def _anthropic_complete(system: str, user: str, *, api_key: str | None, model: str | None) -> str:
    if not api_key:
        raise LLMError("Language-model credentials are missing.")
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise LLMError("The anthropic package is not installed.") from exc

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model or "claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts: list[str] = []
    for block in resp.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()
