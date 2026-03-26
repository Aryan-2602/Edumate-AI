from __future__ import annotations

import json
import logging
from typing import Any, Dict

logger = logging.getLogger("edumate.workflow_metrics")


def log_workflow_event(payload: Dict[str, Any]) -> None:
    """Emit one machine-parseable JSON line (message body is raw JSON)."""
    logger.info("%s", json.dumps(payload, default=str))
