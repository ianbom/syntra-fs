"""Add processing_status and processing_error columns to documents table."""
from sqlalchemy import text
from app.database import engine

def migrate():
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) DEFAULT 'completed'"
        ))
        conn.execute(text(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_error TEXT"
        ))
        conn.commit()
    print("Migration complete: processing_status + processing_error columns added")

if __name__ == "__main__":
    migrate()
