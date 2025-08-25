"""
Database models for VeriPay system
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, Enum, JSON, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class VerificationStatus(enum.Enum):
    """Verification status enumeration"""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    SUSPICIOUS = "suspicious"
    OVERRIDDEN = "overridden"


class BankType(enum.Enum):
    """Bank type enumeration"""
    CBE = "cbe"
    TELEBIRR = "telebirr"
    DASHEN = "dashen"
    OTHER = "other"


class TransactionType(enum.Enum):
    """Transaction type enumeration"""
    PAYMENT = "payment"
    REFUND = "refund"
    TRANSFER = "transfer"


class Waiter(Base):
    """Waiter/Staff member model"""
    __tablename__ = "waiters"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="waiter")
    restaurant = relationship("Restaurant", back_populates="waiters")


class Restaurant(Base):
    """Restaurant/Service provider model"""
    __tablename__ = "restaurants"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(100))
    admin_telegram_id = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    waiters = relationship("Waiter", back_populates="restaurant")
    transactions = relationship("Transaction", back_populates="restaurant")


class Transaction(Base):
    """Transaction model for payment verifications"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    stn_number = Column(String(100), nullable=False)  # Transaction reference
    amount = Column(Float, nullable=False)
    sender_account = Column(String(100))
    receiver_account = Column(String(100))
    transaction_date = Column(DateTime)
    bank_type = Column(Enum(BankType), nullable=False)
    transaction_type = Column(Enum(TransactionType), default=TransactionType.PAYMENT)
    
    # Verification details
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    verification_confidence = Column(Float)
    verification_notes = Column(Text)
    
    # Screenshot details
    screenshot_path = Column(String(500))
    screenshot_hash = Column(String(64))  # SHA256 hash for duplicate detection
    
    # Fraud detection results
    fraud_score = Column(Float)
    fraud_indicators = Column(JSON)  # List of detected fraud indicators
    
    # OCR extracted data
    ocr_data = Column(JSON)
    ocr_confidence = Column(Float)
    
    # Bank API verification
    bank_verified = Column(Boolean, default=False)
    bank_response = Column(JSON)
    
    # Relationships
    waiter_id = Column(Integer, ForeignKey("waiters.id"))
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    admin_id = Column(Integer, ForeignKey("admins.id"))
    
    waiter = relationship("Waiter", back_populates="transactions")
    restaurant = relationship("Restaurant", back_populates="transactions")
    admin = relationship("Admin", back_populates="transactions")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    verified_at = Column(DateTime)


class Admin(Base):
    """Admin/Manager model"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    phone = Column(String(20))
    is_super_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="admin")
    audit_reports = relationship("AuditReport", back_populates="admin")


class AuditReport(Base):
    """Audit report model for reconciliation"""
    __tablename__ = "audit_reports"
    
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, nullable=False)
    report_period_start = Column(DateTime, nullable=False)
    report_period_end = Column(DateTime, nullable=False)
    
    # Report statistics
    total_transactions = Column(Integer, default=0)
    verified_transactions = Column(Integer, default=0)
    failed_transactions = Column(Integer, default=0)
    suspicious_transactions = Column(Integer, default=0)
    
    # Reconciliation results
    bank_statement_path = Column(String(500))
    reconciliation_results = Column(JSON)
    
    # Report file
    report_file_path = Column(String(500))
    report_format = Column(String(10))  # pdf, excel, csv
    
    # Admin who generated the report
    admin_id = Column(Integer, ForeignKey("admins.id"))
    admin = relationship("Admin", back_populates="audit_reports")
    
    created_at = Column(DateTime, default=func.now())


class BankStatement(Base):
    """Bank statement model for reconciliation"""
    __tablename__ = "bank_statements"
    
    id = Column(Integer, primary_key=True)
    statement_date = Column(DateTime, nullable=False)
    bank_type = Column(Enum(BankType), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64))  # SHA256 hash
    
    # Parsed data
    parsed_data = Column(JSON)
    total_amount = Column(Float)
    transaction_count = Column(Integer)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_notes = Column(Text)
    
    uploaded_by = Column(Integer, ForeignKey("admins.id"))
    created_at = Column(DateTime, default=func.now())


class FraudPattern(Base):
    """Fraud pattern model for ML training"""
    __tablename__ = "fraud_patterns"
    
    id = Column(Integer, primary_key=True)
    pattern_type = Column(String(50), nullable=False)  # screenshot_manipulation, duplicate, etc.
    pattern_data = Column(JSON)
    confidence_score = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class SystemLog(Base):
    """System log model for monitoring"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    module = Column(String(100))
    function = Column(String(100))
    line_number = Column(Integer)
    user_id = Column(String(50))  # Telegram ID of user who triggered the log
    additional_data = Column(JSON)
    created_at = Column(DateTime, default=func.now())


class APICache(Base):
    """API cache model for performance optimization"""
    __tablename__ = "api_cache"
    
    id = Column(Integer, primary_key=True)
    cache_key = Column(String(200), unique=True, nullable=False)
    cache_value = Column(JSON)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now()) 