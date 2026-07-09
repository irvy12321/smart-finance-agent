# Development Checks

This project is validated against Python 3.12 and Node.js 20.

## Runtime Versions

- Python: 3.12
- Node.js: 20 LTS
- npm: 10+

Use the pinned runtime files when available:

```powershell
py -3.12 --version
nvm use
```

## Backend Checks

Run from `backend/`:

```powershell
ruff check .
ruff format --check .
python -m compileall -q app
$env:JWT_SECRET_KEY="test-jwt-secret-key-at-least-32-chars-long-aaaa"
$env:DEFAULT_ADMIN_PASSWORD="test-admin-password-123"
$env:ALLOW_MOCK_DATA="false"
python -m pytest tests/ -q
```

## Frontend Checks

Run from `frontend/`:

```powershell
npm ci
npm run lint
npm run test -- --run
npm run build
```

If PowerShell blocks `npm.ps1`, call `npm.cmd` instead.

## Docker Checks

Run from the repository root on a machine with Docker installed:

```powershell
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up
```

Then verify:

```powershell
curl http://localhost:8000/ping
curl http://localhost/
```
