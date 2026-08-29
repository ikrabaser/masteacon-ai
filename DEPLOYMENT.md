# Deploying Masteacon to a VPS

This walks through taking the app from local Docker Compose to a real VPS,
reachable over HTTPS on your own domain, using the production overlay
(`docker-compose.prod.yml`) and Caddy for automatic TLS.

## 1. Provision the server

Any VPS with Docker support works (DigitalOcean, Hetzner, Linode, ...).
Minimum realistically comfortable size:

- **2 vCPU / 4 GB RAM** if you'll ever enable `RERANKER_PROVIDER=cross_encoder`
  (pulls in PyTorch — the model itself is small, but PyTorch's own memory
  footprint is not). **1 vCPU / 2 GB** is enough with reranking off or on
  `lexical`.
- 20GB+ disk (Docker images, Postgres data, uploaded documents).

Install Docker + the Compose plugin (Ubuntu/Debian):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out/in after this
```

## 2. Point DNS at the server

Create an **A record** for the domain you'll use (e.g. `app.yourdomain.com`)
pointing at the server's public IP. Caddy needs this to resolve *before* it
can request a certificate — give DNS a few minutes to propagate.

## 3. Get the code onto the server

```bash
git clone https://github.com/ikrabaser/masteacon-ai.git
cd masteacon-ai
```

## 4. Configure environment

```bash
cp .env.production.example .env
nano .env   # fill in every line marked "MUST CHANGE"
```

At minimum you need: a real `OPENAI_API_KEY`, a generated `JWT_SECRET_KEY`
(`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`), `DOMAIN`
set to your real domain, and `CORS_ORIGINS`/`FRONTEND_BASE_URL` set to
`https://<DOMAIN>`. If you want email verification working, also fill in
`RESEND_API_KEY` (see [resend.com](https://resend.com)).

## 5. Build and start everything

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

First build takes a while (Python deps, especially if `RERANKER_PROVIDER`
is ever set to `cross_encoder`). Caddy will automatically request and renew
a Let's Encrypt certificate for `DOMAIN` on first boot — this needs port 80
reachable from the internet for the ACME HTTP challenge.

## 6. Verify

```bash
docker compose ps                 # everything should be "healthy" or "running"
curl -I https://app.yourdomain.com/health
```

Then open `https://app.yourdomain.com` in a browser, register an account,
upload a document, and ask it a question.

## Updating a running deployment

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Compose only recreates containers whose image or config actually changed —
this is safe to run repeatedly. Database migrations run automatically on
`api` startup (see `docker-entrypoint.sh`).

## Backups

The only stateful data living outside a container is:

- The `postgres_data` Docker volume (all application data).
- The `./uploads` directory (original uploaded files).

At minimum, cron a nightly `pg_dump`:

```bash
docker compose exec postgres pg_dump -U postgres ai_knowledge_assistant | gzip > "backup-$(date +%F).sql.gz"
```

...and copy `backup-*.sql.gz` plus `./uploads` off the server (e.g. to
object storage) on the same schedule.

## What's different from local dev

- `postgres`/`redis`/`api`/`frontend` are bound to `127.0.0.1` on the host
  in the base `docker-compose.yml` — never reachable from the internet
  directly, in dev or in prod.
- The production overlay adds `caddy`, the only internet-facing service
  (ports 80/443), which terminates TLS and reverse-proxies to `frontend`,
  which in turn proxies `/api/*` to `api` internally (`frontend/nginx.conf`)
  — the whole app is one HTTPS origin, so there's no CORS involved for
  normal browser traffic at all.
- `DEBUG=false` and a real `JWT_SECRET_KEY` are required — `app/main.py`
  refuses to boot with the default dev secret when `APP_ENV=production`.
