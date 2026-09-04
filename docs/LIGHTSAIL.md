# Amazon Lightsail deployment and restore runbook

## Live Production Deployment

- **Region & AZ:** Canada Central (`ca-central-1a` — Montreal)
- **Static IP:** `15.175.60.199`
- **Live URL:** `https://15.175.60.199.sslip.io`
- **Instance Plan:** `small_3_0` (2 GB Physical RAM / 2 vCPUs / 60 GB NVMe SSD + 2 GB Swap)
- **Ingress Ports:** TCP 22 (SSH), TCP 80 (HTTP), TCP 443 (HTTPS), UDP 443 (HTTP/3)
- **Private Internal Networks:** PostgreSQL 16 (`postgres:5432`), NATS JetStream (`nats:4222`), FastAPI API (`api:8000`), Next.js (`web:3000`)

## Host preparation & operations

- Ubuntu 24.04 LTS host running Docker Engine 29.8 and Compose v5.5.
- Caddy reverse proxy automatically obtains and renews Let's Encrypt TLS/SSL certificates.
- Multi-container topology defined in `compose.lightsail.yml`.

```bash
docker compose --env-file .env.local -f compose.lightsail.yml config
docker compose --env-file .env.local -f compose.lightsail.yml up -d --build
docker compose --env-file .env.local -f compose.lightsail.yml ps
curl https://15.175.60.199.sslip.io/health/ready
```

## Backups

Run from a protected administrator shell and store the resulting encrypted archive outside the instance:

```bash
docker compose --env-file .env.local -f compose.lightsail.yml exec -T postgres pg_dump -U alphadesk -Fc alphadesk > alphadesk-$(date +%Y%m%d).dump
```

Back up `.env.local` separately in a secrets manager. A database backup without the matching credential master-key version cannot decrypt BYOK records.

## Restore drill

Restore into a new empty PostgreSQL volume, never over the active database:

```bash
docker compose --env-file .env.local -f compose.lightsail.yml exec -T postgres createdb -U alphadesk alphadesk_restore
docker compose --env-file .env.local -f compose.lightsail.yml exec -T postgres pg_restore -U alphadesk -d alphadesk_restore --clean --if-exists < alphadesk-YYYYMMDD.dump
```

Validate row counts, invitation state, credential metadata, and migrations before switching application traffic. Never log or export decrypted provider secrets during a restore test.
