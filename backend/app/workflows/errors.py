from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class WorkflowError(Exception):
    message: str
    details: Optional[Dict[str, Any]] = None


class NotFound(WorkflowError):
    pass


class ValidationError(WorkflowError):
    pass


class GuardrailError(WorkflowError):
    pass


class InternalError(WorkflowError):
    pass

