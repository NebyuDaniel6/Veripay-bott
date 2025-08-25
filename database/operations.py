"""
Database operations for VeriPay system
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, and_, or_, desc, func
from sqlalchemy.exc import IntegrityError
from .models import (
    Base, Waiter, Restaurant, Transaction, Admin, AuditReport,
    BankStatement, FraudPattern, SystemLog, APICache,
    VerificationStatus, BankType, TransactionType
)
import yaml
import hashlib
import json


class DatabaseManager:
    """Database manager for VeriPay operations"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize database connection"""
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        self.engine = create_engine(
            config['database']['url'],
            pool_size=config['database']['pool_size'],
            max_overflow=config['database']['max_overflow'],
            echo=config['database']['echo']
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()


class WaiterOperations:
    """Operations for waiter management"""
    
    @staticmethod
    def create_waiter(session: Session, telegram_id: str, name: str, 
                     phone: str = None, restaurant_id: int = None) -> Waiter:
        """Create a new waiter"""
        waiter = Waiter(
            telegram_id=telegram_id,
            name=name,
            phone=phone,
            restaurant_id=restaurant_id
        )
        session.add(waiter)
        session.commit()
        session.refresh(waiter)
        return waiter
    
    @staticmethod
    def get_waiter_by_telegram_id(session: Session, telegram_id: str) -> Optional[Waiter]:
        """Get waiter by Telegram ID"""
        return session.query(Waiter).filter(Waiter.telegram_id == telegram_id).first()
    
    @staticmethod
    def get_waiters_by_restaurant(session: Session, restaurant_id: int) -> List[Waiter]:
        """Get all waiters for a restaurant"""
        return session.query(Waiter).filter(
            Waiter.restaurant_id == restaurant_id,
            Waiter.is_active == True
        ).all()
    
    @staticmethod
    def update_waiter(session: Session, waiter_id: int, **kwargs) -> Optional[Waiter]:
        """Update waiter information"""
        waiter = session.query(Waiter).filter(Waiter.id == waiter_id).first()
        if waiter:
            for key, value in kwargs.items():
                if hasattr(waiter, key):
                    setattr(waiter, key, value)
            waiter.updated_at = datetime.now()
            session.commit()
            session.refresh(waiter)
        return waiter


class RestaurantOperations:
    """Operations for restaurant management"""
    
    @staticmethod
    def create_restaurant(session: Session, name: str, address: str = None,
                         phone: str = None, email: str = None, 
                         admin_telegram_id: str = None) -> Restaurant:
        """Create a new restaurant"""
        restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            email=email,
            admin_telegram_id=admin_telegram_id
        )
        session.add(restaurant)
        session.commit()
        session.refresh(restaurant)
        return restaurant
    
    @staticmethod
    def get_restaurant_by_id(session: Session, restaurant_id: int) -> Optional[Restaurant]:
        """Get restaurant by ID"""
        return session.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    
    @staticmethod
    def get_restaurant_by_admin(session: Session, admin_telegram_id: str) -> Optional[Restaurant]:
        """Get restaurant by admin Telegram ID"""
        return session.query(Restaurant).filter(
            Restaurant.admin_telegram_id == admin_telegram_id,
            Restaurant.is_active == True
        ).first()


class TransactionOperations:
    """Operations for transaction management"""
    
    @staticmethod
    def create_transaction(session: Session, stn_number: str, amount: float,
                          waiter_id: int, restaurant_id: int, bank_type: BankType,
                          sender_account: str = None, receiver_account: str = None,
                          transaction_date: datetime = None, screenshot_path: str = None) -> Transaction:
        """Create a new transaction"""
        # Generate screenshot hash if path provided
        screenshot_hash = None
        if screenshot_path:
            screenshot_hash = TransactionOperations._generate_file_hash(screenshot_path)
        
        transaction = Transaction(
            stn_number=stn_number,
            amount=amount,
            sender_account=sender_account,
            receiver_account=receiver_account,
            transaction_date=transaction_date or datetime.now(),
            bank_type=bank_type,
            waiter_id=waiter_id,
            restaurant_id=restaurant_id,
            screenshot_path=screenshot_path,
            screenshot_hash=screenshot_hash
        )
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction
    
    @staticmethod
    def get_transaction_by_id(session: Session, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID"""
        return session.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    @staticmethod
    def get_transactions_by_waiter(session: Session, waiter_id: int, 
                                 limit: int = 50) -> List[Transaction]:
        """Get transactions by waiter"""
        return session.query(Transaction).filter(
            Transaction.waiter_id == waiter_id
        ).order_by(desc(Transaction.created_at)).limit(limit).all()
    
    @staticmethod
    def get_transactions_by_restaurant(session: Session, restaurant_id: int,
                                     status: VerificationStatus = None,
                                     start_date: datetime = None,
                                     end_date: datetime = None) -> List[Transaction]:
        """Get transactions by restaurant with optional filters"""
        query = session.query(Transaction).filter(Transaction.restaurant_id == restaurant_id)
        
        if status:
            query = query.filter(Transaction.verification_status == status)
        
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)
        
        return query.order_by(desc(Transaction.created_at)).all()
    
    @staticmethod
    def update_transaction_status(session: Session, transaction_id: int,
                                status: VerificationStatus, confidence: float = None,
                                notes: str = None, admin_id: int = None) -> Optional[Transaction]:
        """Update transaction verification status"""
        transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.verification_status = status
            transaction.verification_confidence = confidence
            transaction.verification_notes = notes
            transaction.admin_id = admin_id
            transaction.verified_at = datetime.now()
            transaction.updated_at = datetime.now()
            session.commit()
            session.refresh(transaction)
        return transaction
    
    @staticmethod
    def update_ocr_data(session: Session, transaction_id: int, ocr_data: Dict,
                       confidence: float) -> Optional[Transaction]:
        """Update transaction OCR data"""
        transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.ocr_data = ocr_data
            transaction.ocr_confidence = confidence
            session.commit()
            session.refresh(transaction)
        return transaction
    
    @staticmethod
    def update_fraud_detection(session: Session, transaction_id: int, fraud_score: float,
                              fraud_indicators: List[str]) -> Optional[Transaction]:
        """Update fraud detection results"""
        transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.fraud_score = fraud_score
            transaction.fraud_indicators = fraud_indicators
            session.commit()
            session.refresh(transaction)
        return transaction
    
    @staticmethod
    def update_bank_verification(session: Session, transaction_id: int, verified: bool,
                               response: Dict) -> Optional[Transaction]:
        """Update bank verification results"""
        transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.bank_verified = verified
            transaction.bank_response = response
            session.commit()
            session.refresh(transaction)
        return transaction
    
    @staticmethod
    def check_duplicate_screenshot(session: Session, screenshot_hash: str) -> Optional[Transaction]:
        """Check for duplicate screenshot"""
        return session.query(Transaction).filter(
            Transaction.screenshot_hash == screenshot_hash
        ).first()
    
    @staticmethod
    def _generate_file_hash(file_path: str) -> str:
        """Generate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class AdminOperations:
    """Operations for admin management"""
    
    @staticmethod
    def create_admin(session: Session, telegram_id: str, name: str,
                    email: str = None, phone: str = None, 
                    is_super_admin: bool = False) -> Admin:
        """Create a new admin"""
        admin = Admin(
            telegram_id=telegram_id,
            name=name,
            email=email,
            phone=phone,
            is_super_admin=is_super_admin
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin
    
    @staticmethod
    def get_admin_by_telegram_id(session: Session, telegram_id: str) -> Optional[Admin]:
        """Get admin by Telegram ID"""
        return session.query(Admin).filter(Admin.telegram_id == telegram_id).first()
    
    @staticmethod
    def is_admin(session: Session, telegram_id: str) -> bool:
        """Check if user is admin"""
        admin = session.query(Admin).filter(
            Admin.telegram_id == telegram_id,
            Admin.is_active == True
        ).first()
        return admin is not None


class AuditOperations:
    """Operations for audit and reporting"""
    
    @staticmethod
    def create_audit_report(session: Session, report_date: datetime,
                           period_start: datetime, period_end: datetime,
                           admin_id: int, report_file_path: str = None,
                           report_format: str = "pdf") -> AuditReport:
        """Create a new audit report"""
        # Calculate statistics
        transactions = session.query(Transaction).filter(
            and_(
                Transaction.created_at >= period_start,
                Transaction.created_at <= period_end
            )
        ).all()
        
        total = len(transactions)
        verified = len([t for t in transactions if t.verification_status == VerificationStatus.VERIFIED])
        failed = len([t for t in transactions if t.verification_status == VerificationStatus.FAILED])
        suspicious = len([t for t in transactions if t.verification_status == VerificationStatus.SUSPICIOUS])
        
        report = AuditReport(
            report_date=report_date,
            report_period_start=period_start,
            report_period_end=period_end,
            total_transactions=total,
            verified_transactions=verified,
            failed_transactions=failed,
            suspicious_transactions=suspicious,
            admin_id=admin_id,
            report_file_path=report_file_path,
            report_format=report_format
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return report
    
    @staticmethod
    def get_audit_reports(session: Session, admin_id: int = None,
                         limit: int = 20) -> List[AuditReport]:
        """Get audit reports"""
        query = session.query(AuditReport)
        if admin_id:
            query = query.filter(AuditReport.admin_id == admin_id)
        return query.order_by(desc(AuditReport.created_at)).limit(limit).all()


class SystemLogOperations:
    """Operations for system logging"""
    
    @staticmethod
    def log_event(session: Session, level: str, message: str, module: str = None,
                  function: str = None, line_number: int = None, user_id: str = None,
                  additional_data: Dict = None):
        """Log a system event"""
        log_entry = SystemLog(
            level=level,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            user_id=user_id,
            additional_data=additional_data
        )
        session.add(log_entry)
        session.commit()
    
    @staticmethod
    def get_logs(session: Session, level: str = None, user_id: str = None,
                 start_date: datetime = None, end_date: datetime = None,
                 limit: int = 100) -> List[SystemLog]:
        """Get system logs with filters"""
        query = session.query(SystemLog)
        
        if level:
            query = query.filter(SystemLog.level == level)
        
        if user_id:
            query = query.filter(SystemLog.user_id == user_id)
        
        if start_date:
            query = query.filter(SystemLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(SystemLog.created_at <= end_date)
        
        return query.order_by(desc(SystemLog.created_at)).limit(limit).all()


class CacheOperations:
    """Operations for API caching"""
    
    @staticmethod
    def set_cache(session: Session, key: str, value: Any, ttl_seconds: int = 3600):
        """Set cache value"""
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        
        # Check if key exists
        existing = session.query(APICache).filter(APICache.cache_key == key).first()
        if existing:
            existing.cache_value = value
            existing.expires_at = expires_at
        else:
            cache_entry = APICache(
                cache_key=key,
                cache_value=value,
                expires_at=expires_at
            )
            session.add(cache_entry)
        
        session.commit()
    
    @staticmethod
    def get_cache(session: Session, key: str) -> Optional[Any]:
        """Get cache value"""
        cache_entry = session.query(APICache).filter(
            and_(
                APICache.cache_key == key,
                APICache.expires_at > datetime.now()
            )
        ).first()
        
        return cache_entry.cache_value if cache_entry else None
    
    @staticmethod
    def clear_expired_cache(session: Session):
        """Clear expired cache entries"""
        session.query(APICache).filter(APICache.expires_at <= datetime.now()).delete()
        session.commit() 