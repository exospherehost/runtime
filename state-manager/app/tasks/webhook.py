import logging
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def dispatch_webhook(
    *,
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
) -> None:
    """
    Dispatch a webhook event.
    This must never raise exceptions (best-effort delivery).
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                url,
                json=payload,
                headers=headers or {},
            )
    except Exception as exc:
        logger.warning(
            "Webhook dispatch failed",
            exc_info=exc,
            extra={"url": url},
        )
