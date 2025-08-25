"""
Lean Database Models for VeriPay - Simplified schema for core functionality
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, Enum, JSON
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


class BankType(enum.Enum):
    """Bank type enumeration"""
    CBE = "cbe"
    TELEBIRR = "telebirr"
    DASHEN = "dashen"
    OTHER = "other"


class UserRole(enum.Enum):
    """User role enumeration"""
    WAITER = "waiter"
    ADMIN = "admin"


class User(Base):
    """Unified user model for waiters and admins"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    assigned_tables = relationship("TableAssignment", back_populates="user")


class Restaurant(Base):
    """Restaurant model"""
    __tablename__ = "restaurants"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    admin_telegram_id = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    tables = relationship("Table", back_populates="restaurant")
    transactions = relationship("Transaction", back_populates="restaurant")


class Table(Base):
    """Table model for restaurant tables"""
    __tablename__ = "tables"
    
    id = Column(Integer, primary_key=True)
    table_number = Column(String(20), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="tables")
    assignments = relationship("TableAssignment", back_populates="table")


class TableAssignment(Base):
    """Table assignment model linking users to tables"""
    __tablename__ = "table_assignments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    assigned_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="assigned_tables")
    table = relationship("Table", back_populates="assignments")


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
    
    # Verification details
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    verification_confidence = Column(Float)
    verification_notes = Column(Text)
    
    # Screenshot details
    screenshot_path = Column(String(500))
    screenshot_hash = Column(String(64))  # SHA256 hash for duplicate detection
    
    # OCR extracted data
    ocr_data = Column(JSON)
    ocr_confidence = Column(Float)
    
    # QR code verification (if present)
    qr_verified = Column(Boolean, default=False)
    qr_data = Column(JSON)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("tables.id"))
    
    user = relationship("User", back_populates="transactions")
    restaurant = relationship("Restaurant", back_populates="transactions")
    table = relationship("Table")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    verified_at = Column(DateTime)


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
    
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())


class ReconciliationReport(Base):
    """Reconciliation report model"""
    __tablename__ = "reconciliation_reports"
    
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
    bank_statement_id = Column(Integer, ForeignKey("bank_statements.id"))
    reconciliation_results = Column(JSON)
    
    # Report file
    report_file_path = Column(String(500))
    report_format = Column(String(10))  # pdf, excel, csv
    
    # Admin who generated the report
    admin_id = Column(Integer, ForeignKey("users.id"))
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