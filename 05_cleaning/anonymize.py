import re

def anonymize_text(text: str) -> str:
    # Email first so @ inside email doesn't get picked up by username
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    # URL (http/https)
    text = re.sub(r'https?://\S+', '[ССЫЛКА]', text)
    # domains/t.me
    text = re.sub(r't\.me/\S+', '[ССЫЛКА]', text)
    # Phone numbers (+7...)
    text = re.sub(r'\+7[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}', '[ТЕЛЕФОН]', text)
    # Usernames (@...)
    text = re.sub(r'@\w+', '[АККАУНТ]', text)
    # Geo
    text = re.sub(r'\d{2}\.\d{3},\s?\d{2}\.\d{3}', '[ГЕОЛОКАЦИЯ]', text)
    # Names (simple heuristic or placeholder)
    text = re.sub(r'Данияр[уа]?', '[ИМЯ]', text)
    return text

if __name__ == "__main__":
    sample = "Call +7 777 123 45 67 or +77771234567, email job@mail.ru, see https://example.com @username"
    print(anonymize_text(sample))
