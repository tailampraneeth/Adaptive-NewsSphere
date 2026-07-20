# Heimdall Deployment Guide (Consumer Edition)

This document provides step-by-step instructions to deploy Heimdall using free-tier cloud services: **Neon** (database), **Render** (backend api), **Vercel** (frontend), and **GitHub Actions** (schedulers).

---

## 1. Database Setup: Neon (Free Tier)
1. Go to [Neon.tech](https://neon.tech/) and sign up for a free account.
2. Create a new project named `heimdall`.
3. Choose **PostgreSQL 16** (or latest).
4. Copy the connection string. It will look like this:
   `postgresql://developer:password@ep-cool-snowflake-123456.us-east-2.aws.neon.tech/neondb?sslmode=require`
5. Note down this URL. You will need to replace the driver scheme `postgresql://` with `postgresql+asyncpg://` when setting the backend environment variable.

---

## 2. API Backend Setup: Render (Free Tier)
1. Go to [Render.com](https://render.com/) and register.
2. Click **New** -> **Web Service**.
3. Connect your GitHub repository containing the Heimdall codebase.
4. Configure the web service properties:
   - **Name:** `heimdall-api`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
5. In the **Environment Variables** tab, add the following parameters:
   - `POSTGRES_USER`: *Your Neon username*
   - `POSTGRES_PASSWORD`: *Your Neon password*
   - `POSTGRES_HOST`: *Your Neon hostname (e.g. ep-cool-snowflake-123456.us-east-2.aws.neon.tech)*
   - `POSTGRES_PORT`: `5432`
   - `POSTGRES_DB`: `neondb`
   - `DATABASE_URL`: *Your asyncpg Neon URL (e.g. postgresql+asyncpg://...)*
   - `INGEST_SECRET`: *A secure long random token*
   - `GEMINI_API_KEY`: *Your Google AI Studio API key (free tier)*
   - `JWT_SECRET`: *A secure random secret key*
   - `SMTP_HOST`: *SMTP server hostname (optional; logs to console if empty)*
   - `SMTP_PORT`: `587`
   - `SMTP_USER`: *SMTP account username*
   - `SMTP_PASSWORD`: *SMTP account password*
   - `SMTP_FROM_EMAIL`: *Sender display email header*
   - `FRONTEND_URL`: *Your Vercel deployment URL (e.g. https://heimdall.vercel.app)*
6. Click **Deploy Web Service**.
7. Copy the URL of your deployed service (e.g. `https://heimdall-api.onrender.com`).

---

## 3. Frontend Setup: Vercel (Free Tier)
1. Go to [Vercel.com](https://vercel.com/) and link your GitHub account.
2. Select **Add New** -> **Project**.
3. Import the Heimdall repository.
4. Configure the build parameters:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
5. Click **Deploy**. Vercel will build the frontend assets and automatically apply the SPA routing rewrites specified in `vercel.json`.

---

## 4. Automation Schedulers: GitHub Actions
We use GitHub Actions to trigger RSS feed ingestion and AI story summarizations automatically at regular intervals.

1. Go to your repository settings in GitHub.
2. Select **Settings** -> **Secrets and variables** -> **Actions**.
3. Add the following repository secrets:
   - `HEIMDALL_API_URL`: *Your Render backend URL (e.g., `https://heimdall-api.onrender.com`)*
   - `INGEST_SECRET`: *The exact same secret key you specified in Render environment variables*
4. Enable GitHub Actions in the **Actions** tab of your repository.
5. Ingestion will run every 30 minutes, and Summarizations will run 10 minutes later.
