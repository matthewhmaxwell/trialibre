# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Trialibre, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email **security@aimr.org** with:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Scope

Security issues we care about:

- Patient data exposure or leakage
- De-identification bypass (PHI sent to LLM when it shouldn't be)
- Authentication or authorization bypass
- Injection vulnerabilities (SQL, command, prompt)
- Dependency vulnerabilities with known exploits

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Responsible Disclosure

We follow responsible disclosure practices. We will credit reporters in the release notes (unless you prefer to remain anonymous).
