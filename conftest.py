"""Root conftest — sets env vars before any module imports Settings()."""

import os

# Ensure BOT_TOKEN exists before any test module triggers config.py import
os.environ.setdefault("BOT_TOKEN", "test:fake-token-for-tests-only")
