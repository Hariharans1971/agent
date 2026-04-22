# AltiusNxt Team Copilot

Local internal copilot app for AltiusNxt with two team-specific workspaces:
- Marketing Copilot
- HR Copilot

The app runs without external dependencies and uses a grounded local mode by default. If you set `OPENAI_API_KEY`, it will automatically use the OpenAI Responses API for live model output.

## What It Includes
- Marketing workspace for landing pages, campaigns, SEO briefs, ad copy, LinkedIn posts, and email drafts
- HR workspace for job descriptions, resume summaries, interview kits, onboarding checklists, and candidate outreach
- Approved-source knowledge base seeded with AltiusNxt company facts and the workspace strategy docs
- SQLite-backed users, sessions, drafts, task history, and indexed uploaded documents
- Role-aware knowledge visibility, protected HR workspace access, and admin-managed knowledge notes
- Saved drafts, task history, template library, file upload, and admin note management

## Run The App
1. Open a terminal in this folder.
2. Run:

```powershell
python launch_agent.py
```

3. Open:

```text
http://127.0.0.1:8765
```

## Demo Accounts

Use one of these local accounts on the login screen:

```text
marketing@altiusnxt.local / Marketing123!
hr@altiusnxt.local / HR12345!
admin@altiusnxt.local / Admin12345!
```

## Optional Live AI Mode
Set an API key before starting the server:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
python launch_agent.py
```

The app defaults to `gpt-5-mini` and can be changed with:

```powershell
$env:ALTIUS_MODEL="gpt-5.2"
```

## Quick Launcher
You can also run:

```powershell
.\run_agent.bat
```

## Server Controls

Check status:

```powershell
python agent_status.py
```

Stop the running server:

```powershell
python stop_agent.py
```

## Smoke Test
To verify the server, auth flow, UI bootstrap, Marketing Copilot, HR Copilot, draft persistence, and upload indexing in one shot:

```powershell
python smoke_test.py
```
