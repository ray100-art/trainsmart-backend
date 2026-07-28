# National / high-volume readiness

This stack can serve a national MoH registry when deployed on proper infrastructure.
Free Vercel/Render/Neon is for demos only.

## What was hardened in code

- Scale indexes (people active/county, certificate pipeline, rate-limit composite, optional `pg_trgm`)
- Certificate verify: joinedload + in-process TTL cache + short HTTP cache headers
- CSRF protection for cookie auth (header + cookie; CORS exposes `X-CSRF-Token`)
- Forgot-password + login IP rate limits
- DB statement / idle-in-transaction timeouts
- Certificate pipeline N+1 fixes; batched cert email user lookup
- Paginated Users / Facilities admin lists
- GitHub Actions CI (pytest / frontend build)

## Required for millions-scale go-live (ops)

1. **Leave free tier** — MoH VM/k8s or paid cloud with always-on API workers
2. **PostgreSQL + PgBouncer** — size `workers × (pool_size + max_overflow)` under `max_connections`
3. **Run migrations** — `alembic upgrade head` (includes `010_scale_indexes`)
4. **Same-origin preferred** — `nhcsc.nascop.org` serving FE+API (Stronger cookies than Vercel↔Render)
5. **Redis (next)** — shared verify cache + rate limits across workers
6. **Backups + monitoring** — Postgres PITR, uptime checks, error tracking (e.g. Sentry)
7. **Bulk people migration** — background job beyond 2k CSV batches for the legacy registry

## Env tips

See `deploy/env.production.example` for pool sizing and cookie settings.
