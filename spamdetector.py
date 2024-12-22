import openai
from openai import OpenAI


def analyze_email_with_keywords(email_body, keywords, api_key_file):
    def get_file_contents(filename):
        try:
            with open(filename, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"'{filename}' file not found")

    # Получение API-ключа
    openai_api_key = get_file_contents(api_key_file)

    # Инициализация клиента OpenAI
    client = OpenAI(api_key=openai_api_key)

    # Формирование промпта
    prompt = (
        f"Есть текст email-письма: {email_body}. Напиши 1, если текст этого письма имеет смысловое семантическое тематическое и "
        f"контекстуальное отношение к этому списку тем: {keywords}, и 0, "
        "если не имеет. Важно, проанализируй смысл письма и учитывай, что он должен иметь отношение ко всем темам из "
        "списка. "
    )

    # Обращение к API GPT для получения ответа
    output = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
    )

    # Возврат результата
    return output.choices[0].message.content.strip()


# filename = 'openai_api_key'
#
# email_body = '"Короче хочу сходить на Черную пятницу залутаться, потом телок тусануть и пивандопалу попить, ' \
#              'ты с нами броски-плутоски?"'
# keywords = ['черная пятница', 'туса']
#
# try:
#     result = analyze_email_with_keywords(email_body, keywords, filename)
#     print(result)
# except Exception as e:
#     print(f"Ошибка: {e}")
