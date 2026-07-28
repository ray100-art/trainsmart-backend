# Free staging deployment (Neon + Render + Vercel)

Use this for **demos and testing only** — not NASCOP national production.

| Service | Role | Free tier |
|---------|------|-----------|
| [Neon](https://neon.tech) | PostgreSQL | 512 MB storage |
| [Render](https://render.com) | FastAPI backend | Sleeps after 15 min idle |
| [Vercel](https://vercel.com) | React frontend | Generous free tier |

---

## Step 1 — Push code to GitHub

Create **two repos** (or one monorepo with subfolders):

- `trainsmart-backend` → contents of `C:\transmart-backend`
- `trainsmart-frontend` → contents of `C:\trainsmart-frontend`

**Never commit `.env`** — secrets go in hosting dashboards only.

---

## Step 2 — Neon (database)

1. Sign up at https://neon.tech
2. **New Project** → name: `trainsmart-staging`
3. Copy the **connection string** (PostgreSQL)
4. Ensure it ends with `?sslmode=require` if not already included

Example:
```
postgresql://user:password@ep-xxxx.eu-west-2.aws.neon.tech/neondb?sslmode=require
```

---

## Step 3 — Render (backend)

1. Sign up at https://render.com → **New → Blueprint** or **Web Service**
2. Connect your **backend** GitHub repo
3. Render detects `render.yaml` automatically, or set manually:

| Setting | Value |
|---------|-------|
| **Root directory** | `.` (repo root) |
| **Build command** | `pip install -r requirements.txt && alembic upgrade head && python seed.py` |
| **Start command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health check** | `/health` |

4. **Environment variables** (Render dashboard → Environment):

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Neon connection string from Step 2 |
| `SECRET_KEY` | Run: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ENVIRONMENT` | `production` |
| `EMAIL_ENABLED` | `false` |
| `RATE_LIMIT_STORAGE` | `database` |
| `ALLOWED_ORIGINS` | `https://YOUR-APP.vercel.app` (set after Step 4; no trailing slash) |
| `FRONTEND_URL` | `https://YOUR-APP.vercel.app` |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `none` |

> **Why `COOKIE_SAMESITE=none`?** The site on Vercel and the API on Render are different domains. Browsers only send the login cookie across domains when the cookie is `SameSite=None; Secure`. For a future same-domain MoH deploy (`nhcsc.nascop.org`), use `COOKIE_SAMESITE=lax` instead.

5. Deploy → note your API URL, e.g. `https://trainsmart-api.onrender.com`

6. **First deploy only:** `seed.py` writes admin credentials to `.admin_credentials` (not to logs). On Render, set `ADMIN_CREDENTIALS_FILE` to a writable path or download/open that file from the instance once, then delete it. Change the password after first login.

7. Test: `https://trainsmart-api.onrender.com/health` → `{"status":"healthy"}`

> **Cold starts:** Free Render sleeps when idle. First request after ~15 min may take 30–60 seconds.

---

## Step 4 — Vercel (frontend)

1. Sign up at https://vercel.com → **Add New Project**
2. Import your **frontend** GitHub repo
3. Framework preset: **Vite**

| Setting | Value |
|---------|-------|
| **Build command** | `npm run build` |
| **Output directory** | `dist` |

4. **Environment variable:**

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://trainsmart-api.onrender.com/api/v1` |

5. Deploy → note URL, e.g. `https://trainsmart-frontend.vercel.app`

6. Go back to **Render** → update `ALLOWED_ORIGINS` and `FRONTEND_URL` with your Vercel URL → redeploy backend.

---

## Step 5 — Log in

- URL: your Vercel link
- Username: `admin`
- Password: from `.admin_credentials` on first `seed.py` run (never printed to logs) or reset via a new seed on a fresh DB

---

## Updating after code changes

- Push to GitHub → Render and Vercel auto-redeploy
- New migrations run automatically on Render build (`alembic upgrade head`)

---

## Limitations (free tier)

- API sleeps when idle (slow wake-up)
- Not suitable for MOH national go-live
- Neon storage cap (~512 MB)
- No custom domain on some free plans without extra setup
- Change default admin password immediately after first login

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| CORS error in browser | `ALLOWED_ORIGINS` must exactly match Vercel URL (no trailing slash) |
| Login then kicked back to login | On Render set `COOKIE_SAMESITE=none`, `COOKIE_SECURE=true`, and `ALLOWED_ORIGINS` to your Vercel URL, then redeploy API |
| 401 after page refresh | Fixed in frontend — redeploy latest frontend |
| `health` unhealthy | Check `DATABASE_URL` and Neon project is active |
| Build fails on seed | Check Render logs; re-run deploy |
