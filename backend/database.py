import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_schema()


def _ensure_sqlite_schema():
    if engine.url.get_backend_name() != "sqlite":
        return

    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = inspector.get_table_names()
        
        # Add necessary indexes safely if they don't exist
        try:
            if "disease_symptoms_link" in table_names:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disease_symptoms_link_disease_id ON disease_symptoms_link (disease_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disease_symptoms_link_symptom_id ON disease_symptoms_link (symptom_id)"))
            
            if "symptom_aliases" in table_names:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_symptom_aliases_symptom_id ON symptom_aliases (symptom_id)"))
            
            if "diagnosis_sessions" in table_names:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_diagnosis_sessions_patient_id ON diagnosis_sessions (patient_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_diagnosis_sessions_created_at ON diagnosis_sessions (created_at)"))
                
                columns = {col["name"] for col in inspector.get_columns("diagnosis_sessions")}
                if "llm_explanation" not in columns:
                    conn.execute(text("ALTER TABLE diagnosis_sessions ADD COLUMN llm_explanation TEXT"))
        except Exception as e:
            print(f"Lỗi khi thêm schema/index an toàn: {e}")
