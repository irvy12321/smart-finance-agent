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
# Prepare production environment files
cp .env.production.example .env
cp backend/.env.production.example backend/.env
# Edit backend/.env and replace every placeholder secret/key before deploy.

# Validate compose syntax
docker compose -f docker-compose.prod.yml config

# Build production images
docker compose -f docker-compose.prod.yml build

# Start production services
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Verify health
curl http://localhost/health
curl http://localhost/api/ping
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network (sfa-network)            │
│                                                             │
│  ┌─────────────────────┐      ┌─────────────────────────┐  │
│  │   Frontend (Nginx)  │      │   Backend (FastAPI)     │  │
│  │   Port: 80          │─────▶│   Port: 8000            │  │
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
  - Listens on non-privileged container ports (`8080`, optional TLS `8443`);
    Compose maps host `3000`/`80`/`443` to those internal ports.

### Backend Image

- **Base**: `python:3.12-slim-bookworm`
- **Size**: ~500MB
- **Features**:
  - Multi-stage build (dependencies → runtime)
  - Runtime dependencies copied from the builder stage
  - 2 uvicorn worker processes
  - Non-root user (appuser)
  - tini init system

Compose services run with `no-new-privileges:true` and `cap_drop: [ALL]` so the
runtime cannot gain extra Linux capabilities after startup.

## Environment Variables

### Backend (.env)

```env
# Required auth configuration
JWT_SECRET_KEY=replace-with-a-64-byte-random-secret
DEFAULT_ADMIN_PASSWORD=replace-with-a-strong-admin-password

# LLM Configuration
MIMO_API_KEY=your-api-key
LLM_PROVIDER=mimo

# Production reliability defaults
ALLOW_MOCK_DATA=false
LITELLM_LOCAL_MODEL_COST_MAP=true
CORS_ORIGINS=https://your-domain.example

# Sentry (optional)
SENTRY_DSN=your-sentry-dsn
ENVIRONMENT=production
```

Production startup fails fast when `JWT_SECRET_KEY` is missing, weak, or still a
placeholder; when `DEFAULT_ADMIN_PASSWORD` is missing, weak, or still a
placeholder; when `ALLOW_MOCK_DATA=true`; or when `CORS_ORIGINS` contains
wildcard/localhost origins. Production startup also fails if the active LLM
provider API key is missing or still a placeholder.

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
| Frontend | 1 CPU | 512MB |
| Backend | 1 CPU | 4GB |

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

3. Uncomment the `443:8443` port mapping in `docker-compose.prod.yml`.

4. Restart frontend service:
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
