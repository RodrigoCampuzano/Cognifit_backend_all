from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/cognifit")
os.environ.setdefault("DB_ENCRYPTION_KEY", "test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
