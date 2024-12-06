import base64
import json
import logging
import os
import pickle
import re
import sqlite3
import textwrap
from urllib.parse import urljoin

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import Flow
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telegram.helpers import escape_markdown

# Модель машинного обучения для предсказания спам/не спам
with open('spamclassifiermodel/model.pkl', 'rb') as f:
    vectorizer, spam_predictor = pickle.load(f)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CLIENT_SECRETS_FILE = 'client_secret4.json'
DB_FILE = 'users.db'
MAX_MESSAGE_LENGTH = 4000
NGROK_URL = 'https://bc54-5-34-215-156.ngrok-free.app'  # Замените на ваш актуальный ngrok URL
TOKEN = "8010623899:AAE4KcSI5rvWzUri0ODzT6TENQiNgdnHLNc"  # Замените на ваш токен


# Функции для работы с базой данных
def save_credentials(user_id, account_id, credentials):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users_accounts (user_id, account_id, credentials)
        VALUES (?, ?, ?)
    ''', (user_id, account_id, json.dumps(credentials)))
    conn.commit()
    conn.close()


def get_credentials(user_id, account_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT credentials FROM users_accounts
        WHERE user_id = ? AND account_id = ?
    ''', (user_id, account_id))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def get_user_accounts(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT account_id FROM users_accounts
        WHERE user_id = ?
    ''', (user_id,))
    accounts = cursor.fetchall()
    conn.close()
    return [acc[0] for acc in accounts]


def escape_markdown_except_links(text):
    """
    Экранирует специальные символы MarkdownV2 в тексте, за исключением Markdown-ссылок.

    :param text: Текст с заменёнными ссылками
    :return: Текст с экранированными символами, кроме ссылок
    """
    # Регулярное выражение для поиска Markdown-ссылок [ссылка](URL)
    link_pattern = re.compile(r'\[ссылка\]\(.*?\)')

    # Найти все ссылки
    links = link_pattern.findall(text)

    # Разделить текст на части, исключая ссылки
    parts = link_pattern.split(text)

    # Экранировать каждую часть, не являющуюся ссылкой
    escaped_parts = [escape_markdown(part, version=2) for part in parts]

    # Воссоздать текст, вставляя неэкранированные ссылки
    new_text = ''.join([part + link for part, link in zip(escaped_parts, links + [''])])

    return new_text


def replace_urls_with_links(text):
    """
    Заменяет все URL в тексте на Markdown-ссылки с текстом 'ссылка'.
    """
    url_pattern = re.compile(
        r'(?i)\b((?:https?://|www\d{0,3}[.]|'
        r'[a-z0-9.\-]+[.][a-z]{2,4}/)'
        r'(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'
        r'(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|'
        r'[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'
    )

    def replacer(match):
        url = match.group(0)
        if not re.match(r'https?://', url):
            url = 'http://' + url
        return f"[ссылка]({url})"

    return url_pattern.sub(replacer, text)


def split_markdown_message(text, max_length=4096):
    """
    Разбивает MarkdownV2 сообщение на части, не нарушая синтаксис MarkdownV2.
    Предпочтительно разбивать по строкам.

    :param text: Обработанный текст сообщения
    :param max_length: Максимальная длина одной части сообщения
    :return: Список частей сообщения
    """
    lines = text.split('\n')
    parts = []
    current_part = ''

    for line in lines:
        # Проверяем, не превышает ли добавление строки лимит
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part)
                current_part = ''
        # Если строка сама по себе длиннее max_length, разбиваем её
        if len(line) > max_length:
            split_lines = textwrap.wrap(line, width=max_length, break_long_words=False, replace_whitespace=False)
            for split_line in split_lines:
                parts.append(split_line)
        else:
            if current_part:
                current_part += '\n' + line
            else:
                current_part = line
    if current_part:
        parts.append(current_part)
    return parts


def get_message_body(message):
    """
    Извлекает текст из тела письма.

    :param message: Сообщение Gmail API
    :return: Текст письма или None
    """
    try:
        payload = message.get('payload', {})
        parts = payload.get('parts', [])
        if not parts:
            # Если сообщение не имеет частей, берём тело напрямую
            body_data = payload.get('body', {}).get('data', '')
            return decode_base64(body_data)

        # Проходим по всем частям и ищем 'text/plain'
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                return decode_base64(body_data)
            elif part.get('mimeType').startswith('multipart/'):
                # Рекурсивно обрабатываем вложенные части
                sub_body = get_message_body(part)
                if sub_body:
                    return sub_body
        return None
    except Exception as e:
        logger.error(f"Ошибка при извлечении тела письма: {e}")
        return None


def decode_base64(data):
    """
    Декодирует base64url строку.

    :param data: Строка в формате base64url
    :return: Декодированная строка или сообщение об ошибке
    """
    try:
        decoded_bytes = base64.urlsafe_b64decode(data + '==')  # Добавляем '==' для выравнивания
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка при декодировании данных: {e}")
        return "Не удалось декодировать текст письма."


async def send_processed_email(update: Update, context: ContextTypes.DEFAULT_TYPE, from_, subject, body: str):
    """
    Обрабатывает тело письма и отправляет его пользователю в Telegram.

    :param update: Объект Update из telegram.ext
    :param context: Контекст из telegram.ext
    :param from_: От кого письмо
    :param subject: Тема письма
    :param body: Текст письма
    """
    try:
        # Шаг 1: Замена URL на Markdown-ссылки
        body_with_links = replace_urls_with_links(body)

        # Шаг 2: Экранирование специальных символов MarkdownV2, исключая ссылки
        safe_body = escape_markdown_except_links(body_with_links)

        # Шаг 3: Формирование полного текста сообщения
        message_text = (
            f"*От кого:*\n{escape_markdown(from_, version=2)}\n"
            f"*Тема:*\n{escape_markdown(subject, version=2)}\n"
            f"*Текст:*\n{safe_body}"
        )

        # Шаг 4: Разбиение сообщения на части, если оно слишком длинное
        if len(message_text) > 4096:
            message_parts = split_markdown_message(message_text, max_length=4096)
        else:
            message_parts = [message_text]

        # Шаг 5: Отправка сообщений пользователю
        for part in message_parts:
            await update.message.reply_text(
                part,
                parse_mode='MarkdownV2',
                disable_web_page_preview=True  # Отключает предварительный просмотр ссылок
            )

    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        await update.message.reply_text("Произошла ошибка при отправке сообщения.")


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    accounts = get_user_accounts(user_id)
    if accounts:
        await update.message.reply_text(
            "Вы уже авторизованы. Используйте /get_emails для получения писем."
        )
    else:
        # Начало OAuth2 процесса
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=urljoin(NGROK_URL, '/oauth2callback')
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=str(user_id)  # Используем user_id как state
        )
        logger.info(f"Authorization URL для пользователя {user_id}: {auth_url}")
        # Отправка ссылки пользователю
        await update.message.reply_text(
            f"Пожалуйста, авторизуйтесь через Gmail, перейдя по [ссылке]({auth_url}).",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )


# Команда /get_emails
async def get_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    accounts = get_user_accounts(user_id)

    if not accounts:
        await update.message.reply_text("У вас нет привязанных почтовых ящиков. Используйте /start для авторизации.")
        return

    if len(accounts) == 1:
        account_id = accounts[0]
        await fetch_and_send_emails(update, context, user_id, account_id)
    else:
        # Предложить выбрать аккаунт
        keyboard = [
            [InlineKeyboardButton(f"Аккаунт {i + 1}", callback_data=acc)] for i, acc in enumerate(accounts)
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите почтовый ящик:', reply_markup=reply_markup)


# Обработчик нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account_id = query.data
    user_id = query.from_user.id
    await fetch_and_send_emails(query, context, user_id, account_id)


# Функция для получения и отправки писем
async def fetch_and_send_emails(update, context, user_id, account_id):
    credentials_dict = get_credentials(user_id, account_id)
    if not credentials_dict:
        await update.message.reply_text("Токены не найдены. Пожалуйста, авторизуйтесь заново с /start.")
        return

    try:
        credentials = Credentials(
            token=credentials_dict['token'],
            refresh_token=credentials_dict['refresh_token'],
            token_uri=credentials_dict['token_uri'],
            client_id=credentials_dict['client_id'],
            client_secret=credentials_dict['client_secret'],
            scopes=credentials_dict['scopes']
        )
    except KeyError as e:
        logger.error(f"Отсутствует необходимое поле в учётных данных: {e}")
        await update.message.reply_text("Некорректные учётные данные. Пожалуйста, авторизуйтесь заново с /start.")
        return

    # Проверка и обновление токенов
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            # Сохранение обновленных токенов
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            save_credentials(user_id, account_id, credentials)
        except Exception as e:
            logger.error(f"Ошибка обновления токена: {e}")
            await update.message.reply_text("Не удалось обновить токен. Пожалуйста, авторизуйтесь заново с /start.")
            return

    try:
        service = build('gmail', 'v1', credentials=credentials)

        # Получение только непрочитанных сообщений
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=1).execute()
        messages = results.get('messages', [])

        if not messages:
            await update.message.reply_text("Нет новых сообщений.")
            return

        for msg in messages:
            message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = message.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Без темы')
            from_ = next((h['value'] for h in headers if h['name'] == 'From'), 'Неизвестно')

            # Извлечение тела письма
            body = get_message_body(message)
            if body:
                cur_email = vectorizer.transform([body])
                cur_predict = spam_predictor.predict(cur_email)
                logger.info("Текст письма получен")
                await send_processed_email(update, context, from_, subject, body)
                await update.message.reply_text(f"Текст письма получен. Результат модельки: {cur_predict}")
            else:
                await update.message.reply_text(
                    f"*От кого:*\n{escape_markdown(from_, version=2)}\n"
                    f"*Тема:*\n{escape_markdown(subject, version=2)}\n"
                    f"*Текст:*\nНе удалось извлечь текст письма.",
                    parse_mode='MarkdownV2'
                )

            # Пометка письма как прочитанного
            # service.users().messages().modify(
            #     userId='me',
            #     id=msg['id'],
            #     body={'removeLabelIds': ['UNREAD']}
            # ).execute()

    except Exception as e:
        logger.error(f"Ошибка при получении писем: {e}")
        await update.message.reply_text("Произошла ошибка при получении писем.")


def main():
    # Инициализация базы данных
    def init_db():
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_accounts (
                user_id INTEGER,
                account_id TEXT,
                credentials TEXT,
                PRIMARY KEY (user_id, account_id)
            )
        ''')
        conn.commit()
        conn.close()

    init_db()

    if not TOKEN:
        logger.error("Не найден токен бота. Установите переменную окружения TELEGRAM_BOT_TOKEN.")
        return

    # Создание приложения
    application = ApplicationBuilder().token(TOKEN).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('get_emails', get_emails))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запуск Telegram бота
    application.run_polling()


if __name__ == '__main__':
    main()
