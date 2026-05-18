import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
p_key = os.getenv("SECRET_KEY")
p_alg = os.getenv("ALGORITHM")