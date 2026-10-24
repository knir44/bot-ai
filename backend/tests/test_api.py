"""API-level tests with Elasticsearch, Postgres and Gemini replaced by in-memory fakes.

Covers the session-security flow and the shape of the chat response; retrieval quality
itself is measured against the real stack by scripts/evaluate.py.
"""
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1 import chat as chat_module
from app.api.v1 import health as health_module
from app.repositories import pg_repo
from app.repositories.pg_repo import turns_to_messages
from app.services import llm, rag


class FakePg:
    def __init__(self):
        self.sessions = {}
        self.messages = []

    def create_session(self, sid):
        self.sessions[sid] = "active"

    def session_status(self, sid):
        return self.sessions.get(sid)

    def archive_session(self, sid):
        self.sessions[sid] = "archived"

    def add_turn(self, sid, question, answer, sources=None, trace=None):
        self.messages.append(
            {"id": len(self.messages), "sid": sid, "question": question, "answer": answer, "sources": sources, "trace": trace, "created_at": "now"}
        )

    def get_turns(self, sid, limit=None):
        rows = [t for t in self.messages if t["sid"] == sid]
        return rows[-limit:] if limit else rows

    def get_messages(self, sid):
        return turns_to_messages(self.get_turns(sid))


class FakeEs:
    def ping(self):
        return True

    def count(self):
        return 3

    def list_documents(self):
        return []


CHUNK = {
    "chunk_id": "d:0",
    "doc_id": "d",
    "filename": "apollo_11.txt",
    "chunk_index": 0,
    "content": "Apollo 11 landed on the Moon on July 20, 1969.",
    "rrf_score": 0.0328,
    "contributions": {"bm25": {"rank": 1, "score": 0.0164}, "vector": {"rank": 2, "score": 0.0161}},
    "bm25_score": 9.1,
    "vector_score": 0.8,
}


@pytest.fixture()
def client(monkeypatch):
    pg, es = FakePg(), FakeEs()
    monkeypatch.setattr(deps, "get_pg", lambda: pg)
    monkeypatch.setattr(deps, "get_es", lambda: es)
    monkeypatch.setattr(chat_module, "get_pg", lambda: pg)
    monkeypatch.setattr(health_module, "get_es", lambda: es)
    monkeypatch.setattr(pg_repo, "ping", lambda: True)
    monkeypatch.setattr(
        rag,
        "retrieve",
        lambda *a, **k: {"params": {}, "bm25": [{**CHUNK, "score": 9.1, "rank": 1}], "vector": [], "fused": [CHUNK], "timings_ms": {}},
    )
    monkeypatch.setattr(llm, "generate_answer", lambda prompt: "It landed on July 20, 1969 [1].")
    monkeypatch.setattr(llm, "rewrite_question", lambda q, h: "When did Apollo 11 land?")
    monkeypatch.setattr(chat_module, "get_rag", lambda: rag.RagService(es, pg))

    from app.main import app

    return TestClient(app)


def headers(s):
    return {"X-Session-Id": s["session_id"], "X-Session-Token": s["token"]}


def new_session(client):
    r = client.post("/api/v1/chat/session")
    assert r.status_code == 201
    return r.json()


def test_health_needs_no_auth(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok" and body["indexed_chunks"] == 3


def test_protected_endpoints_reject_missing_or_forged_session(client):
    assert client.get("/api/v1/documents").status_code == 401
    s = new_session(client)
    forged = {"X-Session-Id": s["session_id"], "X-Session-Token": "0" * 64}
    assert client.get("/api/v1/documents", headers=forged).status_code == 401


def test_chat_roundtrip_returns_sources_and_trace(client):
    s = new_session(client)
    r = client.post("/api/v1/chat/message", headers=headers(s), json={"session_id": s["session_id"], "message": "When did Apollo 11 land?"})
    assert r.status_code == 200
    body = r.json()
    assert "[1]" in body["answer"]
    assert body["sources"][0]["filename"] == "apollo_11.txt"
    assert body["sources"][0]["bm25_rank"] == 1 and body["sources"][0]["vector_rank"] == 2
    assert "<context>" in body["trace"]["prompt"]

    hist = client.get("/api/v1/chat/history", params={"session_id": s["session_id"]}, headers=headers(s)).json()
    assert [m["role"] for m in hist["messages"]] == ["user", "assistant"]


def test_one_row_per_turn_with_question_and_answer_columns(client):
    s = new_session(client)
    client.post("/api/v1/chat/message", headers=headers(s), json={"session_id": s["session_id"], "message": "When did Apollo 11 land?"})
    (turn,) = deps.get_pg().get_turns(s["session_id"])
    assert turn["question"] == "When did Apollo 11 land?"
    assert "[1]" in turn["answer"]
    assert turn["sources"][0]["filename"] == "apollo_11.txt"


def test_answers_even_when_index_is_empty(client, monkeypatch):
    s = new_session(client)
    monkeypatch.setattr(FakeEs, "count", lambda self: 0)
    monkeypatch.setattr(llm, "generate_general_answer", lambda q, h: "אין עדיין מסמכים במאגר. תשובה כללית.")
    r = client.post("/api/v1/chat/message", headers=headers(s), json={"session_id": s["session_id"], "message": "מה זה RAG?"})
    assert r.status_code == 200
    body = r.json()
    assert "תשובה כללית" in body["answer"] and body["sources"] == [] and body["trace"] is None


def test_followup_is_rewritten_using_history(client):
    s = new_session(client)
    send = lambda text: client.post("/api/v1/chat/message", headers=headers(s), json={"session_id": s["session_id"], "message": text}).json()
    first = send("Tell me about Apollo 11")
    assert first["trace"]["standalone_query"] == first["trace"]["original_query"]  # no history yet -> unchanged
    second = send("When did it land?")
    assert second["trace"]["standalone_query"] == "When did Apollo 11 land?"


def test_body_session_must_match_header(client):
    a, b = new_session(client), new_session(client)
    r = client.post("/api/v1/chat/message", headers=headers(a), json={"session_id": b["session_id"], "message": "hi"})
    assert r.status_code == 400


def test_cannot_read_someone_elses_history(client):
    a, b = new_session(client), new_session(client)
    r = client.get("/api/v1/chat/history", params={"session_id": b["session_id"]}, headers=headers(a))
    assert r.status_code == 403


def test_reset_archives_old_session_and_returns_new_one(client):
    old = new_session(client)
    r = client.post("/api/v1/chat/reset", headers=headers(old))
    assert r.status_code == 200
    fresh = r.json()
    assert fresh["archived_session_id"] == old["session_id"] and fresh["session_id"] != old["session_id"]
    again = client.post("/api/v1/chat/message", headers=headers(old), json={"session_id": old["session_id"], "message": "hello"})
    assert again.status_code == 409


def test_empty_and_oversized_messages_rejected(client):
    s = new_session(client)
    h = headers(s)
    assert client.post("/api/v1/chat/message", headers=h, json={"session_id": s["session_id"], "message": "   "}).status_code == 422
    big = "a" * 2500  # under the 5000 schema cap, over the 2000 configured cap
    assert client.post("/api/v1/chat/message", headers=h, json={"session_id": s["session_id"], "message": big}).status_code == 422


def test_upload_rejects_bad_file_types_before_any_embedding(client):
    s = new_session(client)
    r = client.post("/api/v1/documents/upload", headers=headers(s), files={"file": ("evil.exe", b"MZ....", "application/octet-stream")})
    assert r.status_code == 422
    r = client.post("/api/v1/documents/upload", headers=headers(s), files={"file": ("fake.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 422
