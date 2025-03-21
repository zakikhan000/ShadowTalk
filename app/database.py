from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ---------------------------
# Database Setup
# ---------------------------
DATABASE_URL = "mssql+pyodbc://zaki:12365@DESKTOP-VMJ10VF\\SQLEXPRESS/WeShareDB?driver=ODBC+Driver+17+for+SQL+Server"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
