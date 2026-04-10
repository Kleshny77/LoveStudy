# Асинхронная запись событий в PostgreSQL для дашбордов (Metabase, DataLens).
# Не блокирует хендлеры: INSERT в фоне через asyncio.create_task.

from __future__ import annotations

import asyncio
import logging
from typing import Any, Mapping

from config import get_analytics_enabled
from db.models import AnalyticsEvent

logger = logging.getLogger(__name__)

# Имена событий — держим стабильными для SQL/Metabase.
EV_MAIN_MENU_SHOWN = "main_menu_shown"
EV_OPEN_SCREEN = "open_screen"
EV_MATERIAL_SAVED = "material_saved"
EV_DEADLINE_CREATED = "deadline_created"
EV_POMODORO_WORK_DONE = "pomodoro_work_completed"
EV_QUIZ_COMPLETED = "quiz_session_completed"
EV_SUBSCRIPTION_PAID = "subscription_paid"


def schedule_track(
    context: Any,
    user_id: int | None,
    event_name: str,
    properties: Mapping[str, Any] | None = None,
) -> None:
    """Ставит запись события в фоне. Без БД или при ANALYTICS_ENABLED=0 — no-op."""
    if not get_analytics_enabled() or user_id is None:
        return
    factory = context.bot_data.get("session_factory") if context and context.bot_data else None
    if factory is None:
        return
    asyncio.create_task(_insert_event(factory, user_id, event_name, properties))


async def _insert_event(
    factory: Any,
    user_id: int,
    event_name: str,
    properties: Mapping[str, Any] | None,
) -> None:
    try:
        props = dict(properties) if properties else None
        async with factory() as session:
            session.add(
                AnalyticsEvent(
                    user_telegram_id=user_id,
                    event_name=event_name[:128],
                    properties=props,
                )
            )
            await session.commit()
    except Exception:
        logger.debug("analytics: не удалось записать %s", event_name, exc_info=True)
