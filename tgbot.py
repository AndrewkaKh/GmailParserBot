import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


class TelegramBot:
    def __init__(self, token: str):
        """
        Инициализация бота.
        :param token: Токен бота, полученный от BotFather.
        """
        self.bot = telebot.TeleBot(token)
        self.user_data = {}  # Словарь для хранения имен, почты и паролей пользователей
        self.user_states = {}  # Словарь для хранения состояний пользователей (например, ждём имя, почту или пароль)

    def create_main_menu(self):
        """
        Создает клавиатуру с основными кнопками.
        """
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        change_name_button = KeyboardButton("Сменить имя")
        change_email_button = KeyboardButton("Сменить почту")
        markup.add(change_name_button, change_email_button)
        return markup

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            """
            Обработчик команды /start.
            """
            user_id = message.from_user.id

            # Создаем клавиатуру с кнопкой "Начать"
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            start_button = KeyboardButton("Начать")
            markup.add(start_button)

            self.bot.send_message(
                user_id,
                "Добро пожаловать! Нажмите кнопку \"Начать\", чтобы продолжить.",
                reply_markup=markup
            )

        @self.bot.message_handler(func=lambda message: message.text == "Начать")
        def handle_start_button(message):
            """
            Обработчик нажатия на кнопку "Начать".
            """
            user_id = message.from_user.id
            if user_id not in self.user_data:
                self.user_states[user_id] = 'awaiting_name'
                self.bot.reply_to(
                    message,
                    "Привет! Как тебя зовут?"
                )
            else:
                self.bot.send_message(
                    user_id,
                    f"Привет снова, {self.user_data[user_id]['name']}! Как я могу тебе помочь?",
                    reply_markup=self.create_main_menu()
                )

        @self.bot.message_handler(func=lambda message: message.text == "Сменить имя")
        def handle_change_name_button(message):
            """
            Обработчик кнопки "Сменить имя".
            """
            user_id = message.from_user.id
            self.user_states[user_id] = 'changing_name'
            self.bot.reply_to(
                message,
                "Введите новое имя:"
            )

        @self.bot.message_handler(func=lambda message: message.text == "Сменить почту")
        def handle_change_email_button(message):
            """
            Обработчик кнопки "Сменить почту".
            """
            user_id = message.from_user.id
            self.user_states[user_id] = 'changing_email'
            self.bot.reply_to(
                message,
                "Введите новый адрес почты (например, example@gmail.com):"
            )

        @self.bot.message_handler(content_types=['text'])
        def handle_text_messages(message):
            """
            Обработчик текстовых сообщений.
            """
            user_id = message.from_user.id
            user_message = message.text.strip()

            # Если бот ждет имя пользователя
            if user_id in self.user_states and self.user_states[user_id] == 'awaiting_name':
                self.user_data[user_id] = {'name': user_message}  # Сохраняем имя пользователя
                self.user_states[user_id] = 'awaiting_email'  # Меняем состояние на ожидание почты
                self.bot.reply_to(
                    message,
                    f"Приятно познакомиться, {user_message}! Теперь введи свою почту (например, example@gmail.com)."
                )

            # Если бот ждет почту пользователя
            elif user_id in self.user_states and self.user_states[user_id] == 'awaiting_email':
                if '@gmail.com' in user_message:
                    self.user_data[user_id]['email'] = user_message  # Сохраняем почту пользователя
                    self.user_states[user_id] = 'awaiting_password'
                    self.bot.reply_to(
                        message,
                        f"Почта {user_message} сохранена. Теперь введите пароль для этой почты:"
                    )
                else:
                    self.bot.reply_to(
                        message,
                        "Почта введена некорректно! Пожалуйста, убедись, что она содержит '@gmail.com'. Попробуй еще раз."
                    )

            # Если бот ждет пароль пользователя
            elif user_id in self.user_states and self.user_states[user_id] == 'awaiting_password':
                self.user_data[user_id]['password'] = user_message  # Сохраняем пароль пользователя
                self.user_states.pop(user_id)  # Сбрасываем состояние
                self.bot.send_message(
                    user_id,
                    f"Ваши учетные данные сохранены! Почта: {self.user_data[user_id]['email']}, пароль сохранен.",
                    reply_markup=self.create_main_menu()
                )

            # Если пользователь меняет имя
            elif user_id in self.user_states and self.user_states[user_id] == 'changing_name':
                self.user_data[user_id]['name'] = user_message  # Обновляем имя пользователя
                self.user_states.pop(user_id)
                self.bot.send_message(
                    user_id,
                    f"Ваше имя успешно изменено на {user_message}!",
                    reply_markup=self.create_main_menu()
                )

            # Если пользователь меняет почту
            elif user_id in self.user_states and self.user_states[user_id] == 'changing_email':
                if '@gmail.com' in user_message:
                    self.user_data[user_id]['email'] = user_message  # Обновляем почту пользователя
                    self.user_states[user_id] = 'changing_email_password'
                    self.bot.reply_to(
                        message,
                        f"Почта {user_message} сохранена. Теперь введите пароль для этой почты:"
                    )
                else:
                    self.bot.reply_to(
                        message,
                        "Почта введена некорректно! Пожалуйста, убедитесь, что она содержит '@gmail.com'. Попробуйте еще раз."
                    )

            # Если бот ждет пароль для обновленной почты
            elif user_id in self.user_states and self.user_states[user_id] == 'changing_email_password':
                self.user_data[user_id]['password'] = user_message  # Обновляем пароль пользователя
                self.user_states.pop(user_id)  # Сбрасываем состояние
                self.bot.send_message(
                    user_id,
                    f"Ваши учетные данные обновлены! Почта: {self.user_data[user_id]['email']}, пароль сохранен.",
                    reply_markup=self.create_main_menu()
                )

            # Если пользователь уже зарегистрирован
            elif user_id in self.user_data:
                user_name = self.user_data[user_id]['name']
                self.bot.send_message(
                    user_id,
                    f"{user_name}, я получил ваше сообщение: \"{user_message}\"",
                    reply_markup=self.create_main_menu()
                )

            # Если пользователь не нажал "Начать", предлагаем начать сначала
            else:
                markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                start_button = KeyboardButton("Начать")
                markup.add(start_button)
                self.bot.send_message(
                    user_id,
                    "Для начала нажмите кнопку \"Начать\".",
                    reply_markup=markup
                )
            print(self.user_data)

    def run(self):
        """
        Запуск бота.
        """
        print("Бот запущен!")
        self.bot.infinity_polling()


if __name__ == "__main__":
    API_TOKEN = 'ваш_токен_бота'
    telegram_bot = TelegramBot(API_TOKEN)
    telegram_bot.setup_handlers()
    telegram_bot.run()
