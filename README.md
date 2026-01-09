# AGMS - Association Governance Management System

A specialized, AI-enhanced Financial Management System for Philippine Homeowners Associations (HOAs) and Condominium Corporations.

## Features

- **Multi-tenancy**: Complete data isolation per organization
- **Unit Registry**: Master list of Lots/Blocks or Units/Floors
- **Financial Ledger**: Income/Expense tracking with category management
- **Asset Manager**: Profit/Loss tracking for facilities
- **AI OCR Scanner**: Receipt scanning with Google Cloud Vision (Premium)
- **Role-Based Access**: Admin, Staff, Board, Member roles

## Tech Stack

- **Backend**: Django 5.x + Django Ninja
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
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

3. **Access**:
   - API: <http://localhost:8000/api/>
   - Swagger Docs: <http://localhost:8000/api/docs>
   - ReDoc: <http://localhost:8000/api/redoc>
   - Admin: <http://localhost:8000/admin/>

## Development (Local)

1. **Create virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
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

## Project Structure

```
agms/
├── config/             # Django settings, URLs, Celery
├── apps/
│   ├── organizations/  # Multi-tenancy & Branding
│   ├── identity/       # Auth & Permissions
│   ├── registry/       # Unit & Household Management
│   ├── ledger/         # Financial Core
│   ├── assets/         # Facility Tracking
│   ├── intelligence/   # AI & Automation
│   └── governance/     # Board Resolutions
├── docs/               # Documentation
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Architecture

This project follows a **Modular Monolith** pattern:

- Apps communicate through **Services** and **DTOs** (Data Transfer Objects)
- No direct model imports across app boundaries
- Uses UUID primary keys for future microservices migration
- Import Linter enforces architectural constraints

## License

Proprietary - All rights reserved.
