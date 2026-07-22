import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789",
    "1234567890", "qwerty123", "qwerty", "abc12345", "iloveyou",
    "admin123", "letmein", "welcome1", "monkey123", "dragon123",
}


def validate_password(pw: str) -> str | None:
    """Returns an error message, or None if the password is valid. Mirrors
    the rules in pages/0_User_Form.py so signup enforces the same policy
    whether it comes through Streamlit or the new frontend."""
    if not pw.strip():
        return "Password must not consist of only whitespace."
    if len(pw) < 8:
        return "Password must be at least 8 characters long."
    if len(pw) > 128:
        return "Password must not exceed 128 characters."
    if pw.lower() in COMMON_PASSWORDS:
        return "This password is too common. Please choose a stronger one."
    if not re.search(r"[A-Z]", pw):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", pw):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"\d", pw):
        return "Password must contain at least one number."
    if not re.search(r"[^A-Za-z0-9]", pw):
        return "Password must contain at least one special character (e.g. @, #, !)."
    return None
