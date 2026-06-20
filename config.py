import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DEFAULT_MINIMUM_STOCK = 10
OFFLINE_DB_PATH = "offline_data/offline_queue.db"
PHOTO_BUCKET = "component-photos"
