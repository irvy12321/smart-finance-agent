# Docker Deployment Guide

This guide explains how to deploy Smart Finance Agent using Docker.

## Prerequisites

- Docker 20.10+
- Docker Compose v2.0+
- At least 4GB RAM available for Docker

## Quick Start

### Development

```bash
# Build and start services
docker compose up --build

# Or use the build script
./docker-build.ps1  # Windows PowerShell
docker-build.bat    # Windows CMD

# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Production

```bash
# Build production images
docker compose -f docker-compose.prod.yml build

# Start production services
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network (sfa-network)            │
│                                                             │
│  ┌─────────────────────┐      ┌─────────────────────────┐  │
│  │   Frontend (Nginx)  │      │   Backend (FastAPI)     │  │
│  │   Port: 80/443      │─────▶│   Port: 8000            │  │
│  │   - Static files    │      │   - API endpoints       │  │
│  │   - API proxy       │      │   - Agent orchestration │  │
│  └─────────────────────┘      └─────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Image Details

### Frontend Image

- **Base**: `nginx:1.25-alpine`
- **Size**: ~25MB
- **Features**:
  - Multi-stage build (Node.js build → Nginx serve)
  - Gzip compression enabled
  - Static asset caching (1 year)
  - Security headers
  - Non-root user (nginx)

### Backend Image

- **Base**: `python:3.11-slim`
- **Size**: ~500MB
- **Features**:
  - Multi-stage build (dependencies → runtime)
  - Virtual environment isolation
  - uvloop for better performance
  - 4 worker processes
  - Non-root user (appuser)
  - tini init system

## Environment Variables

### Backend (.env)

```env
# LLM Configuration
MIMO_API_KEY=your-api-key
LLM_PROVIDER=mimo

# Sentry (optional)
SENTRY_DSN=your-sentry-dsn
ENVIRONMENT=production
```

### Frontend (build args)

```bash
# Passed during build
VITE_API_URL=/api
VITE_SENTRY_DSN=your-sentry-dsn
```

## Volumes

| Volume | Purpose | Mount Point |
|--------|---------|-------------|
| `backend_data` | SQLite database | `/app/data` |
| `backend_output` | Generated reports | `/app/output` |
| `backend_logs` | Application logs | `/app/logs` |

## Health Checks

- **Frontend**: `GET /health` (returns 200 OK)
- **Backend**: `GET /ping` (returns JSON status)

Health checks run every 30 seconds with 3 retries.

## Resource Limits

### Development

| Service | CPU | Memory |
|---------|-----|--------|
| Frontend | 1 CPU | 256MB |
| Backend | 2 CPUs | 2GB |

### Production

| Service | CPU | Memory |
|---------|-----|--------|
| Frontend | 2 CPUs | 512MB |
| Backend | 4 CPUs | 4GB |

## SSL/TLS Configuration

For production with HTTPS:

1. Place SSL certificates in `nginx/ssl/`:
   - `fullchain.pem` - Certificate chain
   - `privkey.pem` - Private key

2. Copy and modify the nginx config:
   ```bash
   cp nginx/conf.d/default.conf.example nginx/conf.d/default.conf
   # Edit default.conf with your domain
   ```

3. Restart frontend service:
   ```bash
   docker compose restart frontend
   ```

## Common Commands

```bash
# View running containers
docker compose ps

# View logs (specific service)
docker compose logs -f backend
docker compose logs -f frontend

# Restart a service
docker compose restart backend

# Enter a container
docker exec -it sfa-backend bash
docker exec -it sfa-frontend sh

# Rebuild single service
docker compose build --no-cache backend
docker compose up -d backend

# Clean up
docker compose down -v  # Remove volumes too
docker system prune -af # Clean all unused resources
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs backend

# Check health status
docker inspect sfa-backend | grep -A 10 Health
```

### Out of memory

```bash
# Check resource usage
docker stats

# Increase memory limit in docker-compose.yml
```

### Connection refused

```bash
# Check if services are running
docker compose ps

# Check network connectivity
docker exec sfa-frontend curl http://backend:8000/ping
```

### Build fails

```bash
# Clean build cache
docker builder prune -af

# Rebuild without cache
docker compose build --no-cache
```

## Monitoring

### Container Stats

```bash
# Real-time resource usage
docker stats

# Specific service
docker stats sfa-backend sfa-frontend
```

### Logs

```bash
# Follow all logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail 100 backend

# Since specific time
docker compose logs --since 2024-01-01T00:00:00 backend
```

## Backup and Restore

### Backup

```bash
# Backup volumes
docker run --rm -v sfa-backend_data:/data -v $(pwd):/backup alpine tar czf /backup/backend-data.tar.gz -C /data .

# Backup database
docker exec sfa-backend cp /app/data/database.db /app/data/database.db.backup
docker cp sfa-backend:/app/data/database.db.backup ./backup/
```

### Restore

```bash
# Restore volumes
docker run --rm -v sfa-backend_data:/data -v $(pwd):/backup alpine tar xzf /backup/backend-data.tar.gz -C /data

# Restart services
docker compose restart
```
