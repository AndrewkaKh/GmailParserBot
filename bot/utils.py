import re
import textwrap
from telegram.helpers import escape_markdown

def escape_markdown_except_links(text):
    """
    Экранирует специальные символы MarkdownV2 в тексте, за исключением ссылок.
    """
    link_pattern = re.compile(r'\[.*?\]\(.*?\)')
    links = link_pattern.findall(text)
    parts = link_pattern.split(text)
    escaped_parts = [escape_markdown(part, version=2) for part in parts]
    return ''.join([escaped + link for escaped, link in zip(escaped_parts, links + [''])])

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
        return f"[ссылка]({escape_markdown(url, version=2)})"
    return url_pattern.sub(replacer, text)

def split_markdown_message(text, max_length=4096):
    """
    Разбивает MarkdownV2 сообщение на части, не нарушая синтаксис MarkdownV2.
    Предпочтительно разбивать по строкам.
    """
    lines = text.split('\\n')
    parts = []
    current_part = ''
    for line in lines:
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part)
                current_part = ''
        if len(line) > max_length:
            split_lines = textwrap.wrap(line, width=max_length, break_long_words=False, replace_whitespace=False)
            parts.extend(split_lines)
        else:
            current_part = current_part + '\\n' + line if current_part else line
    if current_part:
        parts.append(current_part)
    return parts
