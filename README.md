# Smart API Health Monitoring System

> A production-ready, full-stack API monitoring dashboard built as a BCA final-year project.

---

## Overview

The Smart API Health Monitoring System continuously polls registered HTTP endpoints, records their status and response times, and presents the data on a live web dashboard. It supports full user registration and login, persists all data in MySQL (with automatic SQLite fallback), and sends email alerts when an API fails repeatedly or responds slowly.

---

## Features

| Feature | Description |
|---|---|
| **User Registration** | Create accounts at `/register` — server validates email format, minimum 8-char password, and duplicate check |
| **Secure Login** | Session-based authentication; passwords stored as bcrypt hashes via Werkzeug |
| **Auto-seeded Admin** | `admin@example.com / Admin@123` is created automatically on first run |
| **Persistent DB Connection** | One reusable connection per engine with automatic reconnect on failure |
| **MySQL + SQLite Fallback** | Uses MySQL when available; falls back to SQLite with zero config required |
| **Continuous API Polling** | APScheduler checks every API at its own configurable interval (≥ 5 s) |
| **Intelligent State Detection** | States: `OK`, `SLOW` (response > threshold), `FAIL` (HTTP error / timeout), `PENDING` |
| **Premium Light UI** | Modern glassmorphism interface with smooth animations and vibrant accents |
| **Email Alerts** | SMTP email sent after 3 consecutive failures or a sustained slow response |
| **Live Dashboard** | Cards auto-refresh every 5 seconds without page reload |
| **Response Time Chart** | Chart.js line graph showing historical latency per API |
| **XSS Protection** | All user-supplied API names are HTML-escaped before rendering |
| **Route Protection** | All `/api/*` endpoints return `401` without a valid session; frontend auto-redirects |

---

## Project Structure

```
project/
├── backend/
│   ├── app.py                # Flask app — all routes and auth endpoints
│   ├── db.py                 # Database layer — persistent connection pool, all queries
│   ├── scheduler.py          # APScheduler background polling loop
│   ├── alert.py              # SMTP email alerting
│   ├── config.py             # Configuration (env-variable aware)
│   ├── requirements.txt      # Python dependencies (direct only)
│   └── test_auth_smoke.py    # 12 automated smoke tests
│
├── frontend/
│   ├── index.html            # Login page
│   ├── register.html         # Registration page
│   ├── dashboard.html        # Monitoring dashboard
│   ├── styles.css            # Design system (premium light theme + glassmorphism + animations)
│   └── script.js             # All client-side logic (auth, CRUD, chart)
│
├── database/
│   └── schema.sql            # Reference MySQL schema (auto-applied by backend)
│
├── data/
│   └── api_health_monitor.db # SQLite database file (auto-created if MySQL absent)
│
└── logs/
    └── logs.csv              # CSV backup log of every API check (auto-created)
```

---

## Prerequisites

- **Python 3.8 or later**
- **MySQL Server** *(optional)* — XAMPP, MySQL Workbench, or any local instance.  
  If MySQL is not running the backend automatically uses SQLite — no extra setup needed.

---

## Setup & Running

### 1 — Install dependencies

Open a terminal and run:

```bash
cd "d:\bca project\project\backend"
pip install -r requirements.txt
```

### 2 — (Optional) Configure MySQL

Edit `backend/config.py` or set the corresponding environment variables:

```python
DB_ENGINE   = "auto"          # "auto" | "mysql" | "sqlite"
DB_HOST     = "localhost"
DB_USER     = "root"
DB_PASSWORD = ""              # your MySQL root password
DB_NAME     = "api_health_monitor"
```

> **Tip:** If `DB_ENGINE = "auto"` (the default), the backend tries MySQL first and silently falls back to SQLite if the connection fails.

### 3 — Start the server

```bash
python app.py
```

Expected startup output:

```
[WARN] MySQL unavailable (...), falling back to SQLite.   # only if MySQL not running
[OK] Database initialised -- SQLite at ...data/api_health_monitor.db.
[OK] Default admin account created: admin@example.com     # only on very first run
Scheduler started.
* Running on http://127.0.0.1:5000
```

### 4 — Open in browser

| URL | Purpose |
|---|---|
| `http://localhost:5000/` | **Login** page |
| `http://localhost:5000/register` | **Register** a new account |
| `http://localhost:5000/dashboard` | **Dashboard** (redirects to login if not authenticated) |

**Default admin credentials:**

```
Email:    admin@example.com
Password: Admin@123
```

---

## Authentication Flows

```
Register:   POST /api/auth/register  →  auto-login  →  /dashboard
Login:      POST /api/auth/login     →  set session →  /dashboard
Dashboard:  GET  /api/auth/session   →  401?         →  redirect /
Logout:     POST /api/auth/logout    →  clear session→  /
```

### Password rules (enforced on both client and server)

- Valid email address format
- Minimum **8 characters**
- Passwords must match the confirmation field
- Duplicate email → HTTP **409 Conflict**

---

## API Endpoints Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/auth/session` | No | Check current session |
| `POST` | `/api/auth/register` | No | Create new user account |
| `POST` | `/api/auth/login` | No | Login with email + password |
| `POST` | `/api/auth/logout` | No | Destroy session |
| `GET` | `/api/apis` | Yes | List all registered APIs |
| `POST` | `/api/add_api` | Yes | Add new API to monitor |
| `DELETE` | `/api/delete_api/<id>` | Yes | Remove API and its logs |
| `GET` | `/api/get_status` | Yes | Current status of all APIs |
| `GET` | `/api/logs/<id>` | Yes | Last 20 log entries for an API |

**`POST /api/auth/register` body:**

```json
{
  "email": "you@example.com",
  "password": "SecurePass99!",
  "confirm_password": "SecurePass99!"
}
```

**`POST /api/add_api` body:**

```json
{
  "name": "My Service",
  "url": "https://api.example.com/health",
  "interval": 60,
  "threshold": 1000
}
```

---

## Running Tests

```bash
cd "d:\bca project\project\backend"
python -m pytest test_auth_smoke.py -v
```

### Test coverage (12 tests, all passing)

| Test | What it verifies |
|---|---|
| `test_protected_route_requires_authentication` | `/api/get_status` returns 401 without session |
| `test_protected_apis_list_requires_authentication` | `/api/apis` returns 401 without session |
| `test_seeded_user_can_log_in_and_access_dashboard_data` | Admin login + dashboard data access |
| `test_invalid_password_is_rejected` | Wrong password → 401 |
| `test_missing_fields_rejected_on_login` | Missing fields → 400 |
| `test_new_user_can_register` | Registration returns 201 |
| `test_register_duplicate_email_returns_409` | Duplicate email → 409 |
| `test_register_mismatched_passwords_returns_400` | Mismatched passwords → 400 |
| `test_register_short_password_returns_400` | Password < 8 chars → 400 |
| `test_register_invalid_email_returns_400` | Bad email format → 400 |
| `test_registered_user_can_log_in` | End-to-end: register → login |
| `test_logout_clears_session` | Logout → next request returns 401 |

---

## Email Alerting (optional)

Configure SMTP in `config.py` or via environment variables:

```python
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"   # Google App Password recommended
ALERT_RECEIVER = "alerts@example.com"
```

Alert triggers:
- **FAIL** — 3 consecutive check failures (connection error or non-2xx HTTP status)
- **SLOW** — response time exceeds the configured threshold (ms)
- Alerts reset automatically when the API recovers

---

## Environment Variables

Every config value can be overridden without editing any file:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-this-secret-key` | Flask session signing key |
| `DB_ENGINE` | `auto` | `auto` \| `mysql` \| `sqlite` |
| `DB_HOST` | `localhost` | MySQL hostname |
| `DB_USER` | `root` | MySQL username |
| `DB_PASSWORD` | *(empty)* | MySQL password |
| `DB_NAME` | `api_health_monitor` | MySQL database name |
| `DEFAULT_ADMIN_EMAIL` | `admin@example.com` | Email for the seeded admin account |
| `DEFAULT_ADMIN_PASSWORD` | `Admin@123` | Password for the seeded admin account |
| `SMTP_SERVER` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | *(placeholder)* | SMTP login email |
| `SMTP_PASSWORD` | *(placeholder)* | SMTP app password |
| `ALERT_RECEIVER` | `admin@example.com` | Email address to receive alerts |

**Example — use MySQL and a custom secret key:**

```bash
set SECRET_KEY=my-production-secret
set DB_ENGINE=mysql
set DB_PASSWORD=rootpassword
python app.py
```

---

## Database Schema

```sql
CREATE TABLE users (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE apis (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    name             VARCHAR(255) NOT NULL,
    url              VARCHAR(255) NOT NULL,
    interval_seconds INT NOT NULL DEFAULT 60,
    threshold_ms     INT NOT NULL DEFAULT 1000
);

CREATE TABLE logs (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    api_id        INT NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
    status_code   INT,
    response_time INT,
    state         VARCHAR(20) NOT NULL   -- OK | SLOW | FAIL
);
```

> SQLite uses identical column types (INTEGER / TEXT) and is applied automatically when MySQL is unavailable.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Can't connect to MySQL server` | Expected if MySQL is not running — SQLite is used automatically |
| `UnicodeEncodeError` on Windows | Already fixed — all console output uses plain ASCII |
| `401` on all API calls | Session expired or cookies blocked — sign in again |
| Dashboard blank / "Loading APIs…" stuck | Make sure `python app.py` is running on port 5000 |
| Email alerts not sending | Set `SMTP_USERNAME` and `SMTP_PASSWORD` in `config.py` |
