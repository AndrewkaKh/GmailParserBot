# bot.py
import os
import pickle
import json
import logging
import sqlite3
from urllib.parse import urljoin

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import requests
import base64
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
CLIENT_SECRETS_FILE = 'client_secret3.json'
DB_FILE = 'users.db'

# Публичный URL вашего Flask-сервера через ngrok
NGROK_URL = 'https://da59-5-34-215-156.ngrok-free.app'  # Замените на ваш актуальный ngrok URL

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
            [InlineKeyboardButton(f"Аккаунт {i+1}", callback_data=acc)] for i, acc in enumerate(accounts)
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
            credentials.refresh(requests.Request())
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
                #Тело письма
                logger.info("текст письма получен")
                await update.message.reply_text("Текст письма получен.")
            else:
                await update.message.reply_text(
                    f"*От:* {escape_markdown(from_, version=2)}\n*Тема:* {escape_markdown(subject, version=2)}\n*Текст:*\nНе удалось извлечь текст письма.",
                    parse_mode='MarkdownV2')

            # Пометка письма как прочитанного
            """service.users().messages().modify(
                userId='me',
                id=msg['id'],
                body={'removeLabelIds': ['UNREAD']}
            ).execute()"""

    except Exception as e:
        logger.error(f"Ошибка при получении писем: {e}")
        await update.message.reply_text("Произошла ошибка при получении писем.")


def get_message_body(message):
    """
    Функция для извлечения текста письма из сообщения Gmail API.
    Обрабатывает все части сообщения рекурсивно.
    """
    try:
        parts = message['payload'].get('parts')
        if not parts:
            # Если сообщение не многокомпонентное
            body_data = message['payload']['body'].get('data', '')
            return decode_base64(body_data)

        # Ищем часть с MIME типом 'text/plain'
        for part in parts:
            if part['mimeType'] == 'text/plain':
                body_data = part['body'].get('data', '')
                return decode_base64(body_data)
            elif part['mimeType'].startswith('multipart/'):
                # Рекурсивный вызов для вложенных частей
                sub_body = get_message_body(part)
                if sub_body:
                    return sub_body
            elif part['mimeType'] == 'text/html':
                body_data = part['body'].get('data', '')
                return decode_base64(body_data)

        return "Текст письма не найден."
    except Exception as e:
        logger.error(f"Ошибка при извлечении тела письма: {e}")
        return None


def decode_base64(data):
    """
    Функция для декодирования base64url строки.
    """
    try:
        decoded_bytes = base64.urlsafe_b64decode(data + '==')
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка при декодировании данных: {e}")
        return "Не удалось декодировать текст письма."

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

    # Загрузка токена бота из переменной окружения

    filename = 'apikey'

    def get_file_contents(filename):
        """ Given a filename,
            return the contents of that file
        """
        try:
            with open(filename, 'r') as f:
                # It's assumed our file contains a single line,
                # with our API key
                return f.read().strip()
        except FileNotFoundError:
            print("'%s' file not found" % filename)

    TOKEN = get_file_contents(filename)

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
