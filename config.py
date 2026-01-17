import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
