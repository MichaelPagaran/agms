"""
Database configuration for AGMS.

Supports multiple deployment scenarios:
- Local development (SQLite or Docker PostgreSQL)
- AWS Lambda (RDS via RDS Proxy)
- Traditional server (direct RDS connection)
"""
import os
import re
from pathlib import Path


def get_database_config(base_dir: Path) -> dict:
    """
    Returns database configuration based on environment.
    
    Supports:
    - DATABASE_URL format: postgres://user:pass@host:port/dbname
    - Individual env vars: DB_HOST, DB_NAME, etc.
    - Fallback to SQLite for development
    
    For Lambda with RDS Proxy:
    - Uses IAM authentication when RDS_PROXY_IAM=true
    - Connection pooling is handled by RDS Proxy
    """
    database_url = os.getenv('DATABASE_URL', '')
    
    # Option 1: Parse DATABASE_URL
    if database_url and database_url.startswith('postgres'):
        return _parse_database_url(database_url)
    
    # Option 2: Use individual environment variables
    db_host = os.getenv('DB_HOST')
    if db_host:
        return _get_env_config()
    
    # Option 3: Fallback to SQLite (development)
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': base_dir / 'db.sqlite3',
    }


def _parse_database_url(url: str) -> dict:
    """Parse PostgreSQL DATABASE_URL into Django config."""
    pattern = r'postgres://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)/(?P<name>.+)'
    match = re.match(pattern, url)
    
    if not match:
        raise ValueError(f"Invalid DATABASE_URL format: {url}")
    
    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': match.group('name'),
        'USER': match.group('user'),
        'PASSWORD': match.group('password'),
        'HOST': match.group('host'),
        'PORT': match.group('port'),
    }
    
    # Lambda-specific optimizations
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        config['CONN_MAX_AGE'] = 0  # RDS Proxy handles pooling
        config['OPTIONS'] = {
            'connect_timeout': 5,
            'options': '-c statement_timeout=30000',  # 30 second query timeout
        }
    
    return config


def _get_env_config() -> dict:
    """Build config from individual environment variables."""
    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'agms'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
    
    # Password can come from env or Secrets Manager
    password = os.getenv('DB_PASSWORD')
    if password:
        config['PASSWORD'] = password
    
    # RDS Proxy with IAM authentication
    if os.getenv('RDS_PROXY_IAM', '').lower() == 'true':
        config['OPTIONS'] = {
            'sslmode': 'require',
        }
        # IAM auth token would be generated at runtime
        # This is handled by a custom database backend or middleware
    
    # Lambda optimizations
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        config['CONN_MAX_AGE'] = 0
        config['OPTIONS'] = config.get('OPTIONS', {})
        config['OPTIONS']['connect_timeout'] = 5
    
    return config


# =============================================================================
# RDS Proxy Configuration Notes
# =============================================================================
"""
RDS Proxy Setup (AWS Console):

1. Create RDS Proxy:
   - Engine: PostgreSQL
   - Target: Your RDS instance
   - Authentication: Secrets Manager (stores DB credentials)

2. Configure Lambda:
   - VPC: Same VPC as RDS Proxy
   - Security Group: Allow outbound to RDS Proxy port (5432)
   - Environment Variables:
     - DATABASE_URL=postgres://user:pass@proxy-endpoint:5432/agms

3. Benefits:
   - Connection pooling (handles 1000s of Lambda connections)
   - Automatic failover
   - IAM authentication support
"""
