# NEC4 ECC Contractor Platform

A Django 6.0.3 web application for managing NEC4 Engineering and Construction Contracts (ECC), with multi-tenant SaaS subscriptions, role-based access control, and Stripe billing.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0.3 / Python 3.13 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Task queue | Celery 5 + Redis |
| State machine | django-fsm 3 |
| Audit trail | django-auditlog |
| Payments | Stripe |
| Frontend | Bootstrap 5.3 + HTMX + Crispy Forms |
| Static files | WhiteNoise |
| Containerisation | Docker + docker-compose |

---

## Quick Start

```bash
cp .env.example .env          # fill in SECRET_KEY at minimum
uv sync                        # install dependencies
source .venv/bin/activate
python manage.py migrate
python manage.py create_plans  # seed Free / Pro / Enterprise plans
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000` — default dev login: `admin` / `admin1234`

---

## Platform Workflow

### 🔵 Public Flow (New User)

```
Landing → /accounts/register/
         ├── Fill: Name, Email, Organisation Name, Username, Password
         ├── Auto-creates: Organisation (Free plan) + Owner membership
         └── Redirects to Dashboard
```

---

### 🟢 Organisation Owner / Admin Flow

```
Dashboard
│
├── People  (/people/)                    ← Admin navbar only
│   ├── Add Contractor → /people/new/     (set role=Contractor)
│   ├── Add PM         → /people/new/     (set role=Project Manager)
│   └── Add Supervisor → /people/new/     (set role=Supervisor)
│
├── Organisation  (/organisation/)
│   ├── Members → /organisation/members/
│   │   ├── Invite (by email of registered user)
│   │   ├── Change Role (Owner/Admin/Member)
│   │   └── Remove
│   └── Billing → /organisation/billing/
│       ├── View Free / Pro / Enterprise plans
│       ├── Upgrade → Stripe Checkout
│       └── Manage existing subscription → Stripe Portal
│
└── Projects  (/projects/new/)            ← blocked if plan limit hit
    ├── Assign Contractor, PM, Supervisor (from People list)
    └── Auto-added as project members
```

---

### 🟡 Project Lifecycle

```
Project Created
│
├── Early Warnings  (/early-warnings/)
│   ├── Any party raises EW (Clause 15)
│   ├── Reference auto-generated (EW-0001, EW-0002…)
│   └── [Pro/Enterprise] Celery alerts if open > 2 weeks
│
├── Compensation Events  (/compensation-events/)
│   │
│   ├── notified     → Contractor/PM raises CE
│   ├── quoted       → Contractor submits quote
│   ├── pm_reviewing → PM assesses quote
│   ├── implemented  → Agreed & implemented
│   ├── rejected     → PM rejects
│   └── assumed      → Auto-trigger if PM silent > 8 weeks (Clause 61.4)
│                       [Pro/Enterprise] Celery warns PM at 7-week mark
│
├── Communications  (/communications/)
│   └── Formal notice log with Clause 13.7 duplicate detection
│
└── Financial  (/financial/)
    ├── Defined Cost Schedule  → Contractor enters costs
    └── Payment Applications   → Contractor submits, PM assesses (Clause 51)
                                  [7-day PM certification deadline tracked]
```

---

### 🔴 Plan Gates

| Action | Free | Pro | Enterprise |
|---|---|---|---|
| Create project | 1 max | 1 max | Unlimited |
| Invite member | 3 max | 10 max | Unlimited |
| Deadline emails (Celery) | ✗ | ✓ | ✓ |
| Price | Free | $49/mo | $199/mo |

---

### 🔑 Role Permissions Matrix

| Feature | Contractor | Project Manager | Supervisor | Admin |
|---|---|---|---|---|
| View projects / EWs / CEs | ✓ | ✓ | ✓ | ✓ |
| Create Early Warning | ✓ | ✓ | ✓ | ✓ |
| Create Compensation Event | ✓ | ✓ | — | ✓ |
| Submit CE quote | ✓ | — | — | ✓ |
| Assess CE / Payment Application | — | ✓ | — | ✓ |
| Create project | — | ✓ | — | ✓ |
| Manage People | — | — | — | ✓ |
| Invite organisation members | — | — | — | ✓ |
| Billing & plan management | — | — | — | ✓ (owner) |

---

## URL Reference

| URL | Description |
|---|---|
| `/accounts/login/` | Sign in |
| `/accounts/register/` | Public self-registration |
| `/dashboard/` | Home dashboard |
| `/profile/` | Edit profile |
| `/people/` | People management (admin) |
| `/projects/` | Project list |
| `/early-warnings/` | Early Warning register |
| `/compensation-events/` | CE register & FSM |
| `/communications/` | Formal communications log |
| `/financial/` | Costs & payment applications |
| `/organisation/` | Organisation dashboard |
| `/organisation/members/` | Member management |
| `/organisation/billing/` | Billing & plan upgrade |
| `/webhooks/stripe/` | Stripe webhook endpoint |
| `/admin/` | Django admin |

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```dotenv
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## Docker

```bash
docker-compose up --build
```

Services: `web` (Django), `db` (PostgreSQL 16), `redis` (Redis 7), `celery`, `celery-beat`
