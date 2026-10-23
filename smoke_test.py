import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:8765"


def build_client():
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return opener


def fetch(opener, path: str, data: dict | None = None):
    request = urllib.request.Request(f"{BASE_URL}{path}")
    if data is not None:
        encoded = json.dumps(data).encode("utf-8")
        request.data = encoded
        request.add_header("Content-Type", "application/json")
        request.method = "POST"
    with opener.open(request, timeout=12) as response:
        payload = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return json.loads(payload)
    return payload


def wait_for_server(opener) -> None:
    last_error = None
    for _ in range(30):
        try:
            content = fetch(opener, "/api/health")
            if content:
                return
        except (urllib.error.URLError, ConnectionError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Server did not become ready in time: {last_error}")


def login(opener, email: str, password: str):
    return fetch(opener, "/api/login", {"email": email, "password": password})


def expect_http_error(opener, path: str, data: dict, expected_status: int) -> None:
    try:
        fetch(opener, path, data)
    except urllib.error.HTTPError as exc:
        if exc.code != expected_status:
            raise AssertionError(
                f"{path} returned HTTP {exc.code}; expected {expected_status}."
            ) from exc
        return
    raise AssertionError(f"{path} unexpectedly succeeded; expected HTTP {expected_status}.")


def expect_raw_http_error(
    opener,
    path: str,
    raw_body: bytes,
    expected_status: int,
    *,
    declared_length: int | None = None,
) -> None:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=raw_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if declared_length is not None:
        request.add_header("Content-Length", str(declared_length))

    try:
        with opener.open(request, timeout=12) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code != expected_status:
            raise AssertionError(
                f"{path} returned HTTP {exc.code}; expected {expected_status}."
            ) from exc
        return
    raise AssertionError(f"{path} unexpectedly succeeded; expected HTTP {expected_status}.")


def main() -> None:
    marketing_email = os.getenv("COPILOT_MARKETING_EMAIL", "marketing@altiusnxt.local")
    marketing_password = os.getenv("COPILOT_MARKETING_PASSWORD", "")
    hr_email = os.getenv("COPILOT_HR_EMAIL", "hr@altiusnxt.local")
    hr_password = os.getenv("COPILOT_HR_PASSWORD", "")
    if not marketing_password or not hr_password:
        raise SystemExit(
            "Set COPILOT_MARKETING_PASSWORD and COPILOT_HR_PASSWORD in your local "
            "environment before running the smoke test. Do not use committed default passwords."
        )

    process = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT)
    opener = build_client()

    try:
        wait_for_server(opener)
        health = fetch(opener, "/api/health")
        guest_bootstrap = fetch(opener, "/api/bootstrap")
        expect_raw_http_error(opener, "/api/login", b"{", 400)
        expect_raw_http_error(opener, "/api/login", b"[]", 400)
        expect_raw_http_error(
            opener,
            "/api/login",
            b"{}",
            413,
            declared_length=10 * 1024 * 1024 + 1,
        )
        expect_http_error(
            opener,
            "/api/chat",
            {"copilot": "marketing", "message": "This request must be rejected while logged out."},
            401,
        )
        html = fetch(opener, "/")

        marketing_login = login(opener, marketing_email, marketing_password)
        if marketing_login.get("user", {}).get("role") != "marketing":
            raise AssertionError("Marketing account did not receive the marketing role.")
        marketing_bootstrap = fetch(opener, "/api/bootstrap")
        expect_http_error(
            opener,
            "/api/chat",
            {"copilot": "hr", "message": "A marketing account must not access HR."},
            403,
        )
        marketing_chat = fetch(
            opener,
            "/api/chat",
            {
                "copilot": "marketing",
                "message": "Create a short campaign brief for product data enrichment.",
                "conversation": [],
            },
        )
        draft_save = fetch(
            opener,
            "/api/drafts/save",
            {
                "title": "Marketing smoke draft",
                "copilot": "marketing",
                "content": marketing_chat["answer"],
                "sources": marketing_chat["sources"],
                "mode": marketing_chat["mode"],
            },
        )
        upload_payload = base64.b64encode(b"Candidate: Jane Doe\nExperience: B2B content marketing and industrial catalog writing").decode("ascii")
        upload = fetch(
            opener,
            "/api/upload",
            {
                "fileName": "candidate-note.txt",
                "mimeType": "text/plain",
                "contentBase64": upload_payload,
                "category": "Recruiting note",
                "visibility": "shared",
            },
        )
        fetch(opener, "/api/logout", {})

        hr_opener = build_client()
        hr_login = login(hr_opener, hr_email, hr_password)
        if hr_login.get("user", {}).get("role") != "hr":
            raise AssertionError("HR account did not receive the HR role.")
        expect_http_error(
            hr_opener,
            "/api/admin/knowledge",
            {"title": "CI access test", "content": "This request must be rejected for non-admins."},
            403,
        )
        hr_bootstrap = fetch(hr_opener, "/api/bootstrap")
        hr_chat = fetch(
            hr_opener,
            "/api/chat",
            {
                "copilot": "hr",
                "message": "Create a first-round interview kit for a B2B content marketing manager.",
                "conversation": [],
            },
        )

        print("Health:", health)
        print("HTML route ok:", "AltiusNxt Team Copilot" in html)
        print("Guest authenticated:", guest_bootstrap["authenticated"])
        print("Marketing login user:", marketing_login["user"]["email"])
        print("Marketing templates:", len(marketing_bootstrap["templates"]))
        print("Draft count after save:", len(draft_save["drafts"]))
        print("Knowledge count after upload:", len(upload["knowledge"]))
        print("HR authenticated:", hr_bootstrap["authenticated"])
        print("HR knowledge visible:", len(hr_bootstrap["knowledge"]))
        print("Marketing chat mode:", marketing_chat["mode"])
        print("Marketing preview:", marketing_chat["answer"][:150].replace("\n", " "))
        print("HR preview:", hr_chat["answer"][:150].replace("\n", " "))
        print("Smoke test passed.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
