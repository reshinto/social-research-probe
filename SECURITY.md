# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| 0.1.x   | No        |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email the maintainer at the address in `pyproject.toml` with:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact

You will receive an acknowledgement within 72 hours. Critical fixes will be patched within 14 days.

## Scope

In scope: authentication bypass, secret leakage, command injection, SSRF, privilege escalation.

Out of scope: denial-of-service against local CLI usage, issues in transitive dependencies (please report those upstream).
