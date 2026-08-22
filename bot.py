"""
Telegram-бот для запису на консультації — Олександра Дахно, психологиня
(підлітки та батьки).

Флоу:
/start
 -> ім'я та прізвище
 -> вперше чи вже була на консультації
 -> перевірка запиту
 -> якщо "так": вибір формату
 -> політика оплати та скасування
 -> опис запиту + контакт
 -> заявка надсилається власниці в Telegram
 -> користувачу надсилається підтвердження
"""

import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_CHAT_ID = os.environ["OWNER_CHAT_ID"]

CARD_NUMBER = os.environ["CARD_NUMBER"]
CARD_HOLDER = os.environ["CARD_HOLDER"]


# ============================================================
# TEXTS
# ============================================================

SCOPE_TEXT = (
    "перевір, будь ласка, чи я працюю з твоїм запитом:\n\n"

    "🟢 З ЧИМ Я ПРАЦЮЮ\n"
    "• шкільна тривожність\n"
    "• булінг та конфлікти з однолітками\n"
    "• самооцінка та впевненість\n"
    "• ресурсний стан, виснаження\n"
    "• профорієнтація\n"
    "• стосунки з батьками (для підлітків)\n"
    "• як говорити з підлітком (для батьків)\n"
    "• адаптація / переїзд\n\n"

    "🔴 З ЧИМ НЕ ПРАЦЮЮ\n"
    "• клінічні розлади (психотичні стани, депресія, ПТСР)\n"
    "• суїцидальні думки, самопошкодження\n"
    "• розлади харчової поведінки\n"
    "• залежності\n"
    "• глибока травма\n"
    "• випадки насильства в сім'ї\n\n"

    "якщо запит не пасує — можу порадити, до кого звернутись"
)


FORMATS_TEXT = (
    "чудово! обери формат роботи 🤍\n\n"

    "ознайомча зустріч (30 хв / 500 ₴)\n"
    "знайомство, формування запиту, узгодження подальшої роботи\n\n"

    "повна консультація (50 хв / 1000 ₴)\n"
    "повноцінна сесія по твоєму запиту"
)


POLICY_TEXT = (
    "окей!\n\n"

    "оплата 100% вартості — перед консультацією, "
    "запис підтверджується лише після оплати ✍️\n\n"

    "скасування/перенесення можливе не пізніше ніж за 24 години "
    "до зустрічі, інакше консультація вважається проведеною.\n\n"

    "консультації проходять онлайн (Google Meet), "
    "посилання надсилаю після підтвердження оплати.\n\n"

    "тепер коротко напиши, з яким запитом звертаєшся 🤍"
)


# ============================================================
# CONVERSATION STATES
# ============================================================

NAME, FIRST_TIME, SCOPE_CHECK, FORMAT_CHOICE, POLICY_ACK, DESCRIBING, CONTACT, PAYMENT = range(8)


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    # Log Telegram user information to Railway
    logger.info(
        f"👤 USER INFO | "
        f"id={user.id} | "
        f"username=@{user.username or 'no_username'} | "
        f"name={user.full_name}"
    )

    await update.message.reply_text(
        "вітаю у боті «Ваш психолог Саша✨» 🤍\n\n"
        "вкажи, будь ласка, своє ім'я та прізвище"
    )

    return NAME


# ============================================================
# GET NAME
# ============================================================

async def get_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data["full_name"] = update.message.text

    keyboard = [
        [
            InlineKeyboardButton(
                "вперше",
                callback_data="first"
            )
        ],
        [
            InlineKeyboardButton(
                "вже була на консультації",
                callback_data="returning"
            )
        ],
    ]

    await update.message.reply_text(
        "записуєшся вперше чи вже працювала зі мною? 🤔",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return FIRST_TIME


# ============================================================
# FIRST TIME / RETURNING
# ============================================================

async def first_time_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    context.user_data["first_time"] = (
        "Вперше"
        if query.data == "first"
        else "Вже була"
    )

    await query.edit_message_text(
        f"Обрано: {context.user_data['first_time']}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "так, мій запит пасує",
                callback_data="fits"
            )
        ],
        [
            InlineKeyboardButton(
                "ні, не пасує(",
                callback_data="not_fits"
            )
        ],
        [
            InlineKeyboardButton(
                "хочу уточнити",
                callback_data="clarify"
            )
        ],
    ]

    await query.message.reply_text(
        SCOPE_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return SCOPE_CHECK


# ============================================================
# SCOPE CHECK
# ============================================================

async def scope_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    # --------------------------------------------------------
    # NOT FIT
    # --------------------------------------------------------

    if query.data == "not_fits":

        await query.edit_message_text(
            "дякую за чесність 🤍\n\n"
            "якщо запит не в моїй компетенції, "
            "краще звернутись до профільного спеціаліста.\n\n"
            "якщо захочеш — можеш написати мені напряму, "
            "підкажу, до кого."
        )

        return ConversationHandler.END

    # --------------------------------------------------------
    # CLARIFICATION
    # --------------------------------------------------------

    if query.data == "clarify":

        await query.edit_message_text(
            "звісно! напиши в кількох словах свій запит, "
            "і я скажу, чи можу допомогти."
        )

        context.user_data["needs_clarification"] = True

        return DESCRIBING

    # --------------------------------------------------------
    # FITS
    # --------------------------------------------------------

    await query.edit_message_text(
        "так, мій запит пасує"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "ознайомча зустріч (30 хв / 500 ₴)",
                callback_data="intro"
            )
        ],
        [
            InlineKeyboardButton(
                "повна консультація (50 хв / 1000 ₴)",
                callback_data="full"
            )
        ],
    ]

    await query.message.reply_text(
        FORMATS_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return FORMAT_CHOICE


# ============================================================
# FORMAT
# ============================================================

async def format_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    if query.data == "intro":
        context.user_data["format"] = (
            "Ознайомча зустріч (30 хв / 500 ₴)"
        )
    else:
        context.user_data["format"] = (
            "Повна консультація (50 хв / 1000 ₴)"
        )

    await query.edit_message_text(
        f"Обрано: {context.user_data['format']}"
    )

    await query.message.reply_text(
        POLICY_TEXT
    )

    return DESCRIBING


# ============================================================
# GET REQUEST
# ============================================================

async def get_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data["request_text"] = update.message.text

    if context.user_data.get("needs_clarification"):

        await update.message.reply_text(
            "дякую! я особисто гляну на твій запит "
            "і напишу, чи можу допомогти та які формати доступні.\n\n"
            "залиш, будь ласка, контакт для зв'язку "
            "(нік у Telegram або номер телефону)."
        )

    else:

        await update.message.reply_text(
            "дякую! тепер залиш, будь ласка, "
            "зручний спосіб зв'язку "
            "(нік у Telegram або номер телефону), "
            "щоб надіслати реквізити та узгодити час."
        )

    return CONTACT


# ============================================================
# GET CONTACT
# ============================================================

async def get_contact(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data["contact"] = update.message.text

    # --------------------------------------------------------
    # CLARIFICATION FLOW
    # --------------------------------------------------------

    if context.user_data.get("needs_clarification"):

        await finalize_request(
            update,
            context,
            paid=False
        )

        return ConversationHandler.END

    # --------------------------------------------------------
    # PAYMENT FLOW
    # --------------------------------------------------------

    keyboard = [
        [
            InlineKeyboardButton(
                "я оплатив(-ла) ✅",
                callback_data="paid"
            )
        ]
    ]

    await update.message.reply_text(
        "дякую! для підтвердження запису — "
        "оплата 100% на картку:\n\n"

        f"💳 {CARD_NUMBER}\n"
        f"👤 {CARD_HOLDER}\n\n"

        "після оплати натисни кнопку нижче — "
        "і я підтверджу час консультації.",

        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return PAYMENT


# ============================================================
# PAYMENT CONFIRMATION
# ============================================================

async def payment_confirmed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    await query.answer()

    await query.edit_message_text(
        "дякую, оплату очікую на підтвердження ✅"
    )

    await finalize_request(
        update,
        context,
        paid=True
    )

    return ConversationHandler.END


# ============================================================
# FINALIZE REQUEST
# ============================================================

async def finalize_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    paid: bool
):
    user = update.effective_user

    # Convert Railway environment variable to integer
    owner_chat_id = int(OWNER_CHAT_ID)

    # --------------------------------------------------------
    # BUILD APPLICATION SUMMARY
    # --------------------------------------------------------

    summary = (
        "🆕 Нова заявка з бота\n\n"

        f"Ім'я: "
        f"{context.user_data.get('full_name', '—')}\n"

        f"Статус: "
        f"{context.user_data.get('first_time', '—')}\n"

        f"Формат: "
        f"{context.user_data.get('format', 'потребує уточнення')}\n"

        f"Запит: "
        f"{context.user_data.get('request_text', '—')}\n"

        f"Контакт: "
        f"{context.user_data.get('contact', '—')}\n"

        f"Оплата: "
        f"{'позначено як оплачено ✅ (звір надходження на карту)' if paid else 'без оплати — потребує уточнення формату'}\n"

        f"Telegram: "
        f"@{user.username or 'без username'} "
        f"(id: {user.id})"
    )

    # --------------------------------------------------------
    # SEND APPLICATION TO OWNER
    # --------------------------------------------------------

    try:

        logger.info(
            f"📨 Sending application to "
            f"OWNER_CHAT_ID={owner_chat_id}"
        )

        await context.bot.send_message(
            chat_id=owner_chat_id,
            text=summary,
        )

        logger.info(
            f"✅ Application successfully sent to "
            f"OWNER_CHAT_ID={owner_chat_id}"
        )

    except Exception:

        logger.exception(
            f"❌ FAILED to send application to "
            f"OWNER_CHAT_ID={owner_chat_id}"
        )

    # --------------------------------------------------------
    # SEND CONFIRMATION TO USER
    # --------------------------------------------------------

    if paid:

        reply_text = (
            "дякую! як тільки надходження на карту "
            "підтвердиться, я напишу з підтвердженням "
            "часу та посиланням на Google Meet 🤍"
        )

    else:

        reply_text = (
            "дякую! я особисто передивлюся твій запит "
            "та напишу щодо можливості консультації "
            "протягом дня 🤍"
        )

    # For normal messages, update.message exists.
    # For callback buttons, update.callback_query.message exists.
    target = (
        update.message
        if update.message
        else update.callback_query.message
    )

    await target.reply_text(reply_text)


# ============================================================
# CANCEL
# ============================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "добре, скасовано. "
        "напиши /start, щоб почати знову."
    )

    return ConversationHandler.END


# ============================================================
# MAIN
# ============================================================

def main():

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    conv = ConversationHandler(

        entry_points=[
            CommandHandler(
                "start",
                start
            )
        ],

        states={

            NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_name
                )
            ],

            FIRST_TIME: [
                CallbackQueryHandler(
                    first_time_choice
                )
            ],

            SCOPE_CHECK: [
                CallbackQueryHandler(
                    scope_choice
                )
            ],

            FORMAT_CHOICE: [
                CallbackQueryHandler(
                    format_choice
                )
            ],

            DESCRIBING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_request
                )
            ],

            CONTACT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_contact
                )
            ],

            PAYMENT: [
                CallbackQueryHandler(
                    payment_confirmed
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel
            )
        ],
    )

    app.add_handler(conv)

    logger.info("🚀 Bot starting...")

    app.run_polling()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()