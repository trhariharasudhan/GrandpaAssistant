import os
import shutil
import sys
from contextlib import contextmanager

from fastapi.testclient import TestClient


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for _path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import api.web_api as web_api  # noqa: E402


CHAT_STATE_PATH = os.path.join(ROOT, "backend", "data", "chat_state.json")


def _print_result(name, ok, details=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}")
    if details:
        print(f"  {details}")


@contextmanager
def _temporary_chat_state():
    os.makedirs(os.path.dirname(CHAT_STATE_PATH), exist_ok=True)
    backup_path = CHAT_STATE_PATH + ".bak.codex"
    if os.path.exists(CHAT_STATE_PATH):
        shutil.copy2(CHAT_STATE_PATH, backup_path)

    try:
        if os.path.exists(CHAT_STATE_PATH):
            os.remove(CHAT_STATE_PATH)
        yield
    finally:
        if os.path.exists(backup_path):
            shutil.move(backup_path, CHAT_STATE_PATH)
        elif os.path.exists(CHAT_STATE_PATH):
            os.remove(CHAT_STATE_PATH)


@contextmanager
def _patched_llm():
    original_generate = web_api.generate_chat_reply
    original_stream = web_api.stream_chat_reply

    def _fake_generate_chat_reply(history, message, model=None, system_prompt=None):
        del history, model, system_prompt
        prompt = str(message or "")
        if "[Source: smoke.txt" in prompt:
            return "From [smoke.txt], the key point is: alpha beta gamma."
        return "Smoke reply ok."

    def _fake_stream_chat_reply(history, message, model=None, system_prompt=None):
        del history, message, model, system_prompt
        yield "Smoke "
        yield "stream reply."

    web_api.generate_chat_reply = _fake_generate_chat_reply
    web_api.stream_chat_reply = _fake_stream_chat_reply
    try:
        yield
    finally:
        web_api.generate_chat_reply = original_generate
        web_api.stream_chat_reply = original_stream


def run_chat_and_rag_flow():
    checks = []
    details = {}

    with _temporary_chat_state(), _patched_llm():
        client = TestClient(web_api.app)

        health = client.get("/api/health")
        health_ok = health.status_code == 200 and health.json().get("ok") is True
        checks.append(("API health", health_ok))

        session_create = client.post("/chat/sessions", json={"title": "Smoke Session"})
        session_payload = session_create.json() if session_create.status_code == 200 else {}
        session_ok = session_create.status_code == 200 and session_payload.get("ok")
        session_id = ((session_payload.get("session") or {}).get("id") or "").strip()
        checks.append(("Session create", bool(session_ok and session_id)))

        chat_reply = client.post("/chat", json={"message": "hello", "session_id": session_id})
        chat_payload = chat_reply.json() if chat_reply.status_code == 200 else {}
        chat_ok = (
            chat_reply.status_code == 200
            and chat_payload.get("ok") is True
            and "reply" in chat_payload
            and "Smoke reply" in str(chat_payload.get("reply"))
        )
        checks.append(("Chat send/reply", chat_ok))

        with client.stream("POST", "/chat/stream", json={"message": "stream please", "session_id": session_id}) as response:
            stream_text = "".join(chunk for chunk in response.iter_text())
        stream_ok = response.status_code == 200 and '"type": "chunk"' in stream_text and '"type": "done"' in stream_text
        checks.append(("Streaming reply", stream_ok))

        rename = client.post("/chat/sessions/rename", json={"session_id": session_id, "title": "Smoke Session Renamed"})
        rename_ok = rename.status_code == 200 and rename.json().get("ok") is True
        checks.append(("Session rename", rename_ok))

        history = client.get("/chat/history", params={"session_id": session_id})
        history_ok = history.status_code == 200 and history.json().get("ok") is True
        checks.append(("Session switch/history", history_ok))

        export = client.get("/chat/export", params={"session_id": session_id})
        export_payload = export.json() if export.status_code == 200 else {}
        export_ok = (
            export.status_code == 200
            and export_payload.get("ok") is True
            and "Smoke Session Renamed" in str(export_payload.get("content", ""))
        )
        checks.append(("Chat export", export_ok))

        upload = client.post(
            "/chat/upload",
            data={"session_id": session_id},
            files={"file": ("smoke.txt", b"alpha beta gamma document text", "text/plain")},
        )
        upload_payload = upload.json() if upload.status_code == 200 else {}
        upload_ok = upload.status_code == 200 and upload_payload.get("ok") is True
        filename = ((upload_payload.get("document") or {}).get("name") or "smoke.txt").strip()
        checks.append(("File upload", upload_ok))

        rag_query = client.post("/chat", json={"message": "what is in the uploaded file?", "session_id": session_id})
        rag_payload = rag_query.json() if rag_query.status_code == 200 else {}
        rag_ok = (
            rag_query.status_code == 200
            and rag_payload.get("ok") is True
            and "[smoke.txt]" in str(rag_payload.get("reply", ""))
        )
        checks.append(("RAG reply with citation", rag_ok))

        remove = client.post("/chat/upload/remove", json={"session_id": session_id, "filename": filename})
        remove_ok = remove.status_code == 200 and remove.json().get("ok") is True
        checks.append(("File remove", remove_ok))

        second_session = client.post("/chat/sessions", json={"title": "Smoke Secondary"})
        second_payload = second_session.json() if second_session.status_code == 200 else {}
        second_id = ((second_payload.get("session") or {}).get("id") or "").strip()
        checks.append(("Second session create", bool(second_id)))

        delete = client.post("/chat/sessions/delete", json={"session_id": session_id})
        delete_ok = delete.status_code == 200 and delete.json().get("ok") is True
        checks.append(("Session delete", delete_ok))

        details["stream_excerpt"] = stream_text[:180].replace("\n", " ")
        details["rag_reply"] = str(rag_payload.get("reply", ""))
        details["remaining_session"] = second_id

    overall_ok = all(flag for _, flag in checks)
    return overall_ok, checks, details


def main():
    overall_ok, checks, details = run_chat_and_rag_flow()

    _print_result("Chat + RAG flow", overall_ok)
    for name, ok in checks:
        _print_result(name, ok)

    _print_result("Stream excerpt", True, details.get("stream_excerpt", ""))
    _print_result("RAG reply sample", True, details.get("rag_reply", ""))
    _print_result("Secondary session id", True, details.get("remaining_session", ""))

    print("\nSummary:")
    print(f"overall_ok={overall_ok}")
    if not overall_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
