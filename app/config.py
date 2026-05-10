import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_TITLE = "SHL Assessment Recommender"
API_VERSION = "1.0.0"
MAX_CONVERSATION_TURNS = 8
API_TIMEOUT_SECONDS = 30

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "openai/gpt-oss-20b"
LLM_TEMPERATURE = 0.5
LLM_MAX_TOKENS = 1000

# Embeddings Configuration
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
FAISS_INDEX_TYPE = "Flat"

# Data Configuration
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

CATALOG_PATH = os.getenv(
    "CATALOG_PATH",
    BASE_DIR / "shl_product_catalog.json"
)

# Search Configuration
MAX_RECOMMENDATIONS = 10
KEYWORD_SEARCH_TOP_K = 20
SEMANTIC_SEARCH_TOP_K = 20
MERGED_CANDIDATES_TOP_K = 20

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
