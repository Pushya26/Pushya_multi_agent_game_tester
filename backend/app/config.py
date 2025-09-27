import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY","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")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Fallback to OpenAI if needed
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ARTIFACTS_DIR = "artifacts"
MAX_PARALLELISM = 3