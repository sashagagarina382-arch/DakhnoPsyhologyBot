"""
Telegram-бот для запису на консультації — Олександра Дахно, психологиня
(підлітки та батьки).

Флоу:
/start
 -> ім'я та прізвище
 -> вперше чи вже була на консультації
 -> перевірка запиту (з чим працюю / не працюю) -> так / ні / уточнити
 -> якщо "так": вибір формату (ознайомча / повна)
 -> політика оплати та скасування
 -> запит опис + контакт
 -> заявка йде тобі в Telegram, користувачу — підтвердження
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- НАЛАШТУВАННЯ (через змінні середовища) ----
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_CHAT_ID = os.environ["OWNER_CHAT_ID"]

# ---- РЕКВІЗИТИ ДЛЯ ОПЛАТИ (через змінні середовища) ----
CARD_NUMBER = os.environ["CARD_NUMBER"]
CARD_HOLDER = os.environ["CARD_HOLDER"]

# ---- ТЕКСТИ (редагуй вільно під себе) ----
SCOPE_TEXT = (
    "перевір, будь ласка, чи я працюю з твоїм запитом:\n\n"
    "🟢 *З ЧИМ Я ПРАЦЮЮ*\n"
    "• шкільна тривожність\n"
    "• булінг та конфлікти з однолітками\n"
    "• самооцінка та впевненість\n"
    "• ресурсний стан, виснаження\n"
    "• профорієнтація\n"
    "• стосунки з батьками (для підлітків)\n"
    "• як говорити з підлітком (для батьків)\n"
    "• адаптація / переїзд\n\n"
    "🔴 *З ЧИМ НЕ ПРАЦЮЮ*\n"
    "• клінічні розлади (психотичні стани, депресія, ПТСР)\n"
    "• суїцидальні думки, самопошкодження\n"
    "• розлади харчової поведінки\n"
    "• залежності\n"
    "• глибока травма\n"
    "• випадки насильства в сім'ї\n\n"
    "_якщо запит не пасує — можу порадити, до кого звернутись_"
)

FORMATS_TEXT = (
    "чудово! обери формат роботи 🤍\n\n"
    "*ознайомча зустріч* (30 хв / 500 ₴)\n"
    "знайомство, формування запиту, узгодження подальшої роботи\n\n"
    "*повна консультація* (50 хв / 1000 ₴)\n"
    "повноцінна сесія по твоєму запиту"
)

POLICY_TEXT = (
    "окей!\n\n"
    "оплата 100% вартості — перед консультацією, запис підтверджується "
    "лише після оплати ✍️\n\n"
    "скасування/перенесення можливе не пізніше ніж за 24 години до зустрічі, "
    "інакше консультація вважається проведеною.\n\n"
    "консультації проходять онлайн (Google Meet), посилання надсилаю "
    "після підтвердження оплати.\n\n"
    "тепер коротко напиши, з яким запитом звертаєшся 🤍"
)

NAME, FIRST_TIME, SCOPE_CHECK, FORMAT_CHOICE, POLICY_ACK, DESCRIBING, CONTACT, PAYMENT = range(8)


# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(
#         "вітаю у боті «Ваш психолог Саша✨» 🤍\n\nвкажи, будь ласка, своє ім'я та прізвище"
#     )
#     return NAME

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

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


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text
    keyboard = [
        [InlineKeyboardButton("вперше", callback_data="first")],
        [InlineKeyboardButton("вже була на консультації", callback_data="returning")],
    ]
    await update.message.reply_text(
        "записуєшся вперше чи вже працювала зі мною? 🤔",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FIRST_TIME


async def first_time_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["first_time"] = "Вперше" if query.data == "first" else "Вже була"
    await query.edit_message_text(f"Обрано: {context.user_data['first_time']}")

    keyboard = [
        [InlineKeyboardButton("так, мій запит пасує", callback_data="fits")],
        [InlineKeyboardButton("ні, не пасує(", callback_data="not_fits")],
        [InlineKeyboardButton("хочу уточнити", callback_data="clarify")],
    ]
    await query.message.reply_text(
        SCOPE_TEXT, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SCOPE_CHECK


async def scope_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "not_fits":
        await query.edit_message_text(
            "дякую за чесність 🤍 якщо запит не в моїй компетенції, "
            "краще звернутись до профільного спеціаліста. "
            "якщо захочеш — можеш написати мені напряму, підкажу, до кого."
        )
        return ConversationHandler.END

    if query.data == "clarify":
        await query.edit_message_text(
            "звісно! напиши в кількох словах свій запит, і я скажу, чи можу допомогти."
        )
        context.user_data["needs_clarification"] = True
        return DESCRIBING

    await query.edit_message_text("так, мій запит пасує")
    keyboard = [
        [InlineKeyboardButton("ознайомча зустріч (30 хв / 500 ₴)", callback_data="intro")],
        [InlineKeyboardButton("повна консультація (50 хв / 1000 ₴)", callback_data="full")],
    ]
    await query.message.reply_text(
        FORMATS_TEXT, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return FORMAT_CHOICE


async def format_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["format"] = (
        "Ознайомча зустріч (30 хв / 500 ₴)" if query.data == "intro"
        else "Повна консультація (50 хв / 1000 ₴)"
    )
    await query.edit_message_text(f"Обрано: {context.user_data['format']}")
    await query.message.reply_text(POLICY_TEXT, parse_mode="Markdown")
    return DESCRIBING


async def get_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["request_text"] = update.message.text

    if context.user_data.get("needs_clarification"):
        await update.message.reply_text(
            "дякую! я особисто гляну на твій запит і напишу, чи можу допомогти "
            "та які формати доступні. залиш, будь ласка, контакт для зв'язку "
            "(нік у Telegram або номер телефону)."
        )
    else:
        await update.message.reply_text(
            "дякую! тепер залиш, будь ласка, зручний спосіб зв'язку "
            "(нік у Telegram або номер телефону), щоб надіслати реквізити та узгодити час."
        )
    return CONTACT


async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text

    if context.user_data.get("needs_clarification"):
        # без обраного формату — реквізити не показуємо, спершу уточнення від Олександри
        await finalize_request(update, context, paid=False)
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("я оплатив(-ла) ✅", callback_data="paid")]]
    await update.message.reply_text(
        "дякую! для підтвердження запису — оплата 100% на картку:\n\n"
        f"💳 `{CARD_NUMBER}`\n"
        f"👤 {CARD_HOLDER}\n\n"
        "після оплати натисни кнопку нижче — і я підтверджу час консультації.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PAYMENT


async def payment_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("дякую, оплату очікую на підтвердження ✅")
    await finalize_request(update, context, paid=True)
    return ConversationHandler.END


async def finalize_request(update: Update, context: ContextTypes.DEFAULT_TYPE, paid: bool):
    user = update.effective_user
    # без Markdown: запит користувача може містити символи (* _ `), які ламають
    # парсинг Telegram і тихо блокують надсилання цього повідомлення
    summary = (
        "🆕 Нова заявка з бота\n\n"
        f"Ім'я: {context.user_data.get('full_name', '—')}\n"
        f"Статус: {context.user_data.get('first_time', '—')}\n"
        f"Формат: {context.user_data.get('format', 'потребує уточнення')}\n"
        f"Запит: {context.user_data.get('request_text', '—')}\n"
        f"Контакт: {context.user_data.get('contact', '—')}\n"
        f"Оплата: {'позначено як оплачено (звір надходження на карту)' if paid else 'без оплати — потребує уточнення формату'}\n"
        f"Telegram: @{user.username or 'без username'} (id: {user.id})"
    )
    try:
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=summary)
    except Exception:
        logger.exception("Не вдалося надіслати заявку власнику (перевір OWNER_CHAT_ID)")

    reply_text = (
        "дякую! як тільки надходження на карту підтвердиться, я напишу "
        "з підтвердженням часу та посиланням на Google Meet 🤍"
        if paid else
        "дякую! я особисто передзвонюсь щодо твого запиту протягом дня 🤍"
    )
    target = update.message or update.callback_query.message
    await target.reply_text(reply_text)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("добре, скасовано. напиши /start, щоб почати знову.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FIRST_TIME: [CallbackQueryHandler(first_time_choice)],
            SCOPE_CHECK: [CallbackQueryHandler(scope_choice)],
            FORMAT_CHOICE: [CallbackQueryHandler(format_choice)],
            DESCRIBING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_request)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
            PAYMENT: [CallbackQueryHandler(payment_confirmed)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()
