# app/data/base.py
import os

from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
Base = declarative_base()
engine = create_engine(DATABASE_URL)

