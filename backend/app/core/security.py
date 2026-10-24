"""Security helpers: session tokens, upload validation, input sanitization.

Pure functions (no framework imports) so they are trivial to unit test.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import re
import unicodedata
import uuid
import zipfile
from typing import Tuple

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


class ValidationError(ValueError):
    """Raised when user input is rejected. The message is safe to show to the user."""


# --------------------------------------------------------------------------- sessions
# A session is a random UUID plus an HMAC "token" = HMAC_SHA256(secret, session_id).
# Only the server knows the secret, so a client cannot forge a token for somebody
# else's session_id. (This is *not* user authentication - it is capability-style
# access: whoever holds the token owns that conversation.)

def new_session_id() -> str:
    return str(uuid.uuid4())


def sign_session(session_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()


def verify_session(session_id: str, token: str, secret: str) -> bool:
    if not session_id or not token:
        return False
    # compare_digest = constant-time comparison, avoids timing attacks
    return hmac.compare_digest(sign_session(session_id, secret), token)


# --------------------------------------------------------------------------- text
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str, max_chars: int) -> str:
    """Normalize unicode, drop control characters, trim, and enforce a length cap."""
    text = unicodedata.normalize("NFKC", text or "")
    text = _CONTROL_CHARS.sub("", text).strip()
    if not text:
        raise ValidationError("ההודעה ריקה.")
    if len(text) > max_chars:
        raise ValidationError(f"ההודעה ארוכה מדי (מקסימום {max_chars} תווים).")
    return text


def sanitize_filename(name: str) -> str:
    """Strip any path ('../../etc/passwd'), keep only safe characters."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w.\- ]", "_", name, flags=re.UNICODE).strip(" .")
    return name[:100] or "unnamed"


# --------------------------------------------------------------------------- uploads
def validate_upload(filename: str, data: bytes, max_bytes: int) -> Tuple[str, str]:
    """Validate an uploaded file. Returns (safe_filename, extension) or raises ValidationError.

    Three independent checks, because any single one can be spoofed:
      1. extension allow-list      (client controls the name)
      2. size limit                (protects memory / embedding cost)
      3. magic bytes / content     (the file must actually *be* what its extension claims)
    """
    safe = sanitize_filename(filename)
    ext = "." + safe.rsplit(".", 1)[-1].lower() if "." in safe else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"סוג הקובץ '{ext or 'ללא סיומת'}' אינו מותר. מותר להעלות: PDF, TXT, DOCX.")
    if len(data) == 0:
        raise ValidationError("הקובץ ריק.")
    if len(data) > max_bytes:
        raise ValidationError(f"הקובץ גדול מדי (מקסימום {max_bytes // (1024 * 1024)}MB).")

    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValidationError("תוכן הקובץ אינו PDF תקין.")
    elif ext == ".docx":
        if not data.startswith(b"PK\x03\x04"):
            raise ValidationError("תוכן הקובץ אינו DOCX תקין.")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" not in z.namelist():
                    raise ValidationError("תוכן הקובץ אינו DOCX תקין.")
        except zipfile.BadZipFile:
            raise ValidationError("תוכן הקובץ אינו DOCX תקין.")
    else:  # .txt
        if b"\x00" in data[:4096]:
            raise ValidationError("תוכן הקובץ אינו טקסט רגיל.")
        try:
            data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValidationError("קובצי טקסט חייבים להיות בקידוד UTF-8.")
    return safe, ext
