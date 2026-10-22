import base64
import csv
import hashlib
import html
import io
import json
import os
import re
import secrets
import sqlite3
import textwrap
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent
APP_ROOT = WORKSPACE_ROOT / "app"
STATIC_ROOT = APP_ROOT / "static"
DATA_ROOT = APP_ROOT / "data"
UPLOADS_ROOT = APP_ROOT / "uploads"
DB_PATH = DATA_ROOT / "altiusnxt.db"

UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def normalize_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9\-\+]{1,}", text.lower())


def chunk_markdown(text: str, source_name: str, category: str, path_label: str) -> list[dict]:
    sections: list[dict] = []
    current_title = "Overview"
    buffer: list[str] = []

    def flush():
        body = "\n".join(buffer).strip()
        if not body:
            return
        pieces = textwrap.wrap(body, width=900, break_long_words=False, replace_whitespace=False)
        for index, piece in enumerate(pieces):
            heading = current_title if index == 0 else f"{current_title} (cont.)"
            sections.append(
                {
                    "id": slugify(f"{source_name}-{heading}-{index}"),
                    "title": f"{source_name} - {heading}",
                    "category": category,
                    "source": source_name,
                    "path": path_label,
                    "content": piece.strip(),
                    "visibility": "shared",
                }
            )

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            current_title = line.lstrip("#").strip() or "Overview"
            buffer = []
            continue
        buffer.append(line)

    flush()
    return sections


def html_to_text(content: str) -> str:
    text = re.sub(r"<(script|style).*?>.*?</\1>", " ", content, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def xml_to_text(content: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(content))).strip()


def allowed_visibility_for_role(role: str) -> list[str]:
    if role == "admin":
        return ["shared", "marketing", "hr", "admin"]
    if role == "hr":
        return ["shared", "hr"]
    if role == "marketing":
        return ["shared", "marketing"]
    return ["shared"]


def can_access_copilot(role: str, copilot: str) -> bool:
    if copilot == "hr":
        return role in {"hr", "admin"}
    return role in {"marketing", "hr", "admin"}


# Local demo users are created only when the matching password environment
# variable is set. Never ship reusable default passwords in source control.
DEFAULT_USERS = [
    {
        "name": "Marketing Demo",
        "email": os.getenv("COPILOT_MARKETING_EMAIL", "marketing@altiusnxt.local"),
        "role": "marketing",
        "password_env": "COPILOT_MARKETING_PASSWORD",
    },
    {
        "name": "HR Demo",
        "email": os.getenv("COPILOT_HR_EMAIL", "hr@altiusnxt.local"),
        "role": "hr",
        "password_env": "COPILOT_HR_PASSWORD",
    },
    {
        "name": "Admin Demo",
        "email": os.getenv("COPILOT_ADMIN_EMAIL", "admin@altiusnxt.local"),
        "role": "admin",
        "password_env": "COPILOT_ADMIN_PASSWORD",
    },
]


TEMPLATES = [
    {
        "id": "landing-page",
        "team": "marketing",
        "title": "Landing Page Draft",
        "description": "Create a conversion-focused landing page for an AltiusNxt service and audience.",
        "prompt": "Create a landing page for [service] targeting [audience]. Focus on business outcomes, differentiators, proof, and a strong CTA.",
    },
    {
        "id": "linkedin-post",
        "team": "marketing",
        "title": "LinkedIn Post",
        "description": "Generate an industry-aware social post for B2B eCommerce decision-makers.",
        "prompt": "Write a LinkedIn post about [topic] for industrial distributors and B2B eCommerce leaders. Keep it insight-led and specific.",
    },
    {
        "id": "ad-copy",
        "team": "marketing",
        "title": "Paid Search Ad Copy",
        "description": "Create headlines and descriptions for high-intent search campaigns.",
        "prompt": "Generate paid search ad copy for [service] aimed at industrial B2B buyers searching for product data support.",
    },
    {
        "id": "seo-brief",
        "team": "marketing",
        "title": "SEO Brief",
        "description": "Build a keyword and content brief for a service topic.",
        "prompt": "Create an SEO brief for [topic], including keyword themes, search intent, content angle, and CTA guidance.",
    },
    {
        "id": "campaign-brief",
        "team": "marketing",
        "title": "Campaign Brief",
        "description": "Outline a targeted campaign with message, audience, and next assets.",
        "prompt": "Build a campaign brief for [service] focused on [audience], including goal, core message, proof, and follow-up assets.",
    },
    {
        "id": "job-description",
        "team": "hr",
        "title": "Job Description",
        "description": "Draft a role description tailored to AltiusNxt's business and delivery model.",
        "prompt": "Draft a job description for [role] at AltiusNxt. Include responsibilities, qualifications, and success metrics.",
    },
    {
        "id": "resume-summary",
        "team": "hr",
        "title": "Resume Summary",
        "description": "Summarize a candidate profile against a target role.",
        "prompt": "Summarize this candidate's resume for the role of [role]. Highlight strengths, relevant experience, and interview focus areas.",
    },
    {
        "id": "interview-kit",
        "team": "hr",
        "title": "Interview Kit",
        "description": "Create structured interview questions and an evaluation plan.",
        "prompt": "Create a first-round interview kit for [role] with questions, evaluation criteria, and a lightweight scorecard.",
    },
    {
        "id": "candidate-outreach",
        "team": "hr",
        "title": "Candidate Outreach",
        "description": "Generate a recruiter outreach email that feels specific and professional.",
        "prompt": "Write a candidate outreach email for [role] that reflects AltiusNxt's culture, growth opportunities, and work context.",
    },
    {
        "id": "onboarding-checklist",
        "team": "hr",
        "title": "Onboarding Checklist",
        "description": "Create a practical first-day, first-week, and first-30-days plan.",
        "prompt": "Create an onboarding checklist for [role], organized by day 1, week 1, and first 30 days.",
    },
]


DEFAULT_TASKS = {
    "marketing": [
        "Refresh Product Data Enrichment landing page",
        "LinkedIn post on taxonomy and conversion",
        "SEO brief for industrial product content",
    ],
    "hr": [
        "JD draft for Product Data Analyst",
        "Interview kit for B2B Content Marketing Manager",
        "Onboarding checklist for Catalog Enrichment Specialist",
    ],
}


PROMPTS = {
    "shared": (
        "You are AltiusNxt Team Copilot, an internal assistant for AltiusNxt. "
        "Ground responses in approved company information. AltiusNxt specializes in B2B eCommerce "
        "product data enrichment, taxonomy, product attributes, PIM and MDM, eCommerce consulting, "
        "technical content writing, and platform integration for industrial distributors. "
        "Be specific, professional, useful, and never invent client facts, metrics, or certifications."
    ),
    "marketing": (
        "You are the Marketing Copilot. Translate technical services into business value for industrial "
        "B2B audiences. Help with landing pages, campaigns, SEO, social posts, emails, case study reuse, "
        "and ad copy. Avoid fluffy consumer marketing language."
    ),
    "hr": (
        "You are the HR Copilot. Support AltiusNxt's HR and recruiting team with job descriptions, resume "
        "summaries, interview kits, onboarding checklists, and policy Q&A. Do not make final hiring decisions "
        "or use protected characteristics."
    ),
}


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
        self.seed_default_users()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    copilot TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    copilot TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    template_id TEXT,
                    response_preview TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    visibility TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    uploader_user_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (uploader_user_id) REFERENCES users(id)
                );
                """
            )

    def seed_default_users(self) -> None:
        with self.connect() as conn:
            existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            if existing:
                return
            for user in DEFAULT_USERS:
                password = os.getenv(user["password_env"], "")
                if not password:
                    continue
                salt = secrets.token_hex(16)
                conn.execute(
                    """
                    INSERT INTO users (name, email, role, salt, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["name"],
                        user["email"].lower(),
                        user["role"],
                        salt,
                        self._hash_password(password, salt),
                        utc_now_iso(),
                    ),
                )

    def _hash_password(self, password: str, salt: str) -> str:
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
        return digest.hex()

    def authenticate(self, email: str, password: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, name, email, role, salt, password_hash FROM users WHERE email = ?",
                (email.lower().strip(),),
            ).fetchone()
            if not row:
                return None
            if self._hash_password(password, row["salt"]) != row["password_hash"]:
                return None
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utc_now_iso(), row["id"]))
            return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        created = datetime.now(timezone.utc)
        expires = created + timedelta(days=7)
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, created.isoformat(), expires.isoformat()),
            )
        return token

    def get_user_by_session(self, token: str | None) -> dict | None:
        if not token:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT users.id, users.name, users.email, users.role, sessions.expires_at
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()
            if not row:
                return None
            if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None
            return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def list_drafts(self, user_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, copilot, content, sources_json, mode, created_at, updated_at
                FROM drafts
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "copilot": row["copilot"],
                "content": row["content"],
                "sources": json.loads(row["sources_json"]),
                "mode": row["mode"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in rows
        ]

    def save_draft(
        self,
        *,
        user_id: int,
        title: str,
        copilot: str,
        content: str,
        sources: list[dict],
        mode: str,
        draft_id: int | None = None,
    ) -> dict:
        now = utc_now_iso()
        with self.connect() as conn:
            if draft_id:
                conn.execute(
                    """
                    UPDATE drafts
                    SET title = ?, copilot = ?, content = ?, sources_json = ?, mode = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (title, copilot, content, json.dumps(sources), mode, now, draft_id, user_id),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO drafts (user_id, title, copilot, content, sources_json, mode, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, title, copilot, content, json.dumps(sources), mode, now, now),
                )
                draft_id = cursor.lastrowid
        return self.get_draft(user_id=user_id, draft_id=draft_id)

    def get_draft(self, *, user_id: int, draft_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, title, copilot, content, sources_json, mode, created_at, updated_at
                FROM drafts WHERE id = ? AND user_id = ?
                """,
                (draft_id, user_id),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "copilot": row["copilot"],
            "content": row["content"],
            "sources": json.loads(row["sources_json"]),
            "mode": row["mode"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def delete_draft(self, *, user_id: int, draft_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM drafts WHERE id = ? AND user_id = ?", (draft_id, user_id))

    def clear_drafts(self, user_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM drafts WHERE user_id = ?", (user_id,))

    def add_task(self, *, user_id: int, copilot: str, prompt: str, template_id: str | None, response_preview: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (user_id, copilot, prompt, template_id, response_preview, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, copilot, prompt, template_id, response_preview, utc_now_iso()),
            )

    def list_recent_tasks(self, user_id: int, copilot: str, limit: int = 8) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT prompt FROM tasks
                WHERE user_id = ? AND copilot = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, copilot, limit),
            ).fetchall()
        return [row["prompt"] for row in rows]

    def add_document(
        self,
        *,
        title: str,
        category: str,
        source: str,
        path: str,
        content: str,
        visibility: str,
        document_type: str,
        uploader_user_id: int | None,
    ) -> dict:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO documents (title, category, source, path, content, visibility, document_type, uploader_user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, category, source, path, content, visibility, document_type, uploader_user_id, utc_now_iso()),
            )
            document_id = cursor.lastrowid
        return self.get_document(document_id)

    def get_document(self, document_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not row:
            return None
        return dict(row)

    def list_documents(self, *, user_role: str) -> list[dict]:
        allowed = allowed_visibility_for_role(user_role)
        placeholders = ", ".join("?" for _ in allowed)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, title, category, source, path, content, visibility, document_type, created_at
                FROM documents
                WHERE visibility IN ({placeholders})
                ORDER BY created_at DESC
                """,
                allowed,
            ).fetchall()
        return [dict(row) for row in rows]

    def save_uploaded_file(self, file_name: str, content: bytes) -> str:
        safe_name = slugify(Path(file_name).stem) or "upload"
        extension = Path(file_name).suffix.lower()
        stamped = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_name}{extension}"
        path = UPLOADS_ROOT / stamped
        path.write_bytes(content)
        return str(path.relative_to(WORKSPACE_ROOT))


class KnowledgeBase:
    def __init__(self, storage: Storage):
        self.storage = storage
        self.facts_path = DATA_ROOT / "company_facts.json"
        self.file_documents: list[dict] = []
        self.reload()

    def reload(self) -> None:
        documents: list[dict] = []
        company_facts = read_json(self.facts_path, [])
        for index, fact in enumerate(company_facts):
            documents.append(
                {
                    "id": fact.get("id", f"fact-{index}"),
                    "title": fact.get("title", f"Company fact {index + 1}"),
                    "category": fact.get("category", "Company"),
                    "source": fact.get("source", "AltiusNxt"),
                    "path": fact.get("path", "Public website"),
                    "content": fact.get("content", "").strip(),
                    "visibility": fact.get("visibility", "shared"),
                }
            )

        for markdown_path in sorted(WORKSPACE_ROOT.glob("*.md")):
            if markdown_path.name == "README.md":
                continue
            text = markdown_path.read_text(encoding="utf-8")
            documents.extend(
                chunk_markdown(
                    text=text,
                    source_name=markdown_path.stem.replace("-", " ").title(),
                    category="Workspace document",
                    path_label=markdown_path.name,
                )
            )

        self.file_documents = [doc for doc in documents if doc["content"]]

    def _allowed_documents(self, user_role: str) -> list[dict]:
        allowed = set(allowed_visibility_for_role(user_role))
        docs = [doc for doc in self.file_documents if doc.get("visibility", "shared") in allowed]
        db_docs = self.storage.list_documents(user_role=user_role)
        for row in db_docs:
            docs.append(
                {
                    "id": f"db-{row['id']}",
                    "title": row["title"],
                    "category": row["category"],
                    "source": row["source"],
                    "path": row["path"],
                    "content": row["content"],
                    "visibility": row["visibility"],
                }
            )
        return docs

    def list_documents(self, user_role: str) -> list[dict]:
        return [
            {
                "id": doc["id"],
                "title": doc["title"],
                "category": doc["category"],
                "source": doc["source"],
                "path": doc["path"],
                "visibility": doc.get("visibility", "shared"),
                "excerpt": doc["content"][:240].strip(),
            }
            for doc in self._allowed_documents(user_role)
        ]

    def search(self, query: str, *, copilot: str, user_role: str, limit: int = 5) -> list[dict]:
        query_tokens = set(normalize_tokens(query))
        profile_tokens = {
            "marketing": {"marketing", "campaign", "seo", "linkedin", "landing", "conversion"},
            "hr": {"hiring", "recruiting", "resume", "candidate", "onboarding", "policy"},
        }.get(copilot, set())
        scored = []
        for doc in self._allowed_documents(user_role):
            doc_tokens = set(normalize_tokens(doc["title"] + " " + doc["content"]))
            overlap = len(query_tokens & doc_tokens)
            profile_overlap = len(profile_tokens & doc_tokens)
            score = overlap * 4 + profile_overlap
            if query_tokens and any(token in doc["category"].lower() for token in query_tokens):
                score += 2
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:limit]]


class CopilotEngine:
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("ALTIUS_MODEL", "gpt-5-mini")

    def runtime_mode(self) -> str:
        return "live_openai" if self.api_key else "local_grounded"

    def generate(self, *, copilot: str, message: str, template_id: str | None, conversation: list[dict], user_role: str = "admin") -> dict:
        sources = self.knowledge_base.search(message, copilot=copilot, user_role=user_role, limit=5)
        if self.api_key:
            try:
                answer = self._generate_with_openai(copilot, message, conversation, template_id, sources)
                return {"answer": answer, "sources": self._public_sources(sources), "mode": self.runtime_mode()}
            except Exception as exc:
                fallback = self._generate_locally(copilot, message, template_id, sources)
                answer = (
                    fallback
                    + "\n\n---\n"
                    + f"_The live model path encountered an error and the app fell back to local grounded mode: {exc}_"
                )
                return {"answer": answer, "sources": self._public_sources(sources), "mode": "local_fallback"}

        answer = self._generate_locally(copilot, message, template_id, sources)
        return {"answer": answer, "sources": self._public_sources(sources), "mode": self.runtime_mode()}

    def _public_sources(self, sources: list[dict]) -> list[dict]:
        return [
            {
                "title": source["title"],
                "category": source["category"],
                "path": source["path"],
                "excerpt": source["content"][:220].strip(),
            }
            for source in sources
        ]

    def _generate_with_openai(self, copilot: str, message: str, conversation: list[dict], template_id: str | None, sources: list[dict]) -> str:
        import urllib.request

        source_context = "\n\n".join(
            f"Source: {source['title']} ({source['category']})\n{source['content']}" for source in sources
        )
        template_context = ""
        if template_id:
            template = next((item for item in TEMPLATES if item["id"] == template_id), None)
            if template:
                template_context = f"\nUse this task pattern when helpful: {template['title']} - {template['prompt']}"

        instructions = (
            f"{PROMPTS['shared']}\n\n{PROMPTS[copilot]}\n\n"
            f"Use the following approved context when relevant:\n{source_context}\n"
            f"{template_context}\n"
            "If context is missing, say what is missing. Structure the answer for workplace use and keep it actionable."
        )

        input_items = []
        for item in conversation[-6:]:
            role = "assistant" if item.get("role") == "assistant" else "user"
            input_items.append({"role": role, "content": [{"type": "input_text", "text": item.get("content", "")}]})
        input_items.append({"role": "user", "content": [{"type": "input_text", "text": message}]})

        payload = {"model": self.model, "instructions": instructions, "input": input_items}
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = json.loads(response.read().decode("utf-8"))
        return self._extract_response_text(raw)

    def _extract_response_text(self, payload: dict) -> str:
        if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
            return payload["output_text"].strip()
        parts = []
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content.get("text"), str):
                    parts.append(content["text"])
        if parts:
            return "\n".join(parts).strip()
        raise RuntimeError("The API response did not include assistant text.")

    def _generate_locally(self, copilot: str, message: str, template_id: str | None, sources: list[dict]) -> str:
        if copilot == "marketing":
            return self._marketing_response(message, template_id, sources)
        return self._hr_response(message, template_id, sources)

    def _marketing_response(self, message: str, template_id: str | None, sources: list[dict]) -> str:
        lower_message = message.lower()
        if template_id == "landing-page" or "landing page" in lower_message:
            return self._marketing_landing_page(message, sources)
        if template_id == "linkedin-post" or "linkedin" in lower_message:
            return self._marketing_linkedin(message, sources)
        if template_id == "ad-copy" or "ad copy" in lower_message or "google ads" in lower_message:
            return self._marketing_ad_copy(message, sources)
        if template_id == "seo-brief" or "seo" in lower_message:
            return self._marketing_seo_brief(message, sources)
        if template_id == "campaign-brief" or "campaign" in lower_message:
            return self._marketing_campaign_brief(message, sources)
        context = self._source_summary(sources)
        return (
            "## Marketing Copilot Response\n"
            "I found the most relevant AltiusNxt context and turned it into a practical starting point.\n\n"
            f"### What matters here\n{context}\n\n"
            "### Recommended next asset\n"
            "- Best next deliverable: a landing page draft or campaign brief tied to a specific service and buyer.\n"
            "- Strong CTA default: `Request a Catalog Audit`.\n"
            "- Strongest audience default: industrial distributors with complex multi-supplier catalogs.\n\n"
            "### Suggested prompt to continue\n"
            "`Create a landing page for product data enrichment targeting industrial distributors.`"
        )

    def _marketing_landing_page(self, message: str, sources: list[dict]) -> str:
        return (
            "## Landing Page Draft\n"
            "### Hero\n"
            "**Headline:** Turn Industrial Product Data Into a Revenue-Ready Buying Experience\n\n"
            "**Subheadline:** AltiusNxt helps industrial distributors enrich, normalize, classify, and structure complex product data across PIM, ERP, and eCommerce platforms so teams can onboard faster, improve discoverability, and support higher conversion potential.\n\n"
            "**Primary CTA:** Request a Catalog Audit\n\n"
            "### Why It Matters\n"
            "- Incomplete supplier data slows onboarding and weakens product discoverability.\n"
            "- Technical buyers need structured attributes, taxonomy, and reliable specs to self-serve confidently.\n"
            "- Clean product data improves search, filtering, and customer trust.\n\n"
            "### Why AltiusNxt\n"
            "- Built for industrial catalogs across MRO, HVAC, electrical, plumbing, and related technical categories.\n"
            "- Combines AI-driven speed with human validation for accuracy and quality control.\n"
            "- Supports PIM, ERP, and eCommerce workflows used by industrial distributors.\n\n"
            "### Outcome Block\n"
            "- Faster SKU onboarding\n"
            "- Better product discoverability\n"
            "- Lower manual catalog effort\n"
            "- Stronger buyer experience across digital channels\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _marketing_linkedin(self, message: str, sources: list[dict]) -> str:
        return (
            "## LinkedIn Draft\n"
            "Industrial eCommerce growth is often limited by something teams underestimate: product data quality.\n\n"
            "When technical buyers cannot quickly filter, compare, and trust the product information on a site, revenue slows down long before pricing or traffic become the real issue.\n\n"
            "AltiusNxt helps industrial distributors turn fragmented supplier data into structured, searchable, conversion-ready product content. From taxonomy and attributes to PIM, ERP, and eCommerce readiness, the focus is simple: improve discoverability, reduce manual effort, and create a stronger digital buying experience.\n\n"
            "For industrial distributors, product data is not just an operations problem. It is a growth lever.\n\n"
            "#B2BeCommerce #IndustrialDistribution #ProductData #PIM #DigitalTransformation\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _marketing_ad_copy(self, message: str, sources: list[dict]) -> str:
        return (
            "## Paid Search Ad Copy\n"
            "### Headlines\n"
            "- Industrial Data Enrichment\n"
            "- Faster SKU Onboarding\n"
            "- Improve Product Discovery\n"
            "- AI + Human Validation\n"
            "- Product Data Ready for PIM\n\n"
            "### Descriptions\n"
            "- Turn incomplete supplier data into structured, searchable content for industrial eCommerce.\n"
            "- Improve discoverability, onboarding speed, and buyer experience with AltiusNxt.\n"
            "- Built for complex distributor catalogs across MRO, HVAC, electrical, and plumbing.\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _marketing_seo_brief(self, message: str, sources: list[dict]) -> str:
        return (
            "## SEO Brief\n"
            "### Primary keyword themes\n"
            "- industrial product data enrichment\n"
            "- product taxonomy services\n"
            "- product attribute development\n"
            "- PIM and eCommerce product content\n\n"
            "### Search intent\n"
            "- Buyers looking for specialized industrial catalog support\n"
            "- Teams trying to improve discoverability, search, and SKU onboarding\n"
            "- Decision-makers evaluating platform-ready product data services\n\n"
            "### Suggested content angle\n"
            "Position AltiusNxt as the specialist that translates fragmented supplier data into conversion-ready product content for industrial distributors.\n\n"
            "### CTA\n"
            "`Request a Catalog Audit`\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _marketing_campaign_brief(self, message: str, sources: list[dict]) -> str:
        return (
            "## Campaign Brief\n"
            "### Goal\n"
            "Generate qualified conversations with industrial distributors that need cleaner, faster, and more scalable product data operations.\n\n"
            "### Audience\n"
            "- eCommerce managers\n"
            "- digital transformation leaders\n"
            "- PIM and catalog operations teams\n\n"
            "### Core message\n"
            "AltiusNxt helps industrial distributors turn incomplete supplier catalog data into structured, discoverable, platform-ready product content.\n\n"
            "### Proof themes\n"
            "- deep industrial catalog specialization\n"
            "- AI plus human validation\n"
            "- compatibility with PIM, ERP, and eCommerce workflows\n\n"
            "### Suggested follow-up assets\n"
            "- landing page\n"
            "- paid search ads\n"
            "- LinkedIn thought-leadership post\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _hr_response(self, message: str, template_id: str | None, sources: list[dict]) -> str:
        lower_message = message.lower()
        if template_id == "job-description" or "job description" in lower_message or lower_message.startswith("jd"):
            return self._hr_job_description(message, sources)
        if template_id == "resume-summary" or "resume" in lower_message or "cv" in lower_message:
            return self._hr_resume_summary(message, sources)
        if template_id == "interview-kit" or "interview" in lower_message:
            return self._hr_interview_kit(message, sources)
        if template_id == "candidate-outreach" or "outreach" in lower_message or "email candidate" in lower_message:
            return self._hr_candidate_outreach(message, sources)
        if template_id == "onboarding-checklist" or "onboarding" in lower_message:
            return self._hr_onboarding(message, sources)
        return (
            "## HR Copilot Response\n"
            "I can help with job descriptions, resume summaries, interview kits, onboarding checklists, and recruiting emails.\n\n"
            "### Best next action\n"
            "- If you want a JD: name the role, team, and experience range.\n"
            "- If you want a resume summary: paste the candidate profile and the target role.\n"
            "- If you want an interview kit: specify the role and interview stage.\n\n"
            f"### Source notes\n{self._source_summary(sources)}"
        )

    def _hr_job_description(self, message: str, sources: list[dict]) -> str:
        return (
            "## Job Description Draft\n"
            "### Role Summary\n"
            "Join AltiusNxt to help industrial eCommerce clients improve product data quality, discoverability, and digital buying experience. This role will support projects across product data enrichment, taxonomy, attributes, and commerce operations.\n\n"
            "### Core Responsibilities\n"
            "- Collaborate with internal delivery and client teams on structured data workflows.\n"
            "- Translate business requirements into repeatable execution steps.\n"
            "- Improve quality, consistency, and readiness of catalog or project outputs.\n"
            "- Contribute to documentation, reviews, and cross-functional coordination.\n\n"
            "### Preferred Qualifications\n"
            "- Experience in B2B eCommerce, industrial catalogs, PIM, content operations, or adjacent workflows.\n"
            "- Strong written communication and attention to detail.\n"
            "- Comfort working with process-driven delivery and quality checks.\n\n"
            "### Success Metrics\n"
            "- Output quality\n"
            "- Delivery reliability\n"
            "- Cross-team collaboration\n"
            "- Process adherence and improvement\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _hr_resume_summary(self, message: str, sources: list[dict]) -> str:
        return (
            "## Resume Summary Template\n"
            "### Candidate Snapshot\n"
            "- Relevant experience: summarize years, domains, and core responsibilities from the pasted profile.\n"
            "- Functional fit: note alignment with product data, eCommerce, marketing, HR, or operations work.\n"
            "- Delivery signals: note ownership, quality focus, client interaction, and process rigor.\n\n"
            "### Strengths To Highlight\n"
            "- Domain familiarity with B2B or industrial workflows\n"
            "- Writing, coordination, analysis, or catalog operations strengths\n"
            "- Evidence of handling structured, detail-heavy work\n\n"
            "### Potential Gaps To Validate\n"
            "- Platform exposure\n"
            "- Team collaboration experience\n"
            "- Communication clarity\n"
            "- Scale or complexity of prior work\n\n"
            "### Interview Focus Areas\n"
            "- Problem-solving approach\n"
            "- Accuracy and quality control habits\n"
            "- Stakeholder communication\n"
            "- Role-specific tools or domain experience\n\n"
            "_Paste the resume text into the prompt to get a more specific summary._\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _hr_interview_kit(self, message: str, sources: list[dict]) -> str:
        return (
            "## Interview Kit\n"
            "### Questions\n"
            "1. Tell us about a project where you handled detailed, structured information under deadlines.\n"
            "2. How do you maintain quality when working on repetitive or high-volume tasks?\n"
            "3. Describe a time you coordinated with cross-functional stakeholders to complete a deliverable.\n"
            "4. What attracts you to AltiusNxt's focus on industrial eCommerce and product data services?\n"
            "5. How do you learn a new domain quickly when the terminology is technical?\n"
            "6. Describe how you prioritize when multiple requests arrive at once.\n"
            "7. Tell us about a time you improved a process or documentation workflow.\n"
            "8. How do you handle feedback or revision requests?\n"
            "9. What does strong ownership look like in your day-to-day work?\n"
            "10. What would help you ramp quickly in this role?\n\n"
            "### Traits To Evaluate\n"
            "- Communication\n"
            "- Structured thinking\n"
            "- Quality orientation\n"
            "- Ownership\n"
            "- Domain curiosity\n\n"
            "### Scorecard\n"
            "- 1: weak signal\n"
            "- 2: mixed signal\n"
            "- 3: strong signal\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _hr_candidate_outreach(self, message: str, sources: list[dict]) -> str:
        return (
            "## Candidate Outreach Email\n"
            "**Subject:** Opportunity to Explore a Role at AltiusNxt\n\n"
            "Hi [Candidate Name],\n\n"
            "I came across your profile and thought your background may be relevant for opportunities at AltiusNxt. We work with industrial distributors and B2B commerce teams on product data enrichment, eCommerce, and digital operations projects.\n\n"
            "Our team values ownership, structured thinking, and a strong quality mindset. If you are open to a conversation, I would be glad to share more about the role and learn about your experience.\n\n"
            "Best regards,\n"
            "[Recruiter Name]\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _hr_onboarding(self, message: str, sources: list[dict]) -> str:
        return (
            "## Onboarding Checklist\n"
            "### Day 1\n"
            "- Complete welcome and team introductions\n"
            "- Review AltiusNxt overview, services, and team structure\n"
            "- Set up system access and communication tools\n\n"
            "### Week 1\n"
            "- Review service lines, core workflows, and quality expectations\n"
            "- Shadow current delivery or team processes\n"
            "- Understand how work is reviewed and escalated\n\n"
            "### First 30 Days\n"
            "- Own a small scoped task independently\n"
            "- Document learnings and process questions\n"
            "- Align with manager on role-specific goals and ramp plan\n\n"
            f"### Source notes\n{self._source_summary(sources)}\n\n"
            f"### User request context\n{message.strip()}"
        )

    def _source_summary(self, sources: list[dict]) -> str:
        if not sources:
            return "- No matching internal sources found. The response uses general AltiusNxt defaults."
        return "\n".join(
            f"- {source['title']} ({source['category']}): {source['content'][:140].strip()}..."
            for source in sources[:3]
        )


def extract_text_from_upload(file_name: str, mime_type: str, payload_b64: str) -> tuple[str, bytes]:
    raw = base64.b64decode(payload_b64)
    extension = Path(file_name).suffix.lower()

    if len(raw) > 6 * 1024 * 1024:
        raise ValueError("Upload too large. Keep files under 6 MB for this local build.")

    if extension in {".txt", ".md", ".py", ".json", ".csv", ".tsv", ".html", ".htm"}:
        text = raw.decode("utf-8", errors="replace")
        if extension == ".json":
            try:
                parsed = json.loads(text)
                text = json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                pass
        elif extension in {".csv", ".tsv"}:
            delimiter = "\t" if extension == ".tsv" else ","
            rows = csv.reader(io.StringIO(text), delimiter=delimiter)
            text = "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
        elif extension in {".html", ".htm"}:
            text = html_to_text(text)
        return text.strip(), raw

    if extension == ".docx":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            xml_content = archive.read("word/document.xml").decode("utf-8", errors="replace")
        return xml_to_text(xml_content), raw

    if extension == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return text.strip(), raw
        except Exception as exc:
            raise ValueError(f"PDF extraction is not available in this environment: {exc}") from exc

    if mime_type.startswith("text/"):
        return raw.decode("utf-8", errors="replace").strip(), raw

    raise ValueError("Unsupported file type. Upload .txt, .md, .json, .csv, .tsv, .html, .docx, or .pdf.")


STORAGE = Storage(DB_PATH)
KB = KnowledgeBase(STORAGE)
ENGINE = CopilotEngine(KB)
