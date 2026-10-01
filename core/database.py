import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    desc,
    UniqueConstraint
)
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///data/jobhunter.db"

# NullPool evita completamente TimeoutError: QueuePool limit reached en SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    poolclass=NullPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # linkedin, computrabajo, bumeran
    external_id = Column(String(250), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    company = Column(String(200), nullable=False)
    location = Column(String(200), default="Remoto")
    modality = Column(String(50), default="remote")  # remote, hybrid, onsite
    url = Column(Text, nullable=False)
    salary_snippet = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Matching / scoring para primer empleo
    match_score = Column(Float, default=0.0)
    match_reason = Column(Text, nullable=True)
    requirements_json = Column(Text, nullable=True)  # JSON completo con 'cumplimos', 'no_cumplimos', 'estrategia'
    requirements_fulfilled = Column(Text, nullable=True)  # JSON list de lo que sí cumplimos
    requirements_missing = Column(Text, nullable=True)    # JSON list de lo que no cumplimos
    strategy_notes = Column(Text, nullable=True)
    is_recommended = Column(Boolean, default=True)
    
    # Status: discovered, queued, applied, interview, rejected, discarded
    status = Column(String(50), default="discovered", index=True)
    created_at = Column(DateTime, default=datetime.now)
    applied_at = Column(DateTime, nullable=True)
    
    # Relación con logs de postulación y correos vinculados
    applications = relationship("ApplicationLog", back_populates="job", cascade="all, delete-orphan")
    emails = relationship("EmailMessage", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('platform', 'external_id', name='uq_platform_external_id'),
    )


class ApplicationLog(Base):
    __tablename__ = "application_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    platform = Column(String(50), nullable=False)
    questions_answers = Column(Text, nullable=True)  # JSON string
    status = Column(String(50), default="success")   # success, failed, requires_review
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    job = relationship("Job", back_populates="applications")


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    message_id = Column(String(250), unique=True, index=True)
    sender = Column(String(200), nullable=False)
    subject = Column(String(350), nullable=False)
    snippet = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    category = Column(String(50), default="other")  # interview_invite, coding_challenge, rejection, info
    confidence = Column(Float, default=0.0)
    received_at = Column(DateTime, default=datetime.now)
    action_url = Column(String(500), nullable=True)  # URL directa a prueba técnica o reunión
    
    # Actions
    action_taken = Column(String(50), default="pending")  # pending, draft_created, replied, ignored
    proposed_reply = Column(Text, nullable=True)
    sent_reply = Column(Text, nullable=True)
    replied_at = Column(DateTime, nullable=True)

    job = relationship("Job", back_populates="emails")


class AgentMetric(Base):
    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), index=True)  # YYYY-MM-DD
    platform = Column(String(50), index=True)
    jobs_scanned = Column(Integer, default=0)
    jobs_applied = Column(Integer, default=0)
    interviews_detected = Column(Integer, default=0)


class FreelanceProject(Base):
    __tablename__ = "freelance_projects"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # freelancer, getonbrd, workana, linkedin
    external_id = Column(String(250), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    client_name = Column(String(200), default="Cliente Freelance")
    budget = Column(String(150), nullable=True)  # ej. "$50 - $150 USD", "S/ 300 - 600 PEN"
    currency = Column(String(20), default="USD")
    category = Column(String(100), default="python_automation")  # python_automation, power_bi_data, qa_testing, sql_database, web_dev
    skills_json = Column(Text, nullable=True)  # list of tags in json
    url = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    generated_proposal = Column(Text, nullable=True)
    suggested_bid = Column(String(100), nullable=True)
    suggested_timeline = Column(String(100), nullable=True)
    status = Column(String(50), default="open", index=True)  # open, proposal_generated, applied, dismissed
    auto_applied = Column(Boolean, default=False, index=True)
    applied_at = Column(DateTime, nullable=True)
    bid_response_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('platform', 'external_id', name='uq_freelance_platform_ext_id'),
    )


class FreelanceAutoBidConfig(Base):
    """Configuración y reglas de seguridad para el modo 100% autónomo (Auto-Bid)."""
    __tablename__ = "freelance_autobid_config"

    id = Column(Integer, primary_key=True, default=1)
    is_enabled = Column(Boolean, default=False)
    min_hourly_rate = Column(Float, default=15.0)
    min_fixed_budget = Column(Float, default=50.0)
    max_daily_bids = Column(Integer, default=4)
    check_interval_seconds = Column(Integer, default=75)
    target_categories_json = Column(
        Text,
        default='["customer_support_whatsapp", "sales_setter_crm", "ai_chatbot_system", "social_media_growth", "ecommerce_stores", "virtual_assistant_admin", "power_bi_data", "qa_testing", "sql_database", "web_dev", "python_automation_scraping"]'
    )
    freelancer_api_token = Column(String(300), nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Migración defensiva para columnas nuevas en bases de datos existentes
    try:
        import sqlite3
        conn = sqlite3.connect("data/jobhunter.db")
        cur = conn.cursor()
        
        # Migración tabla jobs
        cols_jobs = [r[1] for r in cur.execute("PRAGMA table_info(jobs)").fetchall()]
        new_cols_jobs = [
            ("requirements_fulfilled", "TEXT"),
            ("requirements_missing", "TEXT"),
            ("strategy_notes", "TEXT"),
            ("is_recommended", "BOOLEAN DEFAULT 1")
        ]
        for col_name, col_type in new_cols_jobs:
            if col_name not in cols_jobs:
                cur.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")

        # Migración tabla freelance_projects
        cols_fl = [r[1] for r in cur.execute("PRAGMA table_info(freelance_projects)").fetchall()]
        new_cols_fl = [
            ("auto_applied", "BOOLEAN DEFAULT 0"),
            ("applied_at", "DATETIME"),
            ("bid_response_log", "TEXT")
        ]
        for col_name, col_type in new_cols_fl:
            if col_name not in cols_fl:
                cur.execute(f"ALTER TABLE freelance_projects ADD COLUMN {col_name} {col_type}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[init_db] Migración notice: {e}")

    # Inicializar registro de configuración por defecto de Auto-Bid si no existe
    try:
        db = SessionLocal()
        cfg = db.query(FreelanceAutoBidConfig).filter(FreelanceAutoBidConfig.id == 1).first()
        if not cfg:
            cfg = FreelanceAutoBidConfig(
                id=1,
                is_enabled=False,
                min_hourly_rate=15.0,
                min_fixed_budget=50.0,
                max_daily_bids=4,
                check_interval_seconds=75
            )
            db.add(cfg)
            db.commit()
        db.close()
    except Exception as e:
        print(f"[init_db] Config auto-bid init: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
