# AGMS - Association Governance Management System

A specialized, AI-enhanced Financial Management System for Philippine Homeowners Associations (HOAs) and Condominium Corporations.

## Features

- **Multi-tenancy**: Complete data isolation per organization
- **Unit Registry**: Master list of Lots/Blocks or Units/Floors
- **Financial Ledger**: Comprehensive income/expense tracking with approval workflow
- **Asset Manager**: Profit/Loss tracking for facilities
- **AI OCR Scanner**: Receipt scanning with Google Cloud Vision (Premium)
- **Role-Based Access**: Admin, Staff, Board, Auditor, Homeowner roles

## Recent Updates

### Financial Ledger Feature Set (v2.0)

The Financial Ledger has been significantly enhanced with the following capabilities:

#### Core Features
- **Transaction CRUD**: Record income and expenses with category management
- **Approval Workflow**: DRAFT → PENDING → APPROVED status flow
- **Amount Validation**: Prevents overcollection (exact match unless advance payment)
- **Credit System**: Advance payments credited to unit accounts

#### Calculations
- **Simple Interest Penalties**: `I = P × R × T` (Principal × Rate × Time in months)
- **Configurable Discounts**: Percentage or flat discounts with minimum month requirements
- **Dues Statement Tracking**: Monthly dues per unit with penalty tracking

#### Reporting & Analytics
- **PDF Reports**: Daily, monthly, and yearly reports using WeasyPrint
- **Financial Summaries**: MTD/YTD income, expense, and net balance
- **Category Breakdowns**: Income and expense analysis by category
- **Monthly Trends**: Income/expense trends over configurable periods
- **Profit/Loss Status**: Real-time profitability indicators

#### Receipt Management
- **S3-Ready Storage**: AWS S3 with local fallback for development
- **File Validation**: JPEG, PNG, PDF (max 10MB)

## Tech Stack

- **Backend**: Django 5.x + Django Ninja
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **PDF Generation**: WeasyPrint
- **File Storage**: django-storages + AWS S3 (optional)
- **Container**: Docker + Docker Compose

## Quick Start

1. **Clone and setup**:

   ```bash
   git clone git@github.com:MichaelPagaran/agms.git
   cd agms
   cp .env.example .env
   ```

2. **Run with Docker**:

   ```bash
   docker-compose up --build
   ```

3. **Run migrations**:

   ```bash
   docker-compose exec backend python manage.py migrate
   ```

4. **Create superuser**:

   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

5. **Seed default data** (see Management Commands below):

   ```bash
   docker-compose exec backend python manage.py seed_ledger_defaults --all
   ```

6. **Access**:
   - API: <http://localhost:8000/api/>
   - Swagger Docs: <http://localhost:8000/api/docs>
   - Admin: <http://localhost:8000/admin/>

## Management Commands

### User Seeder (Identity)

```bash
# Create test users with different roles (for development/testing)
python manage.py seed_users
```

Creates the following test users (password: `password`):

| Username | Role | Notes |
|----------|------|-------|
| `admin` | ADMIN | is_staff=True, is_superuser=True |
| `staff` | STAFF | Can create transactions |
| `board` | BOARD | Can approve transactions, manage config |
| `auditor` | AUDITOR | View-only access |
| `homeowner` | HOMEOWNER | Can view own documents |

### Ledger Seeder

```bash
# Seed categories, discounts, and penalty policies for a specific organization
python manage.py seed_ledger_defaults --org-id <UUID>

# Seed for ALL active organizations
python manage.py seed_ledger_defaults --all
```

This command seeds:
- **Income Categories**: Monthly Dues, Special Assessments, Rental Income, Parking Fees, etc.
- **Expense Categories**: Utilities, Security, Maintenance, Administrative, etc.
- **Discounts**: Early Payment (5%), 6-Month Advance (10%), 12-Month Advance (20%)
- **Penalty Policies**: Late Payment (2% monthly simple interest, 15-day grace period)

### Docker Commands

```bash
# Run seeders in Docker
docker-compose exec backend python manage.py seed_users
docker-compose exec backend python manage.py seed_ledger_defaults --all
```


## Development (Local)

1. **Create virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

2. **Run database migrations**:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Run development server**:

   ```bash
   python manage.py runserver
   ```

## Running Tests

```bash
# Run all ledger tests
python manage.py test apps.ledger

# Run specific test file
python manage.py test apps.ledger.tests.test_services
python manage.py test apps.ledger.tests.test_api
```

## Project Structure

```
agms/
├── config/             # Django settings, URLs, Celery, Storage
├── apps/
│   ├── organizations/  # Multi-tenancy & Branding
│   ├── identity/       # Auth & Permissions
│   ├── registry/       # Unit & Household Management
│   ├── ledger/         # Financial Core
│   │   ├── management/ # Commands (seeders)
│   │   ├── templates/  # PDF report templates
│   │   ├── tests/      # Unit & integration tests
│   │   ├── models.py   # Transaction, Credit, Discount, Penalty models
│   │   ├── services.py # Business logic
│   │   ├── api.py      # API endpoints
│   │   └── ...
│   ├── assets/         # Facility Tracking
│   ├── intelligence/   # AI & Automation
│   └── governance/     # Board Resolutions
├── docs/               # Documentation
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API Endpoints (Ledger)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ledger/transactions` | GET | List transactions with filters |
| `/api/ledger/transactions/income` | POST | Record income |
| `/api/ledger/transactions/expense` | POST | Record expense |
| `/api/ledger/transactions/{id}/approve` | POST | Approve transaction |
| `/api/ledger/analytics/summary` | GET | Financial summary (MTD/YTD) |
| `/api/ledger/analytics/profit-loss` | GET | Profit/loss status |
| `/api/ledger/reports/daily` | GET | Download daily PDF report |
| `/api/ledger/reports/monthly` | GET | Download monthly PDF report |
| `/api/ledger/reports/yearly` | GET | Download yearly PDF report |
| `/api/ledger/credits/{unit_id}` | GET | Get unit credit balance |

See full API documentation at `/api/docs`.

## Architecture

This project follows a **Modular Monolith** pattern:

- Apps communicate through **Services** and **DTOs** (Data Transfer Objects)
- No direct model imports across app boundaries
- Uses UUID primary keys for future microservices migration
- Import Linter enforces architectural constraints

## Environment Variables

See `.env.example` for all configuration options:

```bash
# Core
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://...

# AWS S3 (optional, for receipt storage)
USE_S3_STORAGE=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=ap-southeast-1
```

## License

Proprietary - All rights reserved.
