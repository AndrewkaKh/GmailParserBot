from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from bot.gmail import fetch_unread_emails, fetch_email_details, get_service
from bot.db import get_user_accounts, save_credentials, get_credentials
from bot.oauth import create_flow, get_auth_url, build_credentials_from_dict
from bot.utils import escape_markdown_except_links, replace_urls_with_links, split_markdown_message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start и инициирует процесс авторизации."""
    user_id = update.effective_user.id
    accounts = get_user_accounts(user_id)
    if accounts:
        await update.message.reply_text(
            "Вы уже авторизованы. Используйте /get_emails для получения писем."
        )
    else:
        flow = create_flow(user_id)
        auth_url, state = get_auth_url(flow)
        await update.message.reply_text(
            f"Пожалуйста, авторизуйтесь через Gmail, перейдя по [ссылке]({auth_url}).",
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )

async def get_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /get_emails и предлагает выбрать аккаунт."""
    user_id = update.effective_user.id
    accounts = get_user_accounts(user_id)
    if not accounts:
        await update.message.reply_text("У вас нет привязанных почтовых ящиков. Используйте /start для авторизации.")
        return

    if len(accounts) == 1:
        await fetch_and_send_emails(update, context, user_id, accounts[0])
    else:
        keyboard = [[InlineKeyboardButton(f"Аккаунт {i + 1}", callback_data=acc)] for i, acc in enumerate(accounts)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите почтовый ящик:', reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор аккаунта из списка."""
    query = update.callback_query
    await query.answer()
    account_id = query.data
    user_id = query.from_user.id
    await fetch_and_send_emails(query, context, user_id, account_id)

async def fetch_and_send_emails(update, context, user_id, account_id):
    """Получает письма для выбранного аккаунта и отправляет их пользователю."""
    credentials_dict = get_credentials(user_id, account_id)
    if not credentials_dict:
        await update.message.reply_text("Токены не найдены. Пожалуйста, авторизуйтесь заново с /start.")
        return

    credentials = build_credentials_from_dict(credentials_dict)
    service = get_service(credentials)

    messages = fetch_unread_emails(service, max_results=1)
    if not messages:
        await update.message.reply_text("Нет новых сообщений.")
        return

    for msg in messages:
        details = fetch_email_details(service, msg['id'])
        if details:
            safe_body = escape_markdown_except_links(replace_urls_with_links(details['body']))
            message_text = (
                f"*От кого:*\n{escape_markdown_except_links(details['from'])}\n"
                f"*Тема:*\n{escape_markdown_except_links(details['subject'])}\n"
                f"*Текст:*\n{safe_body}"
            )
            message_parts = split_markdown_message(message_text)
            for part in message_parts:
                await update.message.reply_text(part, parse_mode='MarkdownV2', disable_web_page_preview=True)
