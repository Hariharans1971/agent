# Security policy

## Scope

AltiusNxt Team Copilot is a local portfolio/demo app, not an approved service for real employee, applicant, customer, or company-confidential data. Do not expose it to the public internet without a separate security review.

## Reporting a concern

Do not publish credentials, personal information, or exploit details in a public issue. Use GitHub's private vulnerability reporting feature if enabled for this repository; otherwise contact the maintainer via the [GitHub profile](https://github.com/Hariharans1971) with a concise description and safe reproduction steps.

## Current safeguards and known gaps

- Demo accounts are seeded only when passwords are provided through environment variables.
- Session tokens are random and stored server-side; role checks protect HR and admin operations.
- The app binds to localhost by default and supports only a local demo workflow.
- Request bodies are size-limited and parsed as JSON objects.
- The current-tree secret scan does not inspect old commits. The account-wide history audit must be reviewed separately.
- Authentication hardening, rate limiting, CSRF review, secure production cookie settings, persistent operational logging, and multi-user deployment controls require additional work before any shared deployment.

## Credential handling

Treat a credential committed to a public repository as exposed. Revoke or rotate it with the issuer first, then clean the history only after reviewing the target paths and verifying the current source tree.
