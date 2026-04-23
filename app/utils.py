import re
import html


def sanitize_text(text: str, max_length: int = 5000) -> str:
    if not text:
        return ""
    text = text.strip()
    text = text[:max_length]
    text = html.escape(text)
    return text


def sanitize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def sanitize_email(email: str) -> str:
    if not email:
        return ""
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return ""
    return email


def sanitize_domain(domain: str) -> str:
    if not domain:
        return ""
    domain = domain.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    return domain