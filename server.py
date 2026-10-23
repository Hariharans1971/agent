import json
import mimetypes
import os
from datetime import datetime, timedelta, timezone
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from altiusnxt_core import (
    APP_ROOT,
    DB_PATH,
    ENGINE,
    KB,
    STATIC_ROOT,
    STORAGE,
    TEMPLATES,
    allowed_visibility_for_role,
    can_access_copilot,
    extract_text_from_upload,
)


mimetypes.add_type("application/javascript", ".js")
SESSION_COOKIE = "altius_session"
MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def log_message(self, format: str, *args):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} - {format % args}")

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/bootstrap":
                return self._handle_bootstrap()
            if parsed.path == "/api/health":
                return self._send_json(
                    {
                        "status": "ok",
                        "runtimeMode": ENGINE.runtime_mode(),
                        "database": str(DB_PATH.relative_to(Path(__file__).resolve().parent)),
                    }
                )
            if parsed.path == "/":
                self.path = "/index.html"
            return super().do_GET()
        except PermissionError:
            return

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/login":
                return self._handle_login()
            if parsed.path == "/api/logout":
                return self._handle_logout()
            if parsed.path == "/api/chat":
                return self._handle_chat()
            if parsed.path == "/api/drafts/save":
                return self._handle_save_draft()
            if parsed.path == "/api/drafts/delete":
                return self._handle_delete_draft()
            if parsed.path == "/api/drafts/clear":
                return self._handle_clear_drafts()
            if parsed.path == "/api/admin/knowledge":
                return self._handle_add_knowledge()
            if parsed.path == "/api/upload":
                return self._handle_upload()
            return self._send_json({"error": "Not found."}, status=404)
        except PermissionError:
            return

    def _handle_bootstrap(self):
        user = self._require_user(optional=True)
        role = user["role"] if user else "guest"
        allowed_templates = [
            template
            for template in TEMPLATES
            if template["team"] != "hr" or role in {"hr", "admin"}
        ]
        payload = {
            "appName": "AltiusNxt Team Copilot",
            "runtimeMode": ENGINE.runtime_mode(),
            "authenticated": bool(user),
            "user": user,
            "templates": allowed_templates,
            "knowledge": KB.list_documents(user_role=role),
            "recentTasks": {
                "marketing": STORAGE.list_recent_tasks(user["id"], "marketing") if user else [],
                "hr": STORAGE.list_recent_tasks(user["id"], "hr") if user else [],
            },
            "drafts": STORAGE.list_drafts(user["id"]) if user else [],
            "copilots": [
                {
                    "id": "marketing",
                    "title": "Marketing Copilot",
                    "description": "Landing pages, campaigns, SEO, ads, LinkedIn posts, and sales-support content.",
                },
                {
                    "id": "hr",
                    "title": "HR Copilot",
                    "description": "Job descriptions, resume summaries, interview kits, outreach, onboarding, and policy support.",
                    "restricted": True,
                },
            ],
            "visibilityOptions": allowed_visibility_for_role(role),
        }
        return self._send_json(payload)

    def _handle_login(self):
        payload = self._read_json_body()
        email = payload.get("email", "").strip()
        password = payload.get("password", "")
        if not email or not password:
            return self._send_json({"error": "Email and password are required."}, status=400)
        user = STORAGE.authenticate(email=email, password=password)
        if not user:
            return self._send_json({"error": "Invalid credentials."}, status=401)
        token = STORAGE.create_session(user["id"])
        self._set_session_cookie(token)
        return self._send_json({"status": "ok", "user": user})

    def _handle_logout(self):
        token = self._get_session_token()
        STORAGE.delete_session(token)
        self._clear_session_cookie()
        return self._send_json({"status": "ok"})

    def _handle_chat(self):
        user = self._require_user()
        payload = self._read_json_body()
        copilot = payload.get("copilot", "marketing")
        if not can_access_copilot(user["role"], copilot):
            return self._send_json({"error": "You do not have access to that copilot."}, status=403)
        message = payload.get("message", "").strip()
        template_id = payload.get("templateId")
        conversation = payload.get("conversation", [])
        if not message:
            return self._send_json({"error": "Message is required."}, status=400)
        result = ENGINE.generate(
            copilot=copilot,
            message=message,
            template_id=template_id,
            conversation=conversation,
            user_role=user["role"],
        )
        STORAGE.add_task(
            user_id=user["id"],
            copilot=copilot,
            prompt=message,
            template_id=template_id,
            response_preview=result["answer"][:500],
        )
        return self._send_json(result)

    def _handle_save_draft(self):
        user = self._require_user()
        payload = self._read_json_body()
        copilot = payload.get("copilot", "marketing")
        if not can_access_copilot(user["role"], copilot):
            return self._send_json({"error": "You do not have access to that copilot."}, status=403)
        title = payload.get("title", "").strip() or f"{copilot.title()} draft"
        content = payload.get("content", "").strip()
        if not content:
            return self._send_json({"error": "Draft content is required."}, status=400)
        draft = STORAGE.save_draft(
            user_id=user["id"],
            draft_id=payload.get("draftId"),
            title=title,
            copilot=copilot,
            content=content,
            sources=payload.get("sources", []),
            mode=payload.get("mode", "local_grounded"),
        )
        return self._send_json({"status": "saved", "draft": draft, "drafts": STORAGE.list_drafts(user["id"])})

    def _handle_delete_draft(self):
        user = self._require_user()
        payload = self._read_json_body()
        draft_id = payload.get("draftId")
        if not draft_id:
            return self._send_json({"error": "draftId is required."}, status=400)
        STORAGE.delete_draft(user_id=user["id"], draft_id=int(draft_id))
        return self._send_json({"status": "deleted", "drafts": STORAGE.list_drafts(user["id"])})

    def _handle_clear_drafts(self):
        user = self._require_user()
        STORAGE.clear_drafts(user["id"])
        return self._send_json({"status": "cleared", "drafts": []})

    def _handle_add_knowledge(self):
        user = self._require_user()
        if user["role"] != "admin":
            return self._send_json({"error": "Only admin users can add shared knowledge notes."}, status=403)
        payload = self._read_json_body()
        title = payload.get("title", "").strip()
        category = payload.get("category", "").strip() or "Custom note"
        content = payload.get("content", "").strip()
        visibility = payload.get("visibility", "shared")
        if visibility not in allowed_visibility_for_role(user["role"]):
            return self._send_json({"error": "Invalid visibility scope."}, status=400)
        if not title or not content:
            return self._send_json({"error": "Title and content are required."}, status=400)
        STORAGE.add_document(
            title=title,
            category=category,
            source=f"Admin note by {user['name']}",
            path="app/data/altiusnxt.db",
            content=content,
            visibility=visibility,
            document_type="note",
            uploader_user_id=user["id"],
        )
        KB.reload()
        return self._send_json({"status": "saved", "knowledge": KB.list_documents(user_role=user["role"])})

    def _handle_upload(self):
        user = self._require_user()
        payload = self._read_json_body()
        file_name = payload.get("fileName", "").strip()
        mime_type = payload.get("mimeType", "application/octet-stream")
        content_b64 = payload.get("contentBase64", "")
        category = payload.get("category", "").strip() or "Uploaded document"
        visibility = payload.get("visibility", "shared")
        if visibility not in allowed_visibility_for_role(user["role"]):
            return self._send_json({"error": "Invalid visibility scope for your role."}, status=400)
        if not file_name or not content_b64:
            return self._send_json({"error": "fileName and contentBase64 are required."}, status=400)
        try:
            extracted_text, raw = extract_text_from_upload(file_name, mime_type, content_b64)
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, status=400)
        saved_path = STORAGE.save_uploaded_file(file_name=file_name, content=raw)
        STORAGE.add_document(
            title=Path(file_name).name,
            category=category,
            source=f"Upload by {user['name']}",
            path=saved_path,
            content=extracted_text,
            visibility=visibility,
            document_type="upload",
            uploader_user_id=user["id"],
        )
        KB.reload()
        return self._send_json({"status": "uploaded", "knowledge": KB.list_documents(user_role=user["role"])})

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            self._send_json({"error": "Invalid Content-Length header."}, status=400)
            raise PermissionError("Invalid Content-Length header")

        if length < 0:
            self._send_json({"error": "Invalid request body length."}, status=400)
            raise PermissionError("Invalid request body length")

        if length > MAX_REQUEST_BODY_BYTES:
            self._send_json(
                {"error": "Request body too large. Keep requests under 10 MiB."},
                status=413,
            )
            raise PermissionError("Request body too large")

        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json({"error": "Request body must be valid UTF-8 JSON."}, status=400)
            raise PermissionError("Invalid JSON request body")

        if not isinstance(payload, dict):
            self._send_json({"error": "JSON request body must be an object."}, status=400)
            raise PermissionError("JSON request body must be an object")

        return payload

    def _require_user(self, optional: bool = False) -> dict | None:
        token = self._get_session_token()
        user = STORAGE.get_user_by_session(token)
        if user or optional:
            return user
        self._send_json({"error": "Authentication required."}, status=401)
        raise PermissionError("Authentication required")

    def _get_session_token(self) -> str | None:
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        jar = cookies.SimpleCookie()
        jar.load(cookie_header)
        morsel = jar.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _set_session_cookie(self, token: str) -> None:
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        self._pending_cookie = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Expires={expires}"

    def _clear_session_cookie(self) -> None:
        self._pending_cookie = f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Expires=Thu, 01 Jan 1970 00:00:00 GMT"

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        pending_cookie = getattr(self, "_pending_cookie", None)
        if pending_cookie:
            self.send_header("Set-Cookie", pending_cookie)
            self._pending_cookie = None
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(os.getenv("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    print(f"AltiusNxt Team Copilot running at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
