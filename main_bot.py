import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from bot.handlers import start, get_emails, button_handler, set_filters, get_filters, check_unread_emails
from bot.db import init_db
from config import TELEGRAM_BOT_TOKEN, TIMER_INTERVAL

TOKEN = TELEGRAM_BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def schedule_tasks(application):
    """Запускает периодические задачи."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: application.job_queue.run_once(check_unread_emails, 0),
        trigger=IntervalTrigger(seconds=TIMER_INTERVAL),
        name="check_unread_emails",
        replace_existing=True
    )
    scheduler.start()

def main():
    """Главная точка входа в приложение."""
    # Инициализация базы данных
    init_db()

    if not TOKEN:
        logger.error("Не найден токен бота. Установите переменную окружения или обновите main_bot.py.")
        return

    # Создание приложения Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('get_emails', get_emails))
    application.add_handler(CommandHandler('set_filters', set_filters))
    application.add_handler(CommandHandler('get_filters', get_filters))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запуск планировщика задач
    schedule_tasks(application)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
