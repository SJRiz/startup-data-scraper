import os
from dotenv import load_dotenv

load_dotenv()

RETRY_DELAY = 2.5
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
X_ALGOLIA_API_KEY = os.getenv("x_algolia_api_key")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)