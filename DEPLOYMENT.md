# AGMS Deployment Guide

This guide covers deploying the AGMS backend in different environments.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Compose (Team Development)](#docker-compose)
3. [AWS Lambda (Production)](#aws-lambda-production)
4. [Troubleshooting](#troubleshooting)

---

## Local Development

The simplest setup for individual development. No Docker required.

### Prerequisites

- Python 3.12+
- Node.js 20+ (for frontend)

### Setup

```bash
# Clone and enter the project
cd agms

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env - set these values:
# TASK_BACKEND=local
# DEBUG=True
# (Leave DATABASE_URL empty for SQLite)
```

### Run

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Seed test data (optional)
python manage.py seed_users
python manage.py seed_ledger_defaults --all

# Start server
python manage.py runserver
```

### What You Get

| Feature | Behavior |
|---------|----------|
| Database | SQLite (local file) |
| Tasks | Sync execution (blocking) |
| File Storage | Local `media/` folder |
| API URL | <http://localhost:8000/api/> |

### Frontend Integration

```bash
# In dayung/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## Docker Compose

Full stack with PostgreSQL, Redis, and Celery. Closest to production.

### Prerequisites

- Docker Desktop
- Docker Compose v2+

### Quick Start

```bash
cd agms

# Copy environment file
cp .env.example .env

# Edit .env - key settings:
# DATABASE_URL=postgres://user:password@db:5432/agms
# REDIS_URL=redis://redis:6379/0
# TASK_BACKEND=celery

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Create admin
docker-compose exec backend python manage.py createsuperuser

# Seed data
docker-compose exec backend python manage.py seed_users
docker-compose exec backend python manage.py seed_ledger_defaults --all
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| backend | 8000 | Django API |
| db | 5432 | PostgreSQL |
| redis | 6379 | Celery broker |
| celery_worker | - | Background tasks |
| celery_beat | - | Scheduled tasks |

### Useful Commands

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Restart a service
docker-compose restart backend

# Stop all
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

---

## AWS Lambda (Production)

Serverless deployment using AWS SAM.

### Prerequisites

- AWS CLI configured (`aws configure`)
- SAM CLI installed (`brew install aws-sam-cli` or [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- AWS Account with appropriate permissions

### Step 1: Create RDS Database

```bash
# Via AWS CLI (or use Console)
aws rds create-db-instance \
  --db-instance-identifier agms-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15 \
  --master-username postgres \
  --master-user-password YOUR_PASSWORD \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name default
```

### Step 2: Create RDS Proxy

```bash
# Store credentials in Secrets Manager first
aws secretsmanager create-secret \
  --name agms/db-credentials \
  --secret-string '{"username":"postgres","password":"YOUR_PASSWORD"}'

# Create RDS Proxy (via Console is easier)
# 1. Go to RDS > Proxies > Create proxy
# 2. Select PostgreSQL engine
# 3. Target your RDS instance
# 4. Select the Secrets Manager secret
# 5. Configure VPC (same as RDS)
```

### Step 3: Create Parameter Store Values

```bash
# Database connection string (using RDS Proxy endpoint)
aws ssm put-parameter \
  --name /agms/prod/DATABASE_URL \
  --type SecureString \
  --value "postgres://postgres:PASSWORD@agms-proxy.proxy-xxx.rds.amazonaws.com:5432/agms"

# Django secret key
aws ssm put-parameter \
  --name /agms/prod/SECRET_KEY \
  --type SecureString \
  --value "your-super-secret-key-here"
```

### Step 4: Deploy with SAM

```bash
cd agms

# Build the Lambda package
sam build

# Deploy (first time - interactive)
sam deploy --guided

# Answer the prompts:
# Stack Name: agms-prod
# AWS Region: ap-southeast-1
# Environment: prod
# DatabaseSecret: arn:aws:secretsmanager:...:secret:agms/db-credentials
# VpcSubnetIds: subnet-xxx,subnet-yyy
# VpcSecurityGroupIds: sg-zzz
```

### Step 5: Run Migrations

```bash
# Get the API endpoint
API_URL=$(aws cloudformation describe-stacks \
  --stack-name agms-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

# Option 1: Run via Lambda (create a migration Lambda)
# Option 2: Connect directly to RDS from local machine with VPN/bastion

# If using bastion/VPN:
DATABASE_URL=postgres://user:pass@rds-endpoint:5432/agms \
python manage.py migrate
```

### Step 6: Update Frontend

```bash
# In dayung/.env.production
NEXT_PUBLIC_API_URL=https://xxx.execute-api.ap-southeast-1.amazonaws.com
```

### SAM Deployment Commands Reference

```bash
# First time deployment (interactive)
sam deploy --guided

# Subsequent deployments
sam deploy

# Deploy specific environment
sam deploy --config-env prod

# View stack outputs
sam list stack-outputs --stack-name agms-prod

# View logs
sam logs -n ApiFunction --stack-name agms-prod --tail

# Delete stack (DANGER: destroys everything)
sam delete --stack-name agms-prod
```

### Environment Variables (Lambda)

Set these in `template.yaml` or AWS Console:

| Variable | Description |
|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | `config.settings` |
| `TASK_BACKEND` | `lambda` |
| `DATABASE_URL` | RDS Proxy connection string |
| `TASK_QUEUE_URL` | SQS queue URL (auto-created by SAM) |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `False` (always in production) |

---

## Architecture Reference

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS Production Architecture                     │
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐ │
│  │ API Gateway  │────▶│   Lambda     │────▶│    RDS Proxy         │ │
│  │ (HTTPS)      │     │ (Django API) │     │ (Connection Pool)    │ │
│  └──────────────┘     └──────────────┘     └──────────┬───────────┘ │
│                              │                        │             │
│                              ▼                        ▼             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐ │
│  │ EventBridge  │────▶│   Lambda     │     │    RDS PostgreSQL    │ │
│  │ (Scheduler)  │     │ (Scheduled)  │     │    (Database)        │ │
│  └──────────────┘     └──────────────┘     └──────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐ │
│  │     SQS      │◀────│ TaskService  │     │        S3            │ │
│  │ (Task Queue) │     │ (API calls)  │     │ (File Storage)       │ │
│  └──────┬───────┘     └──────────────┘     └──────────────────────┘ │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │   Lambda     │                                                   │
│  │ (Workers)    │                                                   │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Local Development

**Database errors with SQLite:**

```bash
# Delete and recreate
rm db.sqlite3
python manage.py migrate
```

**Tasks not executing:**

```bash
# Ensure TASK_BACKEND=local in .env
grep TASK_BACKEND .env
```

### Docker Compose

**Container won't start:**

```bash
# Check logs
docker-compose logs backend

# Common fix: rebuild
docker-compose build --no-cache backend
docker-compose up -d
```

**Database connection refused:**

```bash
# Wait for PostgreSQL to be ready
docker-compose up -d db
sleep 5
docker-compose up -d backend
```

### AWS Lambda

**Cold starts are slow:**

- Use Provisioned Concurrency for critical paths
- Reduce package size (use Lambda layers)

**Database connection errors:**

```bash
# Check Lambda is in correct VPC
# Check security group allows 5432 to RDS Proxy
# Check RDS Proxy is in same VPC
```

**Task timeouts:**

- Increase Lambda timeout in template.yaml
- For tasks >15min, use ECS Fargate instead

**View Lambda logs:**

```bash
sam logs -n ApiFunction --stack-name agms-prod --tail
sam logs -n TaskWorkerFunction --stack-name agms-prod --tail
```

---

## Cost Estimation

### AWS Lambda (Low Traffic)

| Resource | Monthly Cost (estimated) |
|----------|--------------------------|
| Lambda (100K requests) | ~$2 |
| API Gateway | ~$3.50 |
| RDS db.t3.micro | ~$15 |
| RDS Proxy | ~$20 |
| SQS | <$1 |
| S3 (10GB) | <$1 |
| **Total** | ~$42/month |

### Scaling Tips

1. **Start with RDS db.t3.micro**, scale up as needed
2. **Use S3 for static files** (not Lambda file system)
3. **Set Lambda memory appropriately** (512MB usually sufficient)
4. **Use Reserved Concurrency** to control costs
