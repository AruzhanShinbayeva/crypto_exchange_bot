import os

# Load environment variables
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# API URL configuration
API_URL = os.getenv("API_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
