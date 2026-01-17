# AGMS - Association Governance Management System

A specialized, AI-enhanced Financial Management System for Philippine Homeowners Associations (HOAs) and Condominium Corporations.

## Features

- **Multi-tenancy**: Complete data isolation per organization
- **Unit Registry**: Master list of Lots/Blocks or Units/Floors
- **Financial Ledger**: Comprehensive income/expense tracking with approval workflow
- **Asset Manager**: Reservation system and profit/loss tracking for facilities
- **AI OCR Scanner**: Receipt scanning with Google Cloud Vision (Premium)
- **Role-Based Access**: Admin, Staff, Board, Auditor, Homeowner roles

## Recent Updates

### Financial Ledger Feature Set (v2.0)

The Financial Ledger has been significantly enhanced with the following capabilities:

#### Core Features
- **Transaction CRUD**: Record income and expenses with category management
- **Approval Workflow**: POSTED → VERIFIED status flow
- **Amount Validation**: Prevents overcollection (exact match unless advance payment)
- **Credit System**: Advance payments credited to unit accounts
- **Attachments**: Receipt upload with S3-ready storage

#### Calculations
- **Simple Interest Penalties**: `I = P × R × T` (Principal × Rate × Time in months)
- **Configurable Discounts**: Percentage or flat discounts with minimum month requirements
- **Dues Statement Tracking**: Monthly dues per unit with penalty tracking
- **Breakdown Preview**: See penalties, discounts, and net amount before submission

#### Reporting & Analytics
- **PDF Reports**: Daily, monthly, and yearly reports using WeasyPrint
- **Financial Summaries**: MTD/YTD income, expense, and net balance
- **Category Breakdowns**: Income and expense analysis by category
- **Monthly Trends**: Income/expense trends over configurable periods
- **Best/Worst Months**: Performance comparison across periods
- **Profit/Loss Status**: Real-time profitability indicators

#### Configuration
- **Billing Configuration**: Monthly dues amount, due dates, grace periods
- **Penalty Policies**: Configurable rates, grace periods, and calculation methods
- **Discount Configurations**: Validity dates, minimum months, percentage or flat

### Asset Manager Feature Set (v2.1)

Manage revenue-generating and shared infrastructure facilities:

#### Core Features
- **Asset CRUD**: Create, update, and soft-delete assets (Pool, Clubhouse, Function Hall, etc.)
- **Reservation System**: Book assets with scheduling and availability checking
- **Payment Workflow**: Homeowners get PENDING_PAYMENT status; staff confirms after payment
- **Automatic Expiration**: Unpaid reservations expire after configurable time (default: 48 hours)
- **Configurable Policies**: Per-organization settings for expiration, same-day booking, advance booking

#### Pricing & Discounts
- **Hourly Rates**: Configurable rental rates per asset
- **Security Deposits**: Optional deposits with configurable amounts
- **Discount Integration**: Apply existing discounts to reservations
- **Payment Breakdown Preview**: See full breakdown before booking

#### Analytics
- **Income per Asset**: Current month income, expenses, and net profit
- **Transaction History**: Drill-down to see rent and expense history per asset
- **Reservation Count**: Track utilization per asset

#### Reservation Status Flow
```
[HOMEOWNER creates] → PENDING_PAYMENT → [Staff records payment] → CONFIRMED → COMPLETED
                                      ↓ (timeout)
                                    EXPIRED
```

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
| `staff` | STAFF | Can create transactions, manage reservations |
| `board` | BOARD | Can approve transactions, manage config |
| `auditor` | AUDITOR | View-only access |
| `homeowner` | HOMEOWNER | Can view own documents, create reservations |

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

### Local Environment

```bash
# Run all ledger tests
python manage.py test apps.ledger

# Run specific test file
python manage.py test apps.ledger.tests.test_services
python manage.py test apps.ledger.tests.test_api
```

### Docker Environment

```bash
# Run all tests
docker-compose exec backend python manage.py test

# Run specific app tests
docker-compose exec backend python manage.py test apps.assets

# Run specific test file
docker-compose exec backend python manage.py test apps.assets.tests.test_receipt_workflow
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
│   ├── assets/         # Facility Tracking & Reservations
│   │   ├── models.py   # Asset, Reservation, ReservationConfig
│   │   ├── services.py # Business logic
│   │   ├── api.py      # API endpoints
│   │   └── tasks.py    # Celery tasks (expiration)
│   ├── intelligence/   # AI & Automation
│   └── governance/     # Board Resolutions
├── docs/               # Documentation
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API Endpoints

### Identity (`/api/identity/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login` | POST | User login |
| `/logout` | POST | User logout |
| `/me` | GET | Get current user info |

### Organizations (`/api/organizations/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List organizations |
| `/` | POST | Create organization |
| `/{id}` | GET | Get organization |
| `/{id}` | PUT | Update organization |

### Registry (`/api/registry/units/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List units (filtered by role) |
| `/` | POST | Create unit |
| `/{id}` | PUT | Update unit |
| `/{id}` | DELETE | Delete unit |

### Ledger (`/api/ledger/`)

#### Transactions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/transactions` | GET | List transactions with filters |
| `/transactions/{id}` | GET | Get transaction details |
| `/transactions/income` | POST | Record income |
| `/transactions/expense` | POST | Record expense |
| `/transactions/income/preview` | POST | Preview income breakdown (penalties, discounts) |
| `/transactions/{id}/verify` | POST | Verify transaction |
| `/transactions/{id}/cancel` | POST | Cancel transaction |

#### Attachments
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/transactions/{id}/attachments` | GET | List attachments |
| `/transactions/{id}/attachments` | POST | Upload receipt |

#### Credits
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/credits/{unit_id}` | GET | Get unit credit balance |
| `/credits/{unit_id}/history` | GET | Get credit history |

#### Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/summary` | GET | Financial summary (MTD/YTD) |
| `/analytics/expenses-by-category` | GET | Expense breakdown by category |
| `/analytics/income-by-category` | GET | Income breakdown by category |
| `/analytics/monthly-trends` | GET | Monthly income/expense trends |
| `/analytics/best-worst-months` | GET | Best and worst performing months |
| `/analytics/profit-loss` | GET | Profit/loss status |

#### Configuration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/categories` | GET | List transaction categories |
| `/categories` | POST | Create category |
| `/discounts` | GET | List discount configurations |
| `/discounts` | POST | Create discount |
| `/penalties` | GET | List penalty policies |
| `/penalties` | POST | Create penalty policy |
| `/billing/config` | GET | Get billing configuration |
| `/billing/config` | POST | Create/update billing config |
| `/billing/generate` | POST | Trigger billing generation |

#### Reports
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reports/daily` | GET | Download daily PDF report |
| `/reports/monthly` | GET | Download monthly PDF report |
| `/reports/yearly` | GET | Download yearly PDF report |

### Assets (`/api/assets/`)

#### Asset CRUD
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List assets |
| `/` | POST | Create asset |
| `/{id}` | GET | Get asset |
| `/{id}` | PUT | Update asset |
| `/{id}` | DELETE | Soft-delete asset |

#### Configuration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config` | GET | Get reservation config (expiration hours, etc.) |
| `/config` | POST | Update reservation config |

#### Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics` | GET | Assets with current month income stats |
| `/{id}/transactions` | GET | Asset income/expense history |

#### Availability
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/{id}/availability` | GET | Get asset schedule/booked slots |

#### Reservations
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reservations` | GET | List reservations |
| `/reservations` | POST | Create reservation |
| `/reservations/preview` | POST | Preview payment breakdown |
| `/reservations/{id}` | GET | Get reservation details |
| `/reservations/{id}/payment` | POST | Record payment |
| `/reservations/{id}/cancel` | POST | Cancel reservation |
| `/discounts/applicable` | GET | Get applicable discounts |

See full interactive API documentation at `/api/docs`.

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
