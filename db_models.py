"""
Database models for Financial Document Analyzer
Handles user management, analysis tracking, and results storage
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
import os

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost/financial_analyzer"
)

engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()


class User(Base):
    """User model for tracking analysis requests"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Analysis(Base):
    """Analysis model for tracking document analysis requests"""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_id = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    status = Column(String, default="queued", nullable=False)  # queued, processing, completed, failed
    task_id = Column(String, unique=True, index=True, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="analyses")
    results = relationship("AnalysisResult", back_populates="analysis", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Analysis(id={self.id}, file_id={self.file_id}, status={self.status})>"


class AnalysisResult(Base):
    """Analysis results model for storing AI-generated analysis"""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    
    # Analysis results from each agent
    verification = Column(Text, nullable=True)
    financial_analysis = Column(Text, nullable=True)
    investment_recommendations = Column(Text, nullable=True)
    risk_assessment = Column(Text, nullable=True)
    
    # Metadata
    result_metadata = Column(JSONB, nullable=True)  # Additional structured data
    processing_time = Column(Integer, nullable=True)  # seconds
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("Analysis", back_populates="results")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, analysis_id={self.analysis_id})>"


class AuditLog(Base):
    """Audit log for tracking system events and user actions"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # upload, analyze, retrieve, delete, etc.
    resource_type = Column(String, nullable=False)  # analysis, result, etc.
    resource_id = Column(Integer, nullable=True)
    status = Column(String, nullable=False)  # success, failure
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully")


def get_db():
    """Get database session"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper functions for database operations

def create_user(db: Session, email: str) -> User:
    """Create a new user"""
    db_user = User(email=email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> User:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_analysis(
    db: Session,
    file_id: str,
    filename: str,
    query: str,
    user_id: int = None
) -> Analysis:
    """Create a new analysis record"""
    analysis = Analysis(
        file_id=file_id,
        filename=filename,
        query=query,
        user_id=user_id,
        status="queued"
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def update_analysis_status(
    db: Session,
    analysis_id: int,
    status: str,
    task_id: str = None,
    error_message: str = None
) -> Analysis:
    """Update analysis status"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis:
        analysis.status = status
        if task_id:
            analysis.task_id = task_id
        if error_message:
            analysis.error_message = error_message
        if status == "completed":
            analysis.completed_at = datetime.utcnow()
        analysis.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(analysis)
    return analysis


def create_analysis_result(
    db: Session,
    analysis_id: int,
    verification: str,
    financial_analysis: str,
    investment_recommendations: str,
    risk_assessment: str,
    metadata: dict = None,
    processing_time: int = None
) -> AnalysisResult:
    """Store analysis results"""
    result = AnalysisResult(
        analysis_id=analysis_id,
        verification=verification,
        financial_analysis=financial_analysis,
        investment_recommendations=investment_recommendations,
        risk_assessment=risk_assessment,
        metadata=metadata,
        processing_time=processing_time
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_analysis(db: Session, analysis_id: int) -> Analysis:
    """Get analysis by ID with results"""
    return db.query(Analysis).filter(Analysis.id == analysis_id).first()


def get_analysis_by_file_id(db: Session, file_id: str) -> Analysis:
    """Get analysis by file ID"""
    return db.query(Analysis).filter(Analysis.file_id == file_id).first()


def log_audit(
    db: Session,
    action: str,
    resource_type: str,
    status: str,
    user_id: int = None,
    resource_id: int = None,
    details: str = None,
    ip_address: str = None
) -> AuditLog:
    """Create audit log entry"""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        details=details,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()
    return audit
