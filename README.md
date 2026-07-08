# Interview Management Platform

A full-stack interview management platform built with **React + Vite** (frontend) and **FastAPI + Python** (backend), connected to **MongoDB Atlas**.

---

## Repository Structure

```
interview-management/
├── frontend/   ← React 19 + Vite + TypeScript (deployed to Vercel)
└── backend/    ← FastAPI + Python 3.12+ (deployed to Render)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS v4 + shadcn/ui |
| Server State | TanStack Query v5 |
| Auth (client) | JWT in httpOnly cookie |
| Backend | FastAPI (Python 3.12+) |
| Validation | Pydantic v2 |
| ODM | Beanie (async MongoDB) |
| Database | MongoDB Atlas |
| Email | Resend |
| Frontend Host | Vercel |
| Backend Host | Render |

---

## Local Development Setup

### Prerequisites
- Node.js 18+
- Python 3.12+
- MongoDB Atlas account (free tier)
- Resend account (free tier — 3000 emails/month)

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd interview-management
```

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the env template and fill in your values:
```bash
cp .env.example .env
```

Edit `backend/.env`:
```
MONGODB_URL=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=interview_platform
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
RESEND_API_KEY=re_xxxxxxxxxxxx
FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
```

Start the backend:
```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
```

Edit `frontend/.env.local`:
```
VITE_API_URL=http://localhost:8000
```

Start the frontend:
```bash
npm run dev
```

Frontend available at: http://localhost:5173

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `MONGODB_URL` | MongoDB Atlas connection string |
| `DATABASE_NAME` | Database name (default: `interview_platform`) |
| `JWT_SECRET_KEY` | Secret key for JWT signing — use a long random string |
| `JWT_ALGORITHM` | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL in minutes (default: `480` = 8 hours) |
| `RESEND_API_KEY` | Resend API key for transactional email |
| `FROM_EMAIL` | Sender email address |
| `FRONTEND_URL` | Frontend origin for CORS (no trailing slash) |
| `ENVIRONMENT` | `development` or `production` (affects cookie SameSite/Secure) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API base URL |

---

## MongoDB Atlas Setup

1. Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a database user with read/write access
3. Under **Network Access**, add `0.0.0.0/0` (allow from anywhere — required for Render serverless)
4. Get your connection string: `mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/`
5. Set it as `MONGODB_URL` in your `.env`
6. The database and collections are created automatically by Beanie on first run

---

## Resend Email Setup

1. Sign up at [resend.com](https://resend.com) (free: 3000 emails/month)
2. Add and verify your domain (or use the sandbox domain for testing)
3. Create an API key and set it as `RESEND_API_KEY`
4. Set `FROM_EMAIL` to a verified address (e.g., `noreply@yourdomain.com`)

---

## Creating the First Admin User

Since there's no signup, the first Admin must be seeded manually. After setting up MongoDB, run this Python snippet from the `backend/` directory:

```python
import asyncio
from app.database import init_db
from app.models.user import User, Role
from app.utils.password import hash_password
from dotenv import load_dotenv

load_dotenv()

async def seed():
    await init_db()
    admin = User(
        name="Admin",
        email="admin@example.com",
        password=hash_password("Admin@1234"),
        role=Role.ADMIN,
        must_change_password=True,
    )
    await admin.insert()
    print("Admin created:", admin.email)

asyncio.run(seed())
```

Then log in with `admin@example.com` / `Admin@1234` and change your password.

---

## Deployment

### Frontend → Vercel

1. Push the repo to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
3. Set **Root Directory** to `frontend`
4. Add environment variable: `VITE_API_URL=https://your-backend.onrender.com`
5. Deploy

The `vercel.json` SPA rewrites are already configured.

### Backend → Render

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo
3. Set **Root Directory** to `backend`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables from the table above
7. Set `FRONTEND_URL` to your Vercel deployment URL (e.g., `https://interview-platform.vercel.app`)
8. Set `ENVIRONMENT=production`
9. Deploy

> **Important for cross-origin cookies:** In production, the backend sets cookies with `SameSite=None; Secure`. Your Vercel frontend and Render backend must both be on HTTPS.

---

## User Roles

| Role | Abilities |
|------|-----------|
| **Admin** | Create/manage all users, reset passwords, grant permissions |
| **Main Manager** | Create candidates, assign interviews, review feedback, make decisions |
| **Hiring Manager** | View assigned candidates, submit interview feedback |
