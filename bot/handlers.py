import logging
from subprocess import check_call
from tabnanny import check

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from win32pdh import counter_status_error

from bot.gmail import fetch_unread_emails, fetch_email_details, get_service
from bot.db import get_user_accounts, save_credentials, get_credentials, save_user_filters, get_user_filters
from bot.oauth import create_flow, get_auth_url, build_credentials_from_dict
from bot.utils import escape_markdown_except_links, replace_urls_with_links, split_markdown_message, matches_filter

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start и инициирует процесс авторизации."""
    user_id = update.effective_user.id
    logger.info(f"Получена команда /start от пользователя {user_id}")

    accounts = get_user_accounts(user_id)
    if accounts:
        await update.message.reply_text(
            "Вы уже авторизованы. Используйте /get_emails для получения писем."
        )
        logger.info(f"Пользователь {user_id} уже авторизован.")
    else:
        flow = create_flow(user_id)
        auth_url, state = get_auth_url(flow)
        await update.message.reply_text(
            f"Пожалуйста, авторизуйтесь через Gmail, перейдя по [ссылке]({auth_url}).",
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )
        logger.info(f"Пользователю {user_id} отправлена ссылка для авторизации.")


async def get_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /get_emails и предлагает выбрать аккаунт."""
    user_id = update.effective_user.id
    logger.info(f"Получена команда /get_emails от пользователя {user_id}")

    accounts = get_user_accounts(user_id)
    if not accounts:
        await update.message.reply_text("У вас нет привязанных почтовых ящиков. Используйте /start для авторизации.")
        logger.warning(f"Пользователь {user_id} попытался получить письма без привязанных аккаунтов.")
        return

    if len(accounts) == 1:
        await fetch_and_send_emails(update, context, user_id, accounts[0])
    else:
        keyboard = [[InlineKeyboardButton(f"Аккаунт {i + 1}", callback_data=acc)] for i, acc in enumerate(accounts)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите почтовый ящик:', reply_markup=reply_markup)
        logger.info(f"Пользователю {user_id} предложено выбрать аккаунт из {len(accounts)} доступных.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор аккаунта из списка."""
    query = update.callback_query
    await query.answer()
    account_id = query.data
    user_id = query.from_user.id

    logger.info(f"Пользователь {user_id} выбрал аккаунт {account_id}")

    await fetch_and_send_emails(query, context, user_id, account_id)


async def fetch_and_send_emails(update, context, user_id, account_id):
    logger.info(f"Начало получения писем для пользователя {user_id} и аккаунта {account_id}")

    credentials_dict = get_credentials(user_id, account_id)
    if not credentials_dict:
        await update.message.reply_text("Токены не найдены. Пожалуйста, авторизуйтесь заново с /start.")
        logger.error(f"Токены для пользователя {user_id} и аккаунта {account_id} не найдены.")
        return

    try:
        credentials = build_credentials_from_dict(credentials_dict)
        service = get_service(credentials)

        messages = fetch_unread_emails(service, max_results=1)
        if not messages:
            await update.message.reply_text("Нет новых сообщений.")
            logger.info(f"Для пользователя {user_id} и аккаунта {account_id} новых сообщений нет.")
            return

        user_filters = get_user_filters(user_id)
        counter_important_msg = 0
        for msg in messages:
            details = fetch_email_details(service, msg['id'])
            if details:
                email_body = details['body']
                email_subject = details['subject']

                # Проверка на соответствие фильтрам
                if matches_filter(email_body, email_subject, user_filters):
                    counter_important_msg += 1
                    await update.message.reply_text(
                        f"⚠️ Важное письмо! Оно соответствует вашим выставленным фильтрам: {user_filters}\n"
                    )
                    logger.info(f"Важное письмо найдено для пользователя {user_id}: {email_subject}")
                    # Отправляем письмо пользователю
                    safe_body = escape_markdown_except_links(replace_urls_with_links(email_body))
                    message_text = (
                        f"*От кого:* {escape_markdown_except_links(details['from'])}\n"
                        f"*Тема:* {escape_markdown_except_links(email_subject)}\n"
                        f"*Текст:* {safe_body}"
                    )
                    message_parts = split_markdown_message(message_text)
                    for part in message_parts:
                        await update.message.reply_text(part, parse_mode='MarkdownV2', disable_web_page_preview=True)

                # Помечаем письмо как прочитанное
                service.users().messages().modify(
                    userId='me',
                    id=msg['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                logger.info(f"Письмо {msg['id']} для пользователя {user_id} помечено как прочитанное.")

        message_text = (f"Найдено важных сообщений: {counter_important_msg}")
        await update.message.reply_text(message_text, parse_mode='MarkdownV2', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Ошибка при обработке писем для пользователя {user_id}: {e}")
        await update.message.reply_text("Произошла ошибка при получении писем. Пожалуйста, попробуйте позже.")


async def set_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /set_filters и позволяет пользователю установить список ключевых фраз."""
    user_id = update.effective_user.id
    logger.info(f"Получена команда /set_filters от пользователя {user_id}")

    if not context.args:
        await update.message.reply_text("Пожалуйста, введите ключевые фразы через запятую после команды /set_filters.")
        logger.warning(f"Пользователь {user_id} не указал ключевые фразы для фильтров.")
        return

    # Разбиваем аргументы по запятой и удаляем лишние пробелы
    filters = [phrase.strip() for phrase in " ".join(context.args).split(",")]
    save_user_filters(user_id, filters)
    await update.message.reply_text(f"Ключевые фразы успешно сохранены: {', '.join(filters)}")
    logger.info(f"Ключевые фразы для пользователя {user_id} сохранены: {filters}")


async def get_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /get_filters и отправляет пользователю текущие ключевые фразы."""
    user_id = update.effective_user.id
    logger.info(f"Получена команда /get_filters от пользователя {user_id}")

    filters = get_user_filters(user_id)

    if not filters:
        await update.message.reply_text(
            "У вас нет сохраненных ключевых фраз. Используйте /set_filters для их добавления."
        )
        logger.info(f"Для пользователя {user_id} фильтры не найдены.")
    else:
        await update.message.reply_text(f"Ваши текущие ключевые фразы: {', '.join(filters)}")
        logger.info(f"Пользователю {user_id} отправлены его фильтры: {filters}")
