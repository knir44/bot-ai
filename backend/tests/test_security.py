import io
import zipfile

import pytest

from app.core import security as sec

MB = 1024 * 1024


def make_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


# ---------------------------------------------------------------- sessions
def test_session_token_roundtrip():
    sid = sec.new_session_id()
    token = sec.sign_session(sid, "secret")
    assert sec.verify_session(sid, token, "secret")


def test_session_token_rejects_tampering():
    sid = sec.new_session_id()
    token = sec.sign_session(sid, "secret")
    assert not sec.verify_session(sec.new_session_id(), token, "secret")  # someone else's id
    assert not sec.verify_session(sid, token[:-1] + ("0" if token[-1] != "0" else "1"), "secret")
    assert not sec.verify_session(sid, token, "other-secret")
    assert not sec.verify_session(sid, "", "secret")
    assert not sec.verify_session("", token, "secret")


# ---------------------------------------------------------------- uploads
def test_accepts_valid_files():
    assert sec.validate_upload("notes.txt", b"hello", MB) == ("notes.txt", ".txt")
    assert sec.validate_upload("a.pdf", b"%PDF-1.7 ...", MB) == ("a.pdf", ".pdf")
    assert sec.validate_upload("b.docx", make_docx(), MB) == ("b.docx", ".docx")


@pytest.mark.parametrize("name", ["virus.exe", "script.sh", "archive.zip", "noextension", "image.png", "doc.pdf.exe"])
def test_rejects_disallowed_extensions(name):
    with pytest.raises(sec.ValidationError):
        sec.validate_upload(name, b"hello", MB)


def test_rejects_spoofed_content():
    with pytest.raises(sec.ValidationError):
        sec.validate_upload("fake.pdf", b"MZ\x90\x00 this is an exe", MB)
    with pytest.raises(sec.ValidationError):
        sec.validate_upload("fake.docx", b"not a zip", MB)
    with pytest.raises(sec.ValidationError):
        sec.validate_upload("fake.docx", b"PK\x03\x04garbage", MB)
    with pytest.raises(sec.ValidationError):
        sec.validate_upload("bin.txt", b"abc\x00\x01\x02", MB)


def test_rejects_oversize_and_empty():
    with pytest.raises(sec.ValidationError):
        sec.validate_upload("big.txt", b"a" * (MB + 1), MB)
    with pytest.raises(sec.ValidationError):
        sec.validate_upload("empty.txt", b"", MB)


def test_filename_path_traversal_is_stripped():
    assert sec.sanitize_filename("../../etc/passwd") == "passwd"
    assert sec.sanitize_filename("C:\\Users\\me\\evil<script>.txt") == "evil_script_.txt"
    assert sec.sanitize_filename("") == "unnamed"


# ---------------------------------------------------------------- text
def test_sanitize_text_strips_control_chars_and_trims():
    assert sec.sanitize_text("  hi\x00 there\x07 \n", 100) == "hi there"


def test_sanitize_text_limits():
    with pytest.raises(sec.ValidationError):
        sec.sanitize_text("   ", 100)
    with pytest.raises(sec.ValidationError):
        sec.sanitize_text("a" * 101, 100)
