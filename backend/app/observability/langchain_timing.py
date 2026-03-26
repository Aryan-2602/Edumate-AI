"""LangChain callback helpers for token usage (legacy + chat models)."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from langchain.callbacks.base import BaseCallbackHandler


def normalize_token_usage(raw: Any) -> Optional[Dict[str, int]]:
    """Flatten vendor-specific token usage to prompt/completion/total ints."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    out: Dict[str, int] = {}
    # OpenAI-style
    if "prompt_tokens" in raw:
        out["prompt_tokens"] = int(raw["prompt_tokens"])
    if "completion_tokens" in raw:
        out["completion_tokens"] = int(raw["completion_tokens"])
    if "total_tokens" in raw:
        out["total_tokens"] = int(raw["total_tokens"])
    # Some responses nest usage
    if not out and "usage" in raw and isinstance(raw["usage"], dict):
        return normalize_token_usage(raw["usage"])
    return out or None


def token_usage_from_llm_result(response: Any) -> Optional[Dict[str, int]]:
    """Read token_usage from an LLMResult (LangChain callbacks / chains)."""
    if response is None:
        return None
    llm_out = getattr(response, "llm_output", None)
    if isinstance(llm_out, dict):
        tu = normalize_token_usage(llm_out.get("token_usage"))
        if tu:
            return tu
    gens = getattr(response, "generations", None) or []
    for gen_list in gens:
        if not gen_list:
            continue
        g0 = gen_list[0]
        gi = getattr(g0, "generation_info", None)
        if isinstance(gi, dict):
            tu = normalize_token_usage(gi.get("token_usage"))
            if tu:
                return tu
    return None


def token_usage_from_chat_message(msg: Any) -> Optional[Dict[str, int]]:
    """Extract usage from AIMessage after llm.invoke (ChatOpenAI)."""
    if msg is None:
        return None
    meta = getattr(msg, "response_metadata", None) or {}
    if isinstance(meta, dict):
        tu = normalize_token_usage(meta.get("token_usage"))
        if tu:
            return tu
    # usage_metadata (newer LC)
    um = getattr(msg, "usage_metadata", None)
    if isinstance(um, dict):
        mapped = {
            k: um[k]
            for k in ("input_tokens", "output_tokens", "total_tokens")
            if k in um
        }
        if mapped:
            out: Dict[str, int] = {}
            if "input_tokens" in mapped:
                out["prompt_tokens"] = int(mapped["input_tokens"])
            if "output_tokens" in mapped:
                out["completion_tokens"] = int(mapped["output_tokens"])
            if "total_tokens" in mapped:
                out["total_tokens"] = int(mapped["total_tokens"])
            return out
    add = getattr(msg, "additional_kwargs", None) or {}
    if isinstance(add, dict):
        return normalize_token_usage(add.get("token_usage"))
    return None


class LlmUsageCaptureHandler(BaseCallbackHandler):
    """Capture the last completed LLM run's token usage (aggregate in chains)."""

    def __init__(self) -> None:
        self.last_usage: Optional[Dict[str, int]] = None

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        tu = token_usage_from_llm_result(response)
        if tu:
            self.last_usage = tu
