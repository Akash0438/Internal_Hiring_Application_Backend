# Interview Management Platform — Implementation Plan

## Top-Level Overview

Build a full-stack **Interview Management Platform** with a **React + Vite frontend** and a **FastAPI Python backend**, connected to **MongoDB Atlas** via **Beanie ODM**.

### Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| Forms | React Hook Form + Zod |
| Server State | TanStack Query (React Query v5) |
| Auth (client) | JWT stored in httpOnly cookie (set by backend) |
| Backend | FastAPI (Python 3.12+) |
| Validation | Pydantic v2 |
| ODM | Beanie (async MongoDB) |
| Database | MongoDB Atlas |
| Email | Resend API |
| Deployment | Vercel (frontend) + Render (backend) |

### Monorepo Layout
```
interview-management/
├── frontend/   ← React + Vite SPA (deployed to Vercel)
└── backend/    ← FastAPI app (deployed to Render)
```

### Scope Decisions (carried from original plan)
- Resume field = plain text URL only
- In-app notifications = full bell UI with unread count, dropdown, mark-as-read
- Password reset = Admin-only reset from User Management (no self-service)
- JWT stored in httpOnly cookie (backend sets `Set-Cookie`)
- Email provider = Resend

### Roles
| Role | Key Abilities |
|------|---------------|
| Admin | CRUD users, reset passwords, grant `can_create_main_managers` |
| Main Manager | Create candidates, assign interviews, review feedback, approve/reject/hold |
| Hiring Manager | View assigned candidates, submit interview feedback |

---

## Sub-Tasks

---

### Sub-Task 1 — Monorepo Scaffold & Environment Setup

**Status:** `[x] done`

**Intent**
Create the monorepo folder structure, scaffold the Vite React frontend, scaffold the FastAPI backend with virtual environment and dependencies, and create all environment template files.

**Expected Outcomes**
- `frontend/` and `backend/` directories exist at the workspace root
- Vite + React 19 + TypeScript frontend builds without errors (`npm run build`)
- FastAPI app starts without errors (`uvicorn app.main:app`)
- All env var keys documented in `.env.example` files for both frontend and backend
- `README.md` at root with setup instructions

**Todo List**

#### Frontend
1. `mkdir frontend && cd frontend`
2. Run `npm create vite@latest . -- --template react-ts`
3. Install dependencies:
   - `react-router-dom`
   - `@tanstack/react-query`
   - `axios`
   - `react-hook-form`
   - `@hookform/resolvers`
   - `zod`
   - `sonner` (toast notifications)
   - `lucide-react`
   - `clsx`
   - `tailwind-merge`
4. Install dev dependencies:
   - `tailwindcss`, `@tailwindcss/vite`, `autoprefixer`
5. Configure Tailwind: `tailwind.config.ts` with content paths `["./index.html", "./src/**/*.{ts,tsx}"]`
6. Run `npx shadcn@latest init` (New York style, Neutral base colour, CSS variables yes)
7. Add shadcn components: `button input label form card dialog dropdown-menu table badge avatar select textarea separator skeleton popover sheet alert alert-dialog tabs`
8. Create `frontend/.env.example`:
   ```
   VITE_API_URL=http://localhost:8000
   ```
9. Create `frontend/.env.local` with the same keys

#### Backend
10. `mkdir backend && cd backend`
11. Create Python virtual environment: `python -m venv .venv`
12. Create `backend/requirements.txt`:
    ```
    fastapi>=0.115
    uvicorn[standard]>=0.32
    beanie>=1.27
    pydantic[email]>=2.9
    pydantic-settings>=2.6
    python-jose[cryptography]>=3.3
    passlib[bcrypt]>=1.7
    python-multipart>=0.0.12
    resend>=2.0
    python-dotenv>=1.0
    email-validator>=2.2
    ```
13. Install: `pip install -r requirements.txt`
14. Create the full backend folder structure:
    ```
    backend/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── config.py
    │   ├── database.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── users.py
    │   │   ├── candidates.py
    │   │   ├── interviews.py
    │   │   ├── feedback.py
    │   │   └── notifications.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── user.py
    │   │   ├── candidate.py
    │   │   ├── interview_assignment.py
    │   │   ├── interview_feedback.py
    │   │   └── notification.py
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── user.py
    │   │   ├── candidate.py
    │   │   ├── interview.py
    │   │   └── feedback.py
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── auth_service.py
    │   │   ├── email_service.py
    │   │   └── notification_service.py
    │   ├── middleware/
    │   │   └── __init__.py
    │   └── utils/
    │       ├── __init__.py
    │       └── password.py
    ├── requirements.txt
    └── .env.example
    ```
15. Create `backend/.env.example`:
    ```
    MONGODB_URL=
    DATABASE_NAME=interview_platform
    JWT_SECRET_KEY=
    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=480
    RESEND_API_KEY=
    FROM_EMAIL=noreply@yourdomain.com
    FRONTEND_URL=http://localhost:5173
    ENVIRONMENT=development
    ```
16. Create `backend/.env` (copy of `.env.example`, values to be filled)

#### Root
17. Create root `README.md` with setup instructions for both frontend and backend

**Relevant Context**
- HLD §2 Project Structure
- Vite uses `VITE_` prefix for env vars exposed to the browser
- shadcn/ui with Vite requires manual Tailwind setup (no Next.js auto-config)

---

### Sub-Task 2 — Backend: MongoDB Models & Database Connection

**Status:** `[x] done`

**Intent**
Define all Beanie document models for the 5 collections and set up the async MongoDB connection with Beanie initialization in FastAPI's lifespan.

**Expected Outcomes**
- `app/database.py` initializes Beanie on app startup with all document models
- All 5 Beanie models defined with correct field types, validators, and enums
- `app/config.py` loads all settings from `.env` using `pydantic-settings`
- `app/main.py` bootstraps FastAPI with lifespan, CORS, and router registration

**Todo List**
1. Write `app/config.py` using `pydantic_settings.BaseSettings`:
   - Fields: `MONGODB_URL`, `DATABASE_NAME`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `RESEND_API_KEY`, `FROM_EMAIL`, `FRONTEND_URL`, `ENVIRONMENT`
   - Export `settings = Settings()`

2. Write `app/models/user.py`:
   ```python
   class Role(str, Enum): ADMIN / MAIN_MANAGER / HIRING_MANAGER
   class User(Document):
       name: str
       email: str  # Indexed, unique
       phone: Optional[str]
       password: str  # bcrypt hash
       role: Role
       must_change_password: bool = True
       can_create_main_managers: bool = False
       is_active: bool = True
       created_by_id: Optional[PydanticObjectId]
       created_at: datetime = Field(default_factory=datetime.utcnow)
       updated_at: datetime = Field(default_factory=datetime.utcnow)
       class Settings: name = "users"; indexes = [IndexModel([("email", 1)], unique=True)]
   ```

3. Write `app/models/candidate.py`:
   ```python
   class CandidateStatus(str, Enum): NEW/ASSIGNED/INTERVIEW_SCHEDULED/INTERVIEW_COMPLETED/FEEDBACK_SUBMITTED/UNDER_REVIEW/APPROVED/REJECTED/ON_HOLD
   class Candidate(Document):
       candidate_name: str
       email: str
       phone: Optional[str]
       position: str
       experience: Optional[str]
       resume_url: Optional[str]
       status: CandidateStatus = CandidateStatus.NEW
       created_by_id: PydanticObjectId
       created_at / updated_at: datetime
   ```

4. Write `app/models/interview_assignment.py`:
   ```python
   class AssignmentStatus(str, Enum): PENDING / IN_PROGRESS / COMPLETED
   class InterviewAssignment(Document):
       candidate_id: PydanticObjectId
       main_manager_id: PydanticObjectId
       hiring_manager_id: PydanticObjectId
       assigned_date: datetime
       status: AssignmentStatus = PENDING
   ```

5. Write `app/models/interview_feedback.py`:
   ```python
   class Recommendation(str, Enum): STRONGLY_RECOMMEND/RECOMMEND/NEUTRAL/DO_NOT_RECOMMEND
   class InterviewFeedback(Document):
       assignment_id: PydanticObjectId  # unique index
       rating: int  # 1–5
       strengths: list[str]
       weaknesses: list[str]
       recommendation: Recommendation
       notes: Optional[str]
       submitted_at: datetime
   ```

6. Write `app/models/notification.py`:
   ```python
   class Notification(Document):
       user_id: PydanticObjectId
       message: str
       is_read: bool = False
       created_at: datetime
   ```

7. Write `app/database.py`:
   - Async `init_db()` function using `motor.motor_asyncio.AsyncIOMotorClient`
   - Call `beanie.init_beanie(database, document_models=[User, Candidate, ...])`

8. Write `app/main.py`:
   - FastAPI app with `@asynccontextmanager` lifespan calling `init_db()`
   - CORS middleware: allow `FRONTEND_URL`, credentials=True, all methods/headers
   - Include all routers with `/api` prefix
   - Health check endpoint `GET /health`

**Relevant Context**
- HLD §10 MongoDB Collections
- Beanie requires `motor` as the async driver (it's a dependency of beanie)
- `PydanticObjectId` is Beanie's type for MongoDB `_id` fields
- CORS must allow credentials for httpOnly cookies to work cross-origin

---

### Sub-Task 3 — Backend: Authentication (JWT + httpOnly Cookie)

**Status:** `[x] done`

**Intent**
Implement full authentication: login with email/password, JWT issued as httpOnly cookie, `must_change_password` enforcement, password change endpoint, and FastAPI dependency for authenticated routes.

**Expected Outcomes**
- `POST /api/auth/login` validates credentials, sets `access_token` httpOnly cookie, returns user info
- `POST /api/auth/logout` clears the cookie
- `POST /api/auth/change-password` updates password, clears `must_change_password` flag
- `GET /api/auth/me` returns current user from cookie token
- `get_current_user` FastAPI dependency reads JWT from cookie and returns the User
- `require_role(roles)` dependency factory for RBAC enforcement
- Passwords hashed with bcrypt (passlib)
- Temporary passwords generated as 10-char random alphanumeric strings

**Todo List**
1. Write `app/utils/password.py`:
   - `hash_password(plain: str) -> str` using `passlib.context.CryptContext`
   - `verify_password(plain: str, hashed: str) -> bool`
   - `generate_temp_password(length=10) -> str` using `secrets.choice`

2. Write `app/services/auth_service.py`:
   - `create_access_token(data: dict) -> str` using `python-jose`
   - `decode_access_token(token: str) -> dict` — raises `HTTPException(401)` on failure
   - `get_current_user(request: Request) -> User` — reads `access_token` cookie, decodes JWT, fetches User from DB, checks `is_active`
   - `require_role(*roles: Role)` — returns a dependency that calls `get_current_user` and checks role

3. Write `app/schemas/auth.py`:
   - `LoginRequest`: `email: EmailStr`, `password: str`
   - `ChangePasswordRequest`: `new_password: str (min 8)`, `current_password: Optional[str]`
   - `UserResponse`: `id, name, email, role, must_change_password, can_create_main_managers`

4. Write `app/api/auth.py`:
   - `POST /login`:
     - Validate credentials, return 401 if wrong
     - Create JWT with `sub=user_id, role=role, must_change_password=flag`
     - Set `Set-Cookie: access_token=<jwt>; HttpOnly; SameSite=Lax; Path=/; Max-Age=<seconds>`
     - For production (ENVIRONMENT=production): also set `Secure` flag
     - Return `UserResponse`
   - `POST /logout`: delete cookie, return 200
   - `GET /me`: returns current user (uses `get_current_user` dependency)
   - `POST /change-password`:
     - If `must_change_password=True`: skip current password check, hash new, update DB, clear flag
     - If voluntary change: verify `current_password` first, then update

**Relevant Context**
- HLD §11 Authentication Flow
- HLD §16 Security (bcrypt, JWT, RBAC, force password change)
- httpOnly cookies require `response.set_cookie()` in FastAPI
- `SameSite=None` is needed for cross-origin cookie (Vercel frontend → Render backend)
- The cookie name `access_token` must match what the frontend's axios reads from

---

### Sub-Task 4 — Backend: User Management API

**Status:** `[x] done`

**Intent**
Build the User Management API endpoints that allow Admins to create, list, edit, deactivate, and reset passwords for users. Creating a user triggers a welcome email with a temporary password.

**Expected Outcomes**
- `GET /api/users` — Admin only, returns all users
- `POST /api/users` — Admin only, creates user with temp password, sends welcome email
- `PATCH /api/users/{id}` — Admin only, updates name/phone/role/is_active/can_create_main_managers
- `POST /api/users/{id}/reset-password` — Admin only, generates new temp password, sends email
- Welcome email and reset email sent via Resend API

**Todo List**
1. Write `app/schemas/user.py`:
   - `CreateUserRequest`: `name, email, phone?, role: Role`
   - `UpdateUserRequest`: all fields optional — `name?, phone?, role?, is_active?, can_create_main_managers?`
   - `UserListResponse`: paginated list with total count

2. Write `app/services/email_service.py`:
   - Initialize Resend client with `RESEND_API_KEY`
   - `send_welcome_email(to: str, name: str, temp_password: str)` — HTML email with login credentials
   - `send_password_reset_email(to: str, name: str, temp_password: str)`
   - `send_assignment_email(to: str, hiring_manager_name: str, candidate_name: str)`
   - `send_feedback_submitted_email(to: str, main_manager_name: str, candidate_name: str)`
   - `send_decision_email(to: str, hiring_manager_name: str, candidate_name: str, decision: str)`

3. Write `app/api/users.py`:
   - All routes protected with `require_role(Role.ADMIN)`
   - `GET /` — fetch all users, return list of `UserResponse`
   - `POST /` — validate, check email uniqueness, generate temp password, hash, create User, send welcome email
   - `PATCH /{id}` — partial update, return updated user
   - `POST /{id}/reset-password` — generate temp password, hash, update DB, set `must_change_password=True`, send email

4. Register `users` router in `app/main.py`

**Relevant Context**
- HLD §4 Admin responsibilities
- HLD §13 Email Flow
- HLD §15 Permission Matrix (Admin only)
- Resend Python SDK: `resend.Emails.send({...})`

---

### Sub-Task 5 — Backend: Candidate Management API

**Status:** `[x] done`

**Intent**
Build the Candidate Management API. Main Managers can create and edit candidates; all roles can view (scoped appropriately).

**Expected Outcomes**
- `GET /api/candidates` — Main Manager sees all they created; Hiring Manager sees only those assigned to them
- `POST /api/candidates` — Main Manager only
- `GET /api/candidates/{id}` — full detail with assignment history
- `PATCH /api/candidates/{id}` — Main Manager only
- Candidate status transitions managed by the assignment and feedback workflow (not directly editable)

**Todo List**
1. Write `app/schemas/candidate.py`:
   - `CreateCandidateRequest`: `candidate_name, email, phone?, position, experience?, resume_url?`
   - `UpdateCandidateRequest`: all optional
   - `CandidateResponse`: full candidate with status, created_by name

2. Write `app/api/candidates.py`:
   - `GET /` — role-scoped:
     - `MAIN_MANAGER`: all candidates where `created_by_id == current_user.id`
     - `HIRING_MANAGER`: candidates linked to their assignments (join with `interview_assignments`)
     - `ADMIN`: all (for visibility if needed — no create/edit)
   - `POST /` — `require_role(MAIN_MANAGER)` — create candidate, set `created_by_id`
   - `GET /{id}` — fetch candidate + its assignments + feedback
   - `PATCH /{id}` — `require_role(MAIN_MANAGER)` — update allowed fields only (not status directly)

3. Register `candidates` router

**Relevant Context**
- HLD §7 Candidate Management module
- HLD §14 Candidate Status Lifecycle (status changes happen via workflow endpoints, not direct PATCH)

---

### Sub-Task 6 — Backend: Interview Assignment API

**Status:** `[x] done`

**Intent**
Allow Main Managers to assign a Hiring Manager to a candidate, creating an `InterviewAssignment`, advancing the candidate status, and notifying the Hiring Manager.

**Expected Outcomes**
- `POST /api/interviews/assign` — creates assignment, updates candidate status to `ASSIGNED`, creates notification, sends email
- `GET /api/interviews/assigned` — role-scoped list of assignments
- `PATCH /api/interviews/{id}/reassign` — Main Manager only, updates `hiring_manager_id`, resets status to PENDING

**Todo List**
1. Write `app/schemas/interview.py`:
   - `AssignInterviewRequest`: `candidate_id: str, hiring_manager_id: str`
   - `ReassignRequest`: `hiring_manager_id: str`
   - `AssignmentResponse`: full assignment with candidate + manager names

2. Write `app/services/notification_service.py`:
   - `create_notification(user_id: PydanticObjectId, message: str) -> Notification`

3. Write `app/api/interviews.py`:
   - `POST /assign` — `require_role(MAIN_MANAGER)`:
     - Validate candidate exists and belongs to this manager
     - Check no active assignment already exists for this candidate
     - Create `InterviewAssignment`
     - Update `Candidate.status = ASSIGNED`
     - Create `Notification` for hiring manager
     - Send assignment email (non-blocking — use `asyncio.create_task`)
   - `GET /assigned` — role-scoped:
     - `MAIN_MANAGER`: assignments where `main_manager_id == current_user.id`
     - `HIRING_MANAGER`: assignments where `hiring_manager_id == current_user.id`
   - `PATCH /{id}/reassign` — `require_role(MAIN_MANAGER)` — update hiring manager, notify new HM

4. Register `interviews` router

**Relevant Context**
- HLD §12 Interview Assignment Sequence
- Status transition: `NEW → ASSIGNED`

---

### Sub-Task 7 — Backend: Feedback API & Hiring Decision

**Status:** `[x] done`

**Intent**
Allow Hiring Managers to submit structured interview feedback, and Main Managers to make the final hiring decision (Approve / Reject / On Hold).

**Expected Outcomes**
- `POST /api/feedback` — Hiring Manager only, creates feedback, advances statuses, notifies Main Manager
- `GET /api/feedback/{assignment_id}` — accessible to the submitting HM and the Main Manager
- `POST /api/candidates/{id}/decision` — Main Manager only, sets final status, notifies HM

**Todo List**
1. Write `app/schemas/feedback.py`:
   - `CreateFeedbackRequest`: `assignment_id, rating (1-5), strengths: list[str], weaknesses: list[str], recommendation, notes?`
   - `DecisionRequest`: `decision: Literal["APPROVED", "REJECTED", "ON_HOLD"]`
   - `FeedbackResponse`: full feedback with assignment and candidate context

2. Write `app/api/feedback.py`:
   - `POST /` — `require_role(HIRING_MANAGER)`:
     - Verify assignment belongs to this HM and has no existing feedback
     - Create `InterviewFeedback`
     - Update `InterviewAssignment.status = COMPLETED`
     - Update `Candidate.status = FEEDBACK_SUBMITTED`
     - Create `Notification` for Main Manager
     - Send feedback-submitted email to Main Manager
   - `GET /{assignment_id}` — accessible to HM (owner) or Main Manager of the candidate

3. Add decision endpoint to `app/api/candidates.py`:
   - `POST /{id}/decision` — `require_role(MAIN_MANAGER)`:
     - Update `Candidate.status` to `APPROVED`, `REJECTED`, or `ON_HOLD`
     - Create `Notification` for the Hiring Manager who submitted feedback
     - Send decision email to Hiring Manager

4. Register `feedback` router

**Relevant Context**
- HLD §14 Candidate Status Lifecycle
- Status transitions: `FEEDBACK_SUBMITTED → UNDER_REVIEW` (implicit on HM view) → `APPROVED/REJECTED/ON_HOLD`

---

### Sub-Task 8 — Backend: Notifications API

**Status:** `[x] done`

**Intent**
Provide endpoints for in-app notifications: list unread, list all, mark as read.

**Expected Outcomes**
- `GET /api/notifications` — returns current user's notifications (newest first), optional `?unread_only=true`
- `PATCH /api/notifications/{id}/read` — marks a notification as read
- `PATCH /api/notifications/read-all` — marks all current user's notifications as read

**Todo List**
1. Write `app/api/notifications.py`:
   - All routes use `get_current_user` dependency
   - `GET /` — filter by `user_id=current_user.id`, sort `-created_at`, limit 50
   - Add `?unread_only=true` query param for bell badge count
   - `PATCH /{id}/read` — set `is_read=True`
   - `PATCH /read-all` — bulk update all unread for user
2. Register `notifications` router

**Relevant Context**
- Plan scope: full bell with unread count, dropdown, mark-as-read, polled on page load

---

### Sub-Task 9 — Frontend: Project Setup & Auth Shell

**Status:** `[x] done`

**Intent**
Configure the Vite React frontend: routing, TanStack Query, Axios with cookie credentials, auth context, login page, change-password page, and route guards.

**Expected Outcomes**
- React Router DOM routes configured for all pages
- `AuthContext` provides `user`, `login()`, `logout()`, `isLoading`
- Axios instance configured with `withCredentials: true` and base URL from `VITE_API_URL`
- Login page (`/login`) calls `POST /api/auth/login`, stores user in context
- Change-password page (`/change-password`) called on first login (`must_change_password=true`)
- `ProtectedRoute` component redirects unauthenticated users to `/login`
- `RoleGuard` component redirects users without the required role to `/dashboard`

**Todo List**
1. Configure `frontend/src/main.tsx`:
   - Wrap app in `QueryClientProvider`, `BrowserRouter`, `AuthProvider`

2. Create `frontend/src/lib/axios.ts`:
   - Axios instance with `baseURL: import.meta.env.VITE_API_URL`
   - `withCredentials: true` (required for cookie auth)
   - Response interceptor: on 401, clear auth context and redirect to `/login`

3. Create `frontend/src/context/AuthContext.tsx`:
   - State: `user: UserResponse | null`, `isLoading: boolean`
   - On mount: call `GET /api/auth/me` to restore session
   - `login(email, password)` → POST to `/api/auth/login`
   - `logout()` → POST to `/api/auth/logout`, clear user state

4. Create `frontend/src/types/index.ts`:
   - TypeScript interfaces mirroring all backend schemas

5. Create `frontend/src/pages/LoginPage.tsx`:
   - React Hook Form + Zod (email required, password min 1)
   - On success: if `must_change_password` → navigate to `/change-password`, else `/dashboard`
   - Error toast on failure

6. Create `frontend/src/pages/ChangePasswordPage.tsx`:
   - Zod: `new_password min 8`, confirm match
   - POST to `/api/auth/change-password`, on success navigate to `/dashboard`

7. Create `frontend/src/components/ProtectedRoute.tsx`:
   - If not authenticated → redirect to `/login`
   - If `must_change_password` → redirect to `/change-password`

8. Create `frontend/src/components/RoleGuard.tsx`:
   - Takes `allowedRoles: string[]`, redirects to `/dashboard` if role not allowed

9. Configure `frontend/src/App.tsx` with React Router routes:
   - Public: `/login`, `/change-password`
   - Protected (inside `ProtectedRoute`): `/dashboard`, `/candidates`, `/candidates/:id`, `/assignments`, `/feedback/:assignmentId`, `/users`, `/profile`

**Relevant Context**
- `withCredentials: true` is essential for cross-origin httpOnly cookies
- SameSite=None + Secure required on backend cookie for Vercel → Render cross-origin calls

---

### Sub-Task 10 — Frontend: Layout Shell & Dashboard

**Status:** `[x] done`

**Intent**
Build the authenticated application shell: sidebar navigation, header with notification bell and user menu, and the main dashboard page with stat cards.

**Expected Outcomes**
- `DashboardLayout` component wraps all protected pages with sidebar + header
- Sidebar shows role-appropriate navigation links
- Header shows notification bell (unread badge + dropdown) and user avatar dropdown
- `/dashboard` page shows stat cards for assigned/pending/completed interviews and candidate statuses

**Todo List**
1. Create `frontend/src/layouts/DashboardLayout.tsx`:
   - Compose `Sidebar` + `Header` + `<Outlet />` (React Router)

2. Create `frontend/src/components/layout/Sidebar.tsx`:
   - Links conditional on `user.role`:
     - Admin: Dashboard, Users
     - Main Manager: Dashboard, Candidates, Assignments
     - Hiring Manager: Dashboard, Assignments
   - All roles: Profile

3. Create `frontend/src/components/layout/Header.tsx`:
   - `NotificationBell`: useQuery polling `GET /api/notifications?unread_only=true`, badge count, dropdown with mark-as-read
   - User avatar dropdown: name, role badge, Profile, Logout

4. Create `frontend/src/services/api.ts`:
   - Typed API wrapper functions for all endpoints (auth, users, candidates, interviews, feedback, notifications)

5. Create `frontend/src/pages/DashboardPage.tsx`:
   - useQuery for stats (candidate counts by status, assignment counts)
   - Render `StatCard` components

6. Create `frontend/src/components/dashboard/StatCard.tsx`

**Relevant Context**
- TanStack Query `useQuery` for data fetching; `useMutation` for write operations
- Notification bell polls every 30s using `refetchInterval`

---

### Sub-Task 11 — Frontend: User Management Page (Admin)

**Status:** `[x] done`

**Intent**
Build the Admin's User Management UI: list users, create user modal, edit user modal, toggle active status, reset password, and toggle `can_create_main_managers`.

**Expected Outcomes**
- `/users` page lists all users in a shadcn table with role badge, active status, actions
- Create User modal: RHF + Zod form, submits to `POST /api/users`
- Edit User modal: pre-filled form, submits to `PATCH /api/users/{id}`
- Reset Password button calls `POST /api/users/{id}/reset-password` and shows toast
- Toggle `can_create_main_managers` visible for Main Manager rows only

**Todo List**
1. Create `frontend/src/pages/UsersPage.tsx` — `RoleGuard allowedRoles={["ADMIN"]}`
2. Create `frontend/src/components/users/UsersTable.tsx`
3. Create `frontend/src/components/users/CreateUserModal.tsx`
4. Create `frontend/src/components/users/EditUserModal.tsx`
5. Wire all mutations with `useMutation` + toast feedback + query invalidation

---

### Sub-Task 12 — Frontend: Candidate Management Page

**Status:** `[x] done`

**Intent**
Build the Candidate Management UI for Main Managers (create, edit, view) with a candidate detail page showing full profile, assignment history, and feedback.

**Expected Outcomes**
- `/candidates` page: table with status badge, position, actions (role-scoped)
- Create Candidate modal (Main Manager only)
- Edit Candidate modal (Main Manager only)
- `/candidates/:id` detail page: profile + assignment history + feedback view + decision buttons

**Todo List**
1. Create `frontend/src/pages/CandidatesPage.tsx`
2. Create `frontend/src/components/candidate/CandidatesTable.tsx`
3. Create `frontend/src/components/candidate/CreateCandidateModal.tsx`
4. Create `frontend/src/components/candidate/EditCandidateModal.tsx`
5. Create `frontend/src/pages/CandidateDetailPage.tsx`:
   - Tabs: Profile | Assignments | Feedback
   - Decision buttons (Approve/Reject/On Hold) visible when status is `FEEDBACK_SUBMITTED` or `UNDER_REVIEW` and role is Main Manager

---

### Sub-Task 13 — Frontend: Assignments & Feedback Pages

**Status:** `[x] done`

**Intent**
Build the assignments list page (role-scoped) and the feedback form/view page.

**Expected Outcomes**
- `/assignments` page: table scoped by role — Main Manager sees all their assignments; Hiring Manager sees their own
- Assign Interview modal on Candidates page: select Hiring Manager, confirm
- `/feedback/:assignmentId` page: Hiring Manager sees a form to submit; Main Manager and HM see read-only view after submission

**Todo List**
1. Create `frontend/src/pages/AssignmentsPage.tsx`
2. Create `frontend/src/components/interview/AssignmentsTable.tsx`
3. Create `frontend/src/components/interview/AssignInterviewModal.tsx`
4. Create `frontend/src/pages/FeedbackPage.tsx`:
   - If no feedback and user is HM and assignment is theirs → show `FeedbackForm`
   - Else → show `FeedbackView`
5. Create `frontend/src/components/interview/FeedbackForm.tsx` — RHF + Zod
6. Create `frontend/src/components/interview/FeedbackView.tsx`

---

### Sub-Task 14 — Frontend: Profile Page

**Status:** `[x] done`

**Intent**
Give every user a profile page showing their info and a voluntary password change form.

**Expected Outcomes**
- `/profile` page shows name, email, phone, role, joined date
- Change Password section: current password + new password + confirm, submits to `POST /api/auth/change-password`

**Todo List**
1. Create `frontend/src/pages/ProfilePage.tsx`
2. Create `frontend/src/components/forms/ChangePasswordForm.tsx`

---

### Sub-Task 15 — Deployment Configuration

**Status:** `[x] done`

**Intent**
Prepare both apps for production deployment: Vercel for the frontend, Render for the FastAPI backend.

**Expected Outcomes**
- `frontend/vercel.json` configured with SPA fallback (`rewrites`)
- `backend/render.yaml` (Render Blueprint) with start command and env var keys
- `backend/Procfile` as fallback: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Root `README.md` updated with full deployment instructions
- `.env.example` files complete and accurate
- CORS production origins set correctly (Vercel URL in `FRONTEND_URL`)

**Todo List**
1. Create `frontend/vercel.json`:
   ```json
   { "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
   ```
2. Create `backend/render.yaml` (Render Blueprint):
   ```yaml
   services:
     - type: web
       name: interview-platform-api
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
       envVars: (all keys listed)
   ```
3. Create `backend/Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Update root `README.md` with:
   - Local dev setup
   - MongoDB Atlas setup (free tier, allow all IPs)
   - Resend API key setup
   - Vercel frontend deploy steps
   - Render backend deploy steps
   - CORS gotcha: `FRONTEND_URL` must match exact Vercel URL; backend cookie must use `SameSite=None; Secure`

**Relevant Context**
- Render auto-detects Python apps; `render.yaml` is optional but recommended
- Vercel SPA rewrites prevent 404 on page refresh for React Router routes
- For cross-origin cookies: backend must set `SameSite=None; Secure` in production; Axios must send `withCredentials: true`

---

## Implementation Order

```
Sub-Task 1  (Scaffold)
    ↓
Sub-Task 2  (DB Models)  →  Sub-Task 3  (Auth API)
    ↓
Sub-Task 4  (Users API)  →  Sub-Task 5  (Candidates API)
    ↓
Sub-Task 6  (Interviews API)  →  Sub-Task 7  (Feedback + Decision API)
    ↓
Sub-Task 8  (Notifications API)
    ↓
Sub-Task 9  (Frontend Auth Shell)  →  Sub-Task 10  (Layout + Dashboard)
    ↓
Sub-Task 11 (Users UI)  →  Sub-Task 12 (Candidates UI)
    ↓
Sub-Task 13 (Assignments + Feedback UI)  →  Sub-Task 14 (Profile UI)
    ↓
Sub-Task 15 (Deployment)
```

Backend sub-tasks (1–8) must complete before frontend sub-tasks (9–14) since the frontend depends on the API contract.
