# Production Deployment Guide

This guide walks through deploying Trialibre with TLS, persistent storage,
healthchecks, and authentication. For a development install, see the
[Quickstart in the README](../README.md#quickstart) instead.

> **Before deploying with real PHI:** read [PRIVACY.md](PRIVACY.md). You need a
> BAA with your AI provider unless you are running fully offline with Ollama.

---

## Prerequisites

- A Linux server with Docker 24+ and Docker Compose v2
- A DNS A record pointing your chosen subdomain at the server's public IP
- Ports 80 and 443 open (Caddy needs both for Let's Encrypt's HTTP-01 challenge)
- Backup destination (S3, restic, BorgBase, or anywhere durable)

---

## Quick deploy: cloud LLM with TLS

```bash
# 1. Clone and configure
git clone https://github.com/matthewhmaxwell/trialibre.git
cd trialibre
cp .env.example .env
$EDITOR .env  # set DOMAIN, ADMIN_EMAIL, CTM_LLM__API_KEY, CTM_API__API_KEYS

# 2. Generate API keys (one per consuming application)
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add to CTM_API__API_KEYS in .env (JSON array)

# 3. Bring everything up
docker compose -f docker-compose.prod.yml up -d

# 4. Verify
curl https://your-domain.example.com/api/v1/health
```

Caddy will obtain a TLS cert from Let's Encrypt automatically on first start
(takes 15-60 seconds). Logs:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

---

## Required environment variables

Create `.env` in the project root with at minimum:

```bash
# Public hostname for the Caddy reverse proxy
DOMAIN=trialibre.example.com
ADMIN_EMAIL=ops@example.com

# LLM provider configuration
CTM_LLM__PROVIDER=anthropic           # or openai, ollama, openai_compat
CTM_LLM__MODEL=claude-sonnet-4-20250514
CTM_LLM__API_KEY=sk-ant-...           # required for cloud providers

# API key authentication — REQUIRED for production
# JSON array of strings; rotate by adding new and removing old over time
CTM_API__API_KEYS=["a-strong-random-key", "another-key-for-rotation"]

# Optional: restrict CORS to your frontend's origin
CTM_API__CORS_ORIGINS=["https://trialibre.example.com"]
```

---

## Offline deployment with Ollama

For HIPAA scenarios where you do not want any data leaving your network:

```bash
# Use the local profile to also start Ollama
docker compose -f docker-compose.prod.yml --profile local up -d

# Pull a model into the Ollama container
docker compose -f docker-compose.prod.yml exec ollama ollama pull llama3.1:8b

# Set CTM_LLM__PROVIDER=ollama and CTM_LLM__BASE_URL=http://ollama:11434 in .env
```

For a dedicated GPU host, mount the GPU into the Ollama container by adding
to `docker-compose.prod.yml`:

```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

---

## Backups

Trialibre stores all uploaded trials, referrals, and batch jobs in
`/data/trialibre.db` inside the container, which lives on the
`trialibre-data` named volume.

### Daily backup with cron + restic

```bash
# /etc/cron.d/trialibre-backup
0 2 * * * root cd /opt/trialibre && \
  docker compose -f docker-compose.prod.yml exec -T trialibre \
    sqlite3 /data/trialibre.db ".backup /tmp/backup.db" && \
  docker cp $(docker compose -f docker-compose.prod.yml ps -q trialibre):/tmp/backup.db /backups/trialibre-$(date +\%F).db
```

### Snapshot the named volume

```bash
docker run --rm \
  -v trialibre_trialibre-data:/data:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/trialibre-$(date +%F).tar.gz -C /data .
```

---

## Monitoring & health checks

The `/api/v1/health` endpoint is exempt from API key auth and reports:

- Server status, version, and current LLM provider
- Whether the LLM is reachable
- Sandbox mode status
- Capability detection (OCR, WeasyPrint, Presidio, FAISS)
- Active warnings (misconfigured provider, missing dependencies, etc.)

Wire it into your monitoring system:

```bash
# Uptime check
curl -fsS https://trialibre.example.com/api/v1/health > /dev/null

# Detailed warnings
curl -fsS https://trialibre.example.com/api/v1/health | jq '.warnings'
```

The Docker compose file already includes a healthcheck that restarts the
container if the endpoint stops responding.

---

## Logs

```bash
# Tail all services
docker compose -f docker-compose.prod.yml logs -f

# Just the app
docker compose -f docker-compose.prod.yml logs -f trialibre

# Just Caddy (TLS issuance, requests)
docker compose -f docker-compose.prod.yml logs -f caddy
```

For production, ship logs to a central system (Loki, Datadog, CloudWatch).
Caddy emits JSON access logs to stdout; the Trialibre app emits standard
Python `logging` output.

---

## Upgrades

```bash
# 1. Back up the database first
docker compose -f docker-compose.prod.yml exec -T trialibre \
  sqlite3 /data/trialibre.db ".backup /tmp/pre-upgrade.db"
docker cp $(docker compose -f docker-compose.prod.yml ps -q trialibre):/tmp/pre-upgrade.db ./backups/

# 2. Pull and rebuild
git pull
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# 3. Verify
curl https://your-domain.example.com/api/v1/health
```

Trialibre uses SQLAlchemy's `Base.metadata.create_all` on startup to add new
tables; existing tables are left alone. For column changes (rare), run
Alembic migrations manually first.

---

## Hardening checklist

Before going live with PHI:

- [ ] BAA signed with the AI provider (Anthropic/OpenAI Enterprise) — see [PRIVACY.md](PRIVACY.md)
- [ ] `CTM_API__API_KEYS` is set with strong random keys (32+ chars each)
- [ ] `CTM_API__CORS_ORIGINS` restricted to your frontend's exact origin
- [ ] `DOMAIN` resolves to your server, TLS is verifiably valid (`curl -v https://...`)
- [ ] Database volume is on encrypted storage (LUKS/dm-crypt, BitLocker, or cloud KMS-backed)
- [ ] Backups configured and tested (you have actually restored from one)
- [ ] Reverse proxy logs do not capture request bodies (would store patient text)
- [ ] Server firewall blocks ports other than 80/443 from the public internet
- [ ] SSH access is key-only with fail2ban or equivalent
- [ ] Trialibre version pinned in `git checkout v0.X.Y` rather than tracking `main`
- [ ] Operational runbook documented for your team (who responds to alerts, how to roll back)

---

## Troubleshooting

### Caddy fails to issue a certificate

Check that:
- `DOMAIN` in `.env` matches the actual public DNS record
- The DNS A/AAAA record has propagated (`dig +short $DOMAIN`)
- Ports 80 and 443 are open on the public internet (not just your VPN)
- Let's Encrypt's rate limits aren't exceeded (5 cert issuances per week per
  domain on first run)

### `/health` returns warnings

These are informational. Common ones:
- `"Tesseract is not installed"` — install `tesseract-ocr` system package
  if you need OCR
- `"Ollama is selected as the provider but the server is not reachable"` —
  check `docker compose ps`, ensure Ollama healthcheck passes
- `"Running in sandbox mode"` — set `CTM_LLM__API_KEY` (cloud) or fix
  Ollama (local)

### Match endpoint is slow

- Cloud LLM: each criterion = 1 API call. A trial with 20 criteria takes
  ~20 seconds with Claude Sonnet. Use `max_trials` to limit screening cost.
- Local Ollama: depends on model size and hardware. Smaller models
  (Llama 3 8B) are 5-10x faster than larger ones (70B+).

### Database file grows large

SQLite includes WAL files. Periodic vacuum:

```bash
docker compose -f docker-compose.prod.yml exec trialibre \
  sqlite3 /data/trialibre.db "VACUUM;"
```

---

## Going beyond this guide

For larger deployments (multi-tenant, > 100 concurrent users, > 1M trials):

- Switch to PostgreSQL: set `CTM_DATABASE__BACKEND=postgresql` and
  `CTM_DATABASE__POSTGRESQL_URL`
- Run multiple Trialibre instances behind a load balancer (the app is
  stateless apart from the database)
- Add Redis for distributed caching of LLM responses
- Use a managed object store (S3) for uploaded protocol PDFs

These are out of scope for the v0.x deployment guide. Open a discussion on
[GitHub](https://github.com/matthewhmaxwell/trialibre/discussions) if you
need help with a non-trivial deployment.
