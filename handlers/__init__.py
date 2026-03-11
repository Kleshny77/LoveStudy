# порядок регистрации критичен:
# ConversationHandler (mat:*, sub:add:*) должен быть до глобальных CallbackQueryHandler-ов,
# иначе глобальный sub:* хендлер перехватит sub:add:* раньше ConversationHandler.

from telegram.ext import Application

from .achievements import register as register_achievements
from .error import register as register_error
from .material_upload import register as register_material_upload
from .quiz import register as register_quiz
from .pomodoro import register as register_pomodoro
from .friends import register as register_friends
from .deadlines import register as register_deadlines
from .profile import register as register_profile
from .start import register as register_start
from .main_menu import register as register_main_menu
from .subjects import register as register_subjects
from .telegram_setup import register as register_telegram_setup


def register_handlers(app: Application) -> None:
    register_error(app)           # error handler (не влияет на порядок updates)
    register_material_upload(app) # ConversationHandler (mat:upload, mat:more, sub:add:*) — первым
    register_pomodoro(app)        # ConversationHandler (pom:cust) + pom:* callbacks
    register_friends(app)         # ConversationHandler (fri:fprof) + fri:* callbacks
    register_deadlines(app)       # ConversationHandler (ddl:*) + deadline callbacks
    register_profile(app)         # prof:* callbacks
    register_start(app)           # /start
    register_telegram_setup(app)  # slash-команды и private-only redirects
    register_achievements(app)    # общие экраны достижений
    register_main_menu(app)       # main:* и nav:main
    register_subjects(app)        # sub:s:*, sub:f:*, sub:del, sub:pg:*, ...
    register_quiz(app)            # sub:tst, sub:fts, poll_answer
