"""Safe JSON array extraction and validation for quiz / flashcards."""

from __future__ import annotations

import json
from typing import Any, List, Tuple

_VALID_MC_ANSWERS = frozenset("ABCD")


def parse_json_array_from_llm(raw: str) -> Tuple[List[Any] | None, str | None]:
    text = (raw or "").strip()
    if not text:
        return None, "empty_raw"
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data, None
        return None, "root_not_array"
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end])
                if isinstance(data, list):
                    return data, None
                return None, "extracted_not_array"
            except json.JSONDecodeError:
                return None, "malformed_json_bracket_extract"
        return None, "malformed_json"


def validate_quiz_items(items: List[Any], expected: int) -> Tuple[bool, str]:
    if not isinstance(items, list):
        return False, "not_a_list"
    if len(items) < expected:
        return False, "too_few_items"
    if len(items) > expected + 2:
        return False, "too_many_items"

    for i in range(expected):
        item = items[i]
        if not isinstance(item, dict):
            return False, f"item_{i}_not_object"
        q = item.get("question")
        opts = item.get("options")
        ca = item.get("correct_answer")
        if not q or not isinstance(q, str) or not str(q).strip():
            return False, f"item_{i}_bad_question"
        if not isinstance(opts, list) or len(opts) != 4:
            return False, f"item_{i}_bad_options"
        if not ca or str(ca).strip().upper() not in _VALID_MC_ANSWERS:
            return False, f"item_{i}_bad_correct_answer"

    return True, ""


def validate_flashcard_items(items: List[Any], expected: int) -> Tuple[bool, str]:
    if not isinstance(items, list):
        return False, "not_a_list"
    if len(items) < expected:
        return False, "too_few_items"
    if len(items) > expected + 2:
        return False, "too_many_items"

    for i in range(expected):
        item = items[i]
        if not isinstance(item, dict):
            return False, f"item_{i}_not_object"
        front = item.get("front", "")
        back = item.get("back", "")
        if not str(front).strip() or not str(back).strip():
            return False, f"item_{i}_empty_front_or_back"

    return True, ""
