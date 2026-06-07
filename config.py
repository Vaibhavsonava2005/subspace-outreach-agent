"""
Configuration management for Subspace Cold Outreach Agent.
Created by Vaibhav Sonava

Loads environment variables from .env and exposes them as a validated
configuration dictionary consumed by every pipeline stage.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent / ".env"

_KEY_MAP: dict[str, str] = {
    "ocean_api_key": "OCEAN_API_KEY",
    "prospeo_api_key": "PROSPEO_API_KEY",
    "brevo_api_key": "BREVO_API_KEY",
    "sender_email": "SENDER_EMAIL",
    "sender_name": "SENDER_NAME",
}

_REQUIRED_KEYS: set[str] = {"brevo_api_key", "sender_email"}

# ---------------------------------------------------------------------------
# Logging bootstrap
# ---------------------------------------------------------------------------
logger.remove()  # remove default stderr sink
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    level="DEBUG",
    colorize=True,
)
logger.add(
    "logs/outreach_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    enqueue=True,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load_config() -> dict[str, str | None]:
    """Load configuration from the ``.env`` file and validate it.

    Returns
    -------
    dict[str, str | None]
        A dictionary with the following keys:
        ``ocean_api_key``, ``prospeo_api_key``,
        ``brevo_api_key``, ``sender_email``, ``sender_name``.
        Values are ``None`` when the corresponding env-var is unset.

    Raises
    ------
    SystemExit
        When *required* keys (``brevo_api_key``, ``sender_email``) are
        missing — the pipeline cannot operate without email delivery
        credentials.
    """

    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)
        logger.info("Loaded environment from {}", _ENV_PATH)
    else:
        logger.warning(
            ".env file not found at {}. Falling back to system environment variables.",
            _ENV_PATH,
        )

    config: dict[str, str | None] = {}
    for key, env_var in _KEY_MAP.items():
        value = os.getenv(env_var)
        config[key] = value if value else None

        if value:
            # Mask the value so secrets never leak into logs
            masked = value[:4] + "****" if len(value) > 4 else "****"
            logger.debug("  {} = {}", key, masked)
        else:
            logger.debug("  {} = <not set>", key)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    missing = [k for k in _REQUIRED_KEYS if not config.get(k)]
    if missing:
        logger.warning(
            "Required configuration keys are missing: {}. "
            "Email delivery will fail without these.",
            ", ".join(missing),
        )

    optional_missing = [
        k for k in _KEY_MAP if k not in _REQUIRED_KEYS and not config.get(k)
    ]
    if optional_missing:
        logger.info(
            "Optional keys not configured (stages may be skipped): {}",
            ", ".join(optional_missing),
        )

    logger.success("Configuration loaded successfully.")
    return config
