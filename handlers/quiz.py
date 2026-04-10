# AI-викторины: генерация по файлам, отправка quiz-опросов, обновление стрика

import asyncio
import logging
from datetime import datetime
from uuid import uuid4
from typing import Any

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import PollType
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, PollAnswerHandler

from ai.quiz_generator import QuizQuestion, generate_quiz
from config import (
    get_deepseek_api_key,
    get_gemini_api_key,
    get_gemini_proxy_api_key,
    get_gemini_proxy_base_url,
    get_gemini_proxy_model,
    get_groq_api_key,
    is_quiz_ai_configured,
)
from services.analytics import EV_QUIZ_COMPLETED, EV_QUIZ_GENERATED, schedule_track
from services.callback_feedback import (
    MSG_NO_DATABASE,
    MSG_QUIZ_AI_UNAVAILABLE,
    MSG_QUIZ_LIMIT_SHORT,
    answer_callback,
)
from constants import (
    CB_FILE_BACK,
    CB_FILE_TEST,
    CB_FILE_TEST_MORE,
    CB_NAV_MAIN,
    CB_SUB_BACK,
    CB_SUB_TEST,
    CB_SUB_TEST_MORE,
    UD_VIEWING_MATERIAL_ID,
    UD_VIEWING_SUBJECT_ID,
    UD_VIEWING_SUBJECT_NAME,
)
from db.models import Material
from db.repositories import (
    QUIZ_GENERATIONS_PER_DAY,
    get_material_by_id,
    get_materials_by_subject,
    get_quiz_generation_status,
    get_subject_by_id,
    record_quiz_generation,
    record_quiz_completion,
    update_streak,
)
from services.ui import em, ib
logger = logging.getLogger(__name__)

# Храним poll_id -> данные конкретного poll и session_id.
_QUIZ_POLLS_KEY = "quiz_polls"
_QUIZ_SESSIONS_KEY = "quiz_sessions"
_QUIZ_HISTORY_KEY = "quiz_history"

def _get_quiz_polls(context: ContextTypes.DEFAULT_TYPE) -> dict[str, dict[str, Any]]:
    if _QUIZ_POLLS_KEY not in context.bot_data:
        context.bot_data[_QUIZ_POLLS_KEY] = {}
    return context.bot_data[_QUIZ_POLLS_KEY]


def _get_quiz_sessions(context: ContextTypes.DEFAULT_TYPE) -> dict[str, dict[str, Any]]:
    if _QUIZ_SESSIONS_KEY not in context.bot_data:
        context.bot_data[_QUIZ_SESSIONS_KEY] = {}
    return context.bot_data[_QUIZ_SESSIONS_KEY]


def _get_quiz_history(context: ContextTypes.DEFAULT_TYPE) -> dict[str, list[str]]:
    if _QUIZ_HISTORY_KEY not in context.bot_data:
        context.bot_data[_QUIZ_HISTORY_KEY] = {}
    return context.bot_data[_QUIZ_HISTORY_KEY]


def _make_quiz_history_key(
    user_id: int,
    kind: str,
    subject_id: int | None = None,
    material_id: int | None = None,
) -> str | None:
    if kind == "file" and material_id is not None:
        return f"{user_id}:file:{material_id}"
    if kind == "subject" and subject_id is not None:
        return f"{user_id}:subject:{subject_id}"
    return None


def _get_history_questions(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    kind: str,
    subject_id: int | None = None,
    material_id: int | None = None,
) -> list[str]:
    history_key = _make_quiz_history_key(user_id, kind, subject_id, material_id)
    if not history_key:
        return []
    return list(_get_quiz_history(context).get(history_key, []))


def _remember_questions(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    kind: str,
    questions: list[str],
    subject_id: int | None = None,
    material_id: int | None = None,
) -> None:
    history_key = _make_quiz_history_key(user_id, kind, subject_id, material_id)
    if not history_key or not questions:
        return
    history = _get_quiz_history(context)
    history.setdefault(history_key, [])
    for question in questions:
        if question not in history[history_key]:
            history[history_key].append(question)


def _get_quiz_summary_keyboard(
    kind: str,
    subject_id: int | None = None,
    material_id: int | None = None,
) -> InlineKeyboardMarkup:
    back_cb = CB_FILE_BACK if kind == "file" else CB_SUB_BACK
    rows: list[list[Any]] = []
    if kind == "file" and material_id is not None:
        rows.append([ib("➕ Ещё 3 вопроса", callback_data=f"{CB_FILE_TEST_MORE}{material_id}", style="primary")])
    elif kind == "subject" and subject_id is not None:
        rows.append([ib("➕ Ещё 3 вопроса", callback_data=f"{CB_SUB_TEST_MORE}{subject_id}", style="primary")])
    rows.append([ib("🔙 Назад", callback_data=back_cb), ib("🏠 Главное меню", callback_data=CB_NAV_MAIN)])
    return InlineKeyboardMarkup(rows)


def _format_generation_reset_at(reset_at: datetime) -> str:
    return reset_at.strftime("%d.%m в %H:%M")


def _build_quiz_limit_text(*, used_today: int, reset_at: datetime) -> str:
    return em(
        "⚠️ Лимит генерации тестов на сегодня исчерпан.\n\n"
        f"Сегодня использовано: {used_today}/{QUIZ_GENERATIONS_PER_DAY}\n"
        f"Новые тесты можно будет сгенерировать после {_format_generation_reset_at(reset_at)}."
    )


def _build_quiz_summary_text(
    *,
    title: str,
    total_questions: int,
    correct_answers: int,
    wrong_answers: int,
    passed: bool,
    learned_count: int,
    total_materials: int,
    streak_days: int,
    streak_event: str,
) -> str:
    lines = [
        f"{'✅' if passed else '📝'} <b>{title}</b>",
        "",
        f"Верно: {correct_answers}/{total_questions}",
        f"Ошибок: {wrong_answers}",
    ]
    if total_materials > 0:
        lines.append(f"🧠 Выучено тем: {learned_count}/{total_materials}")
    if streak_event == "started":
        lines.append(f"🔥 Тестовый стрик начат: {streak_days} день")
    elif streak_event == "continued":
        lines.append(f"🔥 Тестовый стрик продолжается: {streak_days} дней")
    elif streak_event == "reset":
        lines.append(f"🔥 Тестовый стрик начат заново: {streak_days} день")
    elif streak_event == "same":
        lines.append(f"🔥 Тестовый стрик на сегодня уже засчитан: {streak_days} дней")
    return em("\n".join(lines))


async def _download_material_file(bot, material: Material) -> bytes | None:
    if not material.telegram_file_id:
        return None
    try:
        tg_file = await bot.get_file(material.telegram_file_id)
        buf = await tg_file.download_as_bytearray()
        return bytes(buf)
    except Exception as e:
        logger.warning("Download material %s failed: %s", material.id, e)
        return None


def _material_to_tuple(m: Material, data: bytes | None) -> tuple[bytes | None, str | None, str | None, str | None]:
    return (data, m.url, m.mime_type, m.original_filename)


async def _run_quiz_generation(
    materials: list[tuple[bytes | None, str | None, str | None, str | None]],
    subject_name: str,
    num_questions: int = 3,
    exclude_questions: list[str] | None = None,
    *,
    gemini_proxy_key: str | None = None,
    gemini_proxy_base_url: str | None = None,
    gemini_proxy_model: str = "gemini-3.1-flash-lite-preview",
    deepseek_key: str | None = None,
    groq_key: str | None = None,
    gemini_key: str | None = None,
) -> list[QuizQuestion]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: generate_quiz(
            materials, subject_name, num_questions,
            exclude_questions=exclude_questions,
            gemini_proxy_key=gemini_proxy_key,
            gemini_proxy_base_url=gemini_proxy_base_url,
            gemini_proxy_model=gemini_proxy_model,
            deepseek_key=deepseek_key,
            groq_key=groq_key,
            gemini_key=gemini_key,
        ),
    )


async def _send_quiz_polls(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    questions: list[QuizQuestion],
    *,
    kind: str,
    title: str,
    subject_id: int | None = None,
    material_id: int | None = None,
) -> int:
    polls = _get_quiz_polls(context)
    sessions = _get_quiz_sessions(context)
    session_id = uuid4().hex
    sessions[session_id] = {
        "user_id": user_id,
        "chat_id": chat_id,
        "kind": kind,
        "title": title,
        "subject_id": subject_id,
        "material_id": material_id,
        "total_questions": len(questions),
        "answered_questions": 0,
        "correct_answers": 0,
        "wrong_answers": 0,
    }
    sent_polls = 0
    sent_question_texts: list[str] = []
    for q in questions:
        try:
            msg = await context.bot.send_poll(
                chat_id=chat_id,
                question=q.question,
                options=q.options,
                type=PollType.QUIZ,
                is_anonymous=False,
                correct_option_id=q.correct_index,
                explanation=q.explanation or None,
            )
            if msg.poll:
                polls[msg.poll.id] = {
                    "session_id": session_id,
                    "correct_index": q.correct_index,
                }
                sent_polls += 1
                sent_question_texts.append(q.question)
        except Exception as e:
            logger.exception("send_poll failed: %s", e)
    if sent_polls == 0:
        sessions.pop(session_id, None)
        return 0
    sessions[session_id]["total_questions"] = sent_polls
    _remember_questions(context, user_id, kind, sent_question_texts, subject_id, material_id)
    return sent_polls


async def _check_quiz_generation_limit(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> bool:
    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        await answer_callback(query, MSG_NO_DATABASE, alert=True)
        return False
    async with session_factory() as session:
        status = await get_quiz_generation_status(session, user_id)
    if status.allowed:
        return True
    await answer_callback(query, MSG_QUIZ_LIMIT_SHORT, alert=True)
    if query.message:
        await query.message.reply_text(
            _build_quiz_limit_text(used_today=status.used_today, reset_at=status.next_reset_at),
            parse_mode="HTML",
        )
    return False


async def _mark_quiz_generation_used(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        return
    async with session_factory() as session:
        await record_quiz_generation(session, user_id)


async def on_test_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тест по всем файлам предмета."""
    query = update.callback_query
    uid = update.effective_user.id
    if query.data and query.data.startswith(CB_SUB_TEST_MORE):
        try:
            subject_id = int(query.data.removeprefix(CB_SUB_TEST_MORE))
        except ValueError:
            await answer_callback(query, "Не удалось определить предмет.", alert=True)
            return
    else:
        subject_id = context.user_data.get(UD_VIEWING_SUBJECT_ID)

    if not subject_id:
        await answer_callback(query, "Открой предмет ещё раз и нажми «Тест».", alert=True)
        return
    if not await _check_quiz_generation_limit(query, context, uid):
        return

    if not is_quiz_ai_configured():
        await answer_callback(query, MSG_QUIZ_AI_UNAVAILABLE, alert=True)
        return

    gemini_proxy_key = get_gemini_proxy_api_key()
    gemini_proxy_base_url = get_gemini_proxy_base_url()
    gemini_proxy_model = get_gemini_proxy_model()
    deepseek_key = get_deepseek_api_key()
    groq_key = get_groq_api_key()
    gemini_key = get_gemini_api_key()

    await answer_callback(query)

    status_msg = await query.message.reply_text(
        em("🧠 Готовлю вопросы по материалам... Это займет несколько секунд."),
        parse_mode="HTML",
    )

    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        await status_msg.edit_text(em(MSG_NO_DATABASE), parse_mode="HTML")
        return

    try:
        async with session_factory() as session:
            subject = await get_subject_by_id(session, subject_id, uid)
            if not subject:
                await status_msg.edit_text(em("⚠️ Предмет не найден."), parse_mode="HTML")
                return
            materials = await get_materials_by_subject(session, subject_id, uid)

        file_materials = [m for m in materials if m.telegram_file_id]
        if not file_materials:
            await status_msg.edit_text(em("📂 В предмете нет файлов для викторины."), parse_mode="HTML")
            return

        material_tuples: list[tuple[bytes | None, str | None, str | None, str | None]] = []
        for m in file_materials[:10]:
            data = await _download_material_file(context.bot, m)
            material_tuples.append(_material_to_tuple(m, data))

        excluded_questions = _get_history_questions(context, uid, "subject", subject_id=subject.id)
        questions = await _run_quiz_generation(
            material_tuples, subject.name, num_questions=3,
            exclude_questions=excluded_questions,
            gemini_proxy_key=gemini_proxy_key,
            gemini_proxy_base_url=gemini_proxy_base_url,
            gemini_proxy_model=gemini_proxy_model,
            deepseek_key=deepseek_key,
            groq_key=groq_key,
            gemini_key=gemini_key,
        )

        if not questions:
            await status_msg.edit_text(
                em(
                    "⚠️ Не удалось сгенерировать новые вопросы.\n\n"
                    "Возможные причины: недоступен AI-провайдер, в материалах мало извлекаемого текста "
                    "или новые вопросы без повторов закончились."
                ),
                parse_mode="HTML",
            )
            return

        await status_msg.delete()
        sent_polls = await _send_quiz_polls(
            context,
            query.message.chat_id,
            uid,
            questions,
            kind="subject",
            title=f"Тест по предмету «{subject.name}»",
            subject_id=subject.id,
        )
        if sent_polls > 0:
            await _mark_quiz_generation_used(context, uid)
            schedule_track(
                context,
                uid,
                EV_QUIZ_GENERATED,
                {
                    "kind": "subject",
                    "subject_id": subject.id,
                    "material_id": None,
                    "question_count": len(questions),
                },
            )
    except Exception as e:
        logger.exception("Quiz generation failed: %s", e)
        try:
            await status_msg.edit_text(em("⚠️ Ошибка генерации. Попробуй позже."), parse_mode="HTML")
        except Exception:
            pass


async def on_file_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тест по одному файлу."""
    query = update.callback_query
    uid = update.effective_user.id
    if query.data and query.data.startswith(CB_FILE_TEST_MORE):
        try:
            material_id = int(query.data.removeprefix(CB_FILE_TEST_MORE))
        except ValueError:
            await answer_callback(query, "Не удалось определить файл.", alert=True)
            return
    else:
        material_id = context.user_data.get(UD_VIEWING_MATERIAL_ID)

    if not material_id:
        await answer_callback(query, "Открой файл ещё раз и нажми «Тест».", alert=True)
        return
    if not await _check_quiz_generation_limit(query, context, uid):
        return

    if not is_quiz_ai_configured():
        await answer_callback(query, MSG_QUIZ_AI_UNAVAILABLE, alert=True)
        return

    gemini_proxy_key = get_gemini_proxy_api_key()
    gemini_proxy_base_url = get_gemini_proxy_base_url()
    gemini_proxy_model = get_gemini_proxy_model()
    deepseek_key = get_deepseek_api_key()
    groq_key = get_groq_api_key()
    gemini_key = get_gemini_api_key()

    await answer_callback(query)

    status_msg = await query.message.reply_text(
        em("🧠 Готовлю вопросы по файлу... Это займет несколько секунд."),
        parse_mode="HTML",
    )

    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        await status_msg.edit_text(em(MSG_NO_DATABASE), parse_mode="HTML")
        return

    try:
        async with session_factory() as session:
            material = await get_material_by_id(session, material_id, uid)

        if not material:
            await status_msg.edit_text(em("⚠️ Файл не найден."), parse_mode="HTML")
            return

        if material.url:
            await status_msg.edit_text(
                em("⚠️ Тесты по ссылкам больше не поддерживаются. Загрузи материал файлом."),
                parse_mode="HTML",
            )
            return
        if material.telegram_file_id:
            data = await _download_material_file(context.bot, material)
            material_tuples = [_material_to_tuple(material, data)]
        else:
            await status_msg.edit_text(em("⚠️ Файл недоступен для анализа."), parse_mode="HTML")
            return

        name = material.original_filename or "файл"
        excluded_questions = _get_history_questions(context, uid, "file", material_id=material.id)
        questions = await _run_quiz_generation(
            material_tuples, name, num_questions=3,
            exclude_questions=excluded_questions,
            gemini_proxy_key=gemini_proxy_key,
            gemini_proxy_base_url=gemini_proxy_base_url,
            gemini_proxy_model=gemini_proxy_model,
            deepseek_key=deepseek_key,
            groq_key=groq_key,
            gemini_key=gemini_key,
        )

        if not questions:
            await status_msg.edit_text(
                em(
                    "⚠️ Не удалось сгенерировать новые вопросы.\n\n"
                    "Возможные причины: недоступен AI-провайдер, в файле мало извлекаемого текста "
                    "или новые вопросы без повторов закончились."
                ),
                parse_mode="HTML",
            )
            return

        await status_msg.delete()
        sent_polls = await _send_quiz_polls(
            context,
            query.message.chat_id,
            uid,
            questions,
            kind="file",
            title=f"Тест по «{name}»",
            subject_id=material.subject_id,
            material_id=material.id,
        )
        if sent_polls > 0:
            await _mark_quiz_generation_used(context, uid)
            schedule_track(
                context,
                uid,
                EV_QUIZ_GENERATED,
                {
                    "kind": "file",
                    "subject_id": material.subject_id,
                    "material_id": material.id,
                    "question_count": len(questions),
                },
            )
    except Exception as e:
        logger.exception("Quiz generation failed: %s", e)
        try:
            await status_msg.edit_text(em("⚠️ Ошибка генерации. Попробуй позже."), parse_mode="HTML")
        except Exception:
            pass


async def on_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ответа на викторину: обновление стрика при правильном ответе."""
    answer = update.poll_answer
    if not answer:
        return

    poll_id = answer.poll_id
    polls = _get_quiz_polls(context)
    meta = polls.pop(poll_id, None)
    if not meta:
        return

    session_id = meta.get("session_id")
    correct_index = meta.get("correct_index", -1)
    option_ids = answer.option_ids or []
    sessions = _get_quiz_sessions(context)
    session_meta = sessions.get(session_id) if session_id else None

    if not option_ids or session_meta is None:
        return

    # option_ids — индексы выбранных вариантов (для quiz — один)
    is_correct = option_ids[0] == correct_index if option_ids else False
    session_meta["answered_questions"] += 1
    if is_correct:
        session_meta["correct_answers"] += 1
    else:
        session_meta["wrong_answers"] += 1

    if session_meta["answered_questions"] < session_meta["total_questions"]:
        return

    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        return

    user_id = session_meta.get("user_id")
    subject_id = session_meta.get("subject_id")
    material_id = session_meta.get("material_id")
    total_questions = int(session_meta.get("total_questions") or 0)
    correct_answers = int(session_meta.get("correct_answers") or 0)
    wrong_answers = int(session_meta.get("wrong_answers") or 0)
    passed = correct_answers >= max(1, (total_questions + 1) // 2)

    learned_count = 0
    total_materials = 0
    streak_days = 0
    streak_event = "same"
    try:
        async with session_factory() as session:
            learned_count, total_materials = await record_quiz_completion(
                session,
                user_id,
                subject_id=subject_id,
                material_id=material_id,
                correct_answers=correct_answers,
                wrong_answers=wrong_answers,
                passed=passed,
            )
            streak_days, streak_event = await update_streak(session, user_id)
    except Exception as e:
        logger.exception("quiz completion update failed: %s", e)
        return

    schedule_track(
        context,
        user_id,
        EV_QUIZ_COMPLETED,
        {
            "passed": passed,
            "correct_answers": correct_answers,
            "wrong_answers": wrong_answers,
            "total_questions": total_questions,
        },
    )

    summary_text = _build_quiz_summary_text(
        title=session_meta.get("title") or "Тест завершён",
        total_questions=total_questions,
        correct_answers=correct_answers,
        wrong_answers=wrong_answers,
        passed=passed,
        learned_count=learned_count,
        total_materials=total_materials,
        streak_days=streak_days,
        streak_event=streak_event,
    )
    try:
        await context.bot.send_message(
            chat_id=session_meta["chat_id"],
            text=summary_text,
            reply_markup=_get_quiz_summary_keyboard(
                session_meta.get("kind") or "subject",
                subject_id=session_meta.get("subject_id"),
                material_id=session_meta.get("material_id"),
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("quiz summary send failed: %s", e)
    finally:
        if session_id:
            sessions.pop(session_id, None)


def register(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(on_test_all, pattern=rf"^{CB_SUB_TEST}$"))
    app.add_handler(CallbackQueryHandler(on_file_test, pattern=rf"^{CB_FILE_TEST}$"))
    app.add_handler(CallbackQueryHandler(on_test_all, pattern=rf"^{CB_SUB_TEST_MORE}\d+$"))
    app.add_handler(CallbackQueryHandler(on_file_test, pattern=rf"^{CB_FILE_TEST_MORE}\d+$"))
    app.add_handler(PollAnswerHandler(on_poll_answer))
