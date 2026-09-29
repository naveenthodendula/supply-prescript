import os
from sqlalchemy import create_engine

PASSWORD = os.environ.get("SP_DB_PASSWORD", "YOUR_PASSWORD")
DB_URL = f"postgresql+psycopg://postgres:{PASSWORD}@localhost:5432/supplyprescript"
engine = create_engine(DB_URL)