import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DB_URL")
test_db_url = os.getenv("TEST_DB_URL")
p_key = os.getenv("SECRET_KEY")
p_alg = os.getenv("ALGORITHM")