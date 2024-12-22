import logging
from flask import Flask

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Создание и конфигурация Flask-приложения."""
    app = Flask(__name__)
    with app.app_context():
        # Инициализация базы данных или других компонентов, если требуется
        from .db import init_db
        init_db()
    return app
