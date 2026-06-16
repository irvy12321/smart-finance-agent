import hashlib
import os


def check_jwt_secret():
    """Validate JWT_SECRET_KEY at startup. Fail fast if missing or weak."""
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY not set. "
            "Set it in .env or docker-compose environment."
        )

    if len(secret) < 32:
        raise RuntimeError(
            f"FATAL: JWT_SECRET_KEY too weak ({len(secret)} chars). "
            "Minimum 32 characters required."
        )

    secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    print(f"[STARTUP] JWT_SECRET_KEY hash: {secret_hash}")
    print(f"[STARTUP] JWT_SECRET_KEY length: {len(secret)} chars")
    return secret_hash
