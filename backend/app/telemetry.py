"""Optional experiment / metrics logging (Weights & Biases)."""

from __future__ import annotations

import logging
from typing import Any, Dict

import wandb

from app.config import settings

logger = logging.getLogger(__name__)


def log_metrics(data: Dict[str, Any]) -> None:
    """Log a metrics dict if a W&B run is active."""
    if not settings.wandb_api_key:
        return
    try:
        if wandb.run is not None:
            wandb.log(data)
    except Exception as e:
        logger.debug("W&B log skipped: %s", e)


def init_wandb() -> None:
    """Start a single API-level run (call once from app lifespan)."""
    if not settings.wandb_api_key:
        return
    try:
        wandb.login(key=settings.wandb_api_key)
        wandb.init(project=settings.wandb_project, job_type="api")
    except Exception as e:
        logger.warning("Failed to initialize W&B: %s", e)


def finish_wandb() -> None:
    if wandb.run is not None:
        try:
            wandb.finish()
        except Exception:
            pass
