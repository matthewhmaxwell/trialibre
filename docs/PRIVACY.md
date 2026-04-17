# Privacy & Compliance Guide

This document describes how Trialibre handles patient data, what the built-in
privacy controls actually do, and what you must do yourself before using it
with real Protected Health Information (PHI).

**Bottom line:** Trialibre can be configured to handle PHI responsibly, but it
is not HIPAA-compliant out of the box. Operating Trialibre on PHI requires
(a) a Business Associate Agreement (BAA) with your AI provider, and
(b) a deployment architecture that enforces network, storage, and access
controls that Trialibre itself does not provide.

---

## What Trialibre does on its own

### Built-in privacy features

- **De-identification (Presidio)**: When the configured AI provider is a cloud
  service (Anthropic, OpenAI, or any OpenAI-compatible remote endpoint),
  Trialibre runs the patient note through Microsoft Presidio to strip names,
  dates, MRNs, phone numbers, email addresses, and URLs before the text is
  sent to the AI. The original text is reconstructed locally when displaying
  results. See `ctm/privacy/engine.py`.
- **Local-only processing**: When the provider is Ollama (running on your
  machine or local network), de-identification is skipped because no data
  leaves the network. The privacy indicator in the UI shows "Private" in this
  mode.
- **API key authentication**: Setting the `CTM_API__API_KEYS` environment
  variable enables API key auth on every endpoint except `/health`.
- **File upload size limits**: 50 MB per upload.
- **Input validation**: NCT IDs, email addresses, and batch sizes are
  validated with strict Pydantic schemas.

### What Trialibre does NOT do

- **No BAA**: Trialibre itself is software, not a service. The AIMR does not
  sign BAAs. You must obtain one from your AI provider.
- **No audit-trail signing**: Audit logs exist but are not cryptographically
  signed or exported to tamper-resistant storage.
- **No automatic patient deletion**: The "Delete after match" UI toggle is
  cosmetic in v0.1.1 — actual enforcement is on the roadmap.
- **No user accounts or RBAC**: API key auth gates the whole API, but all
  authenticated callers have equal access.
- **No network enforcement**: Trialibre will happily talk to any cloud API if
  the URL is reachable. Restricting egress is your deployment's job.
- **No PHI detection quality guarantees**: Presidio catches ~80–95% of common
  PHI but misses patterns specific to clinical text (e.g., provider names in
  unusual formats, patient initials). Do not rely on it as the sole control.

---

## Required steps before using with real PHI

### 1. Sign a BAA with your AI provider

Cloud AI providers will not accept PHI under their default terms. You need
a HIPAA-compliant plan and a signed BAA.

| Provider | Plan required | BAA process |
|---|---|---|
| Anthropic | Enterprise | Contact sales@anthropic.com, specify HIPAA BAA |
| OpenAI | Enterprise or Business API | [platform.openai.com/docs/compliance/baa](https://platform.openai.com/docs/compliance/baa) |
| Azure OpenAI | Microsoft Enterprise Agreement | Usually bundled with existing Microsoft BAA |
| Ollama (local) | N/A — no data leaves your network | N/A |

If you do not have a BAA, **use local Ollama**. It is the only way to run
Trialibre on PHI without one.

### 2. Run on a private network

Trialibre binds to `127.0.0.1` by default. Do not expose port 8000 directly
to the public internet. Put it behind:
- A reverse proxy (nginx, Caddy, Traefik) with TLS
- A VPN (Tailscale, WireGuard) or private VPC
- An identity-aware proxy (Cloudflare Access, IAP, AWS ALB + OIDC)

### 3. Enable API key auth

```bash
export CTM_API__API_KEYS='["a-strong-random-key-here"]'
trialibre serve
```

Clients then include `X-API-Key: a-strong-random-key-here` on every request.
Rotate keys by listing multiple and phasing out the old one.

### 4. Verify de-identification yourself

Presidio is a tool, not a guarantee. Before handling real patients, run a
batch of representative notes through `/api/v1/ingest/patient` and confirm the
returned text is clean. If you see residual PHI, add custom recognizers in
`ctm/privacy/medical_recognizers.py`.

### 5. Restrict data retention

Trialibre stores uploaded trials and referrals in SQLite by default. For PHI
handling:
- Mount the database file on encrypted storage (LUKS, BitLocker, EBS with KMS)
- Back up the database file with the same protections as clinical data
- Set a data retention policy and delete rows explicitly when no longer needed
- Consider disabling the audit log (`CTM_AUDIT__ENABLED=false`) if it would
  store PHI you do not want persisted

### 6. Use the sandbox for demos

Never demo Trialibre with real patient data. Run `trialibre serve` with
sandbox mode enabled and show the built-in synthetic patients and protocols.

---

## Recommended deployment profiles

### Profile A: Personal / single-user research (no PHI)

- Provider: any (Anthropic, OpenAI, Ollama)
- API key auth: disabled
- Network: `127.0.0.1` only
- Suitable for: exploring the tool, sandbox demos, literature-only research

### Profile B: Small clinic with BAA (PHI allowed)

- Provider: Anthropic Enterprise or OpenAI Enterprise, BAA signed
- API key auth: enabled, one key per workstation
- Network: private LAN only, behind VPN for remote access
- Storage: encrypted volume for SQLite file
- De-ID: enabled (auto mode)
- Suitable for: a handful of coordinators screening patients at a single site

### Profile C: Fully offline (PHI allowed, no BAA needed)

- Provider: Ollama with a local model (Llama 3, DeepSeek, Mistral)
- API key auth: enabled
- Network: air-gapped or private VPN
- Storage: encrypted volume
- De-ID: irrelevant (no cloud traffic)
- Trade-off: match quality is lower than cloud models, larger models require
  beefier hardware

---

## Reporting security issues

See [SECURITY.md](../.github/SECURITY.md) for responsible disclosure.

---

## Legal

Trialibre is released under the MIT License. It is provided "as is" without
warranty of any kind. The AIMR is not responsible for misconfiguration,
non-compliance with HIPAA or any other regulation, or any harm that results
from using this software with real patient data.

If you are unsure whether your use case is compliant, consult your institution's
privacy officer and your legal counsel before proceeding.
