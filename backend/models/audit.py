from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text)
    result = Column(String(50))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ImportedDataset(Base):
    __tablename__ = "imported_datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500))
    file_format = Column(String(20))
    diseases_added = Column(Integer, default=0)
    diseases_updated = Column(Integer, default=0)
    symptoms_added = Column(Integer, default=0)
    links_added = Column(Integer, default=0)
    status = Column(String(50))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
