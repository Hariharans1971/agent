# AltiusNxt Team Copilot — Portfolio Demo

A local Python application demonstrating a two-workspace copilot concept for marketing and HR workflows. It includes draft generation, a local knowledge base, document indexing, task history, and an optional model-provider integration.

> **Security and scope:** This repository is a portfolio/demo project. Do not use it with real employee, applicant, customer, or company-confidential data. Review authorization, session handling, prompt-injection defenses, logging, and data retention before any shared deployment. No credentials should be published in this README.

## Features

- Marketing and HR workflow prototypes
- Local knowledge base and document indexing
- Saved drafts and task history
- Optional OpenAI API integration via environment variables
- Local health/status utilities and smoke-test script

## Run locally

Use a supported Python 3 version and install the dependencies listed in the repository's requirements file, if present.

```powershell
python launch_agent.py
```

Then open `http://127.0.0.1:8765`.

If the launcher is unavailable in your checkout, inspect `server.py` and the current project structure before running the server directly.

## Optional model integration

Set your own API key in the local environment. Never commit it or place it in source code.

```powershell
$env:OPENAI_API_KEY = "your-local-key"
python launch_agent.py
```

The model can be configured through `ALTIUS_MODEL` if supported by the installed version. Check provider documentation and current model availability before configuring a deployment.

## Smoke test

```powershell
python smoke_test.py
```

Run this only after reviewing the script and installing the project's dependencies.

## Before any deployment

- Replace demo authentication with securely managed credentials and password hashing.
- Enforce authorization checks on every protected operation and document access.
- Use a secret manager or environment variables for provider keys.
- Add CSRF protections where applicable, rate limiting, upload validation, and safe file handling.
- Avoid embedding internal company information or real user data in a public repository.
- Add automated tests for authentication, role isolation, API errors, and document permissions.

## License and attribution

Check the repository's current license and confirm that all included company-specific materials are authorized for public distribution before reusing or deploying them.
