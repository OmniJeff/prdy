import os
import secrets
from dotenv import load_dotenv

# Load .env file for local development (ignored in production)
load_dotenv()

# Environment detection
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT")
IS_PRODUCTION = RAILWAY_ENVIRONMENT is not None

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Session secret - require explicit key in production, generate random for dev
if IS_PRODUCTION:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required in production")
else:
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Redis configuration (for session storage in production)
REDIS_URL = os.getenv("REDIS_URL")

# Output directory - use Railway volume if available, otherwise local
RAILWAY_VOLUME = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
if RAILWAY_VOLUME:
    OUTPUT_DIR = os.path.join(RAILWAY_VOLUME, "output")
else:
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
