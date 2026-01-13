# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies including WeasyPrint requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
