"""
Lean Database Operations for VeriPay - Simplified operations for core functionality
"""
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Optional, Tuple
import yaml
from loguru import logger

from .lean_models import (
    Base, User, Restaurant, Table, TableAssignment, Transaction, 
    BankStatement, ReconciliationReport, SystemLog,
    UserRole, VerificationStatus, BankType
)


class LeanDatabaseManager:
    """Simplified database manager for lean VeriPay model"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize database manager"""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Create database engine
        self.engine = create_engine(
            self.config['database']['url'],
            pool_size=self.config['database']['pool_size'],
            max_overflow=self.config['database']['max_overflow'],
            echo=self.config['database']['echo']
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """Close database session"""
        session.close()


class UserOperations:
    """User management operations"""
    
    @staticmethod
    def create_user(session: Session, telegram_id: str, name: str, role: UserRole, 
                   phone: str = None) -> User:
        """Create a new user"""
        try:
            user = User(
                telegram_id=telegram_id,
                name=name,
                phone=phone,
                role=role,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"Created user: {name} ({role.value})")
            return user
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    @staticmethod
    def get_user_by_telegram_id(session: Session, telegram_id: str) -> Optional[User]:
        """Get user by Telegram ID"""
        try:
            return session.query(User).filter(
                User.telegram_id == telegram_id,
                User.is_active == True
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    @staticmethod
    def get_users_by_role(session: Session, role: UserRole) -> List[User]:
        """Get all users by role"""
        try:
            return session.query(User).filter(
                User.role == role,
                User.is_active == True
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting users by role: {e}")
            return []
    
    @staticmethod
    def update_user(session: Session, telegram_id: str, **kwargs) -> bool:
        """Update user information"""
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.updated_at = datetime.now()
                session.commit()
                logger.info(f"Updated user: {telegram_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating user: {e}")
            return False
    
    @staticmethod
    def deactivate_user(session: Session, telegram_id: str) -> bool:
        """Deactivate user"""
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.is_active = False
                user.updated_at = datetime.now()
                session.commit()
                logger.info(f"Deactivated user: {telegram_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error deactivating user: {e}")
            return False


class RestaurantOperations:
    """Restaurant management operations"""
    
    @staticmethod
    def create_restaurant(session: Session, name: str, admin_telegram_id: str,
                         address: str = None, phone: str = None) -> Restaurant:
        """Create a new restaurant"""
        try:
            restaurant = Restaurant(
                name=name,
                address=address,
                phone=phone,
                admin_telegram_id=admin_telegram_id,
                is_active=True
            )
            session.add(restaurant)
            session.commit()
            session.refresh(restaurant)
            
            logger.info(f"Created restaurant: {name}")
            return restaurant
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating restaurant: {e}")
            raise
    
    @staticmethod
    def get_restaurant_by_admin(session: Session, admin_telegram_id: str) -> Optional[Restaurant]:
        """Get restaurant by admin Telegram ID"""
        try:
            return session.query(Restaurant).filter(
                Restaurant.admin_telegram_id == admin_telegram_id,
                Restaurant.is_active == True
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting restaurant: {e}")
            return None
    
    @staticmethod
    def get_all_restaurants(session: Session) -> List[Restaurant]:
        """Get all active restaurants"""
        try:
            return session.query(Restaurant).filter(Restaurant.is_active == True).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting restaurants: {e}")
            return []


class TableOperations:
    """Table management operations"""
    
    @staticmethod
    def create_table(session: Session, table_number: str, restaurant_id: int) -> Table:
        """Create a new table"""
        try:
            table = Table(
                table_number=table_number,
                restaurant_id=restaurant_id,
                is_active=True
            )
            session.add(table)
            session.commit()
            session.refresh(table)
            
            logger.info(f"Created table: {table_number}")
            return table
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating table: {e}")
            raise
    
    @staticmethod
    def assign_table_to_user(session: Session, user_id: int, table_id: int) -> TableAssignment:
        """Assign table to user"""
        try:
            # Deactivate any existing assignments for this user
            session.query(TableAssignment).filter(
                TableAssignment.user_id == user_id,
                TableAssignment.is_active == True
            ).update({"is_active": False})
            
            # Create new assignment
            assignment = TableAssignment(
                user_id=user_id,
                table_id=table_id,
                is_active=True
            )
            session.add(assignment)
            session.commit()
            session.refresh(assignment)
            
            logger.info(f"Assigned table {table_id} to user {user_id}")
            return assignment
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error assigning table: {e}")
            raise
    
    @staticmethod
    def get_user_tables(session: Session, user_id: int) -> List[Table]:
        """Get tables assigned to user"""
        try:
            return session.query(Table).join(TableAssignment).filter(
                TableAssignment.user_id == user_id,
                TableAssignment.is_active == True,
                Table.is_active == True
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user tables: {e}")
            return []


class TransactionOperations:
    """Transaction management operations"""
    
    @staticmethod
    def create_transaction(session: Session, stn_number: str, amount: float,
                          user_id: int, restaurant_id: int, bank_type: BankType,
                          screenshot_path: str = None, ocr_data: dict = None,
                          table_id: int = None, **kwargs) -> Transaction:
        """Create a new transaction"""
        try:
            transaction = Transaction(
                stn_number=stn_number,
                amount=amount,
                user_id=user_id,
                restaurant_id=restaurant_id,
                bank_type=bank_type,
                screenshot_path=screenshot_path,
                ocr_data=ocr_data,
                table_id=table_id,
                verification_status=VerificationStatus.PENDING,
                **kwargs
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            
            logger.info(f"Created transaction: {stn_number}")
            return transaction
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating transaction: {e}")
            raise
    
    @staticmethod
    def get_user_transactions(session: Session, user_id: int, 
                            days: int = 30) -> List[Transaction]:
        """Get transactions for a user within specified days"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            return session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.created_at >= start_date
            ).order_by(Transaction.created_at.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user transactions: {e}")
            return []
    
    @staticmethod
    def get_restaurant_transactions(session: Session, restaurant_id: int,
                                  start_date: datetime = None,
                                  end_date: datetime = None) -> List[Transaction]:
        """Get transactions for a restaurant within date range"""
        try:
            query = session.query(Transaction).filter(
                Transaction.restaurant_id == restaurant_id
            )
            
            if start_date:
                query = query.filter(Transaction.created_at >= start_date)
            if end_date:
                query = query.filter(Transaction.created_at <= end_date)
            
            return query.order_by(Transaction.created_at.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting restaurant transactions: {e}")
            return []
    
    @staticmethod
    def update_transaction_status(session: Session, transaction_id: int,
                                status: VerificationStatus, **kwargs) -> bool:
        """Update transaction verification status"""
        try:
            transaction = session.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()
            
            if transaction:
                transaction.verification_status = status
                transaction.verified_at = datetime.now()
                
                for key, value in kwargs.items():
                    if hasattr(transaction, key):
                        setattr(transaction, key, value)
                
                session.commit()
                logger.info(f"Updated transaction {transaction_id} status to {status.value}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating transaction status: {e}")
            return False
    
    @staticmethod
    def get_daily_summary(session: Session, restaurant_id: int,
                         date: datetime = None) -> Dict:
        """Get daily transaction summary"""
        try:
            if not date:
                date = datetime.now()
            
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            transactions = session.query(Transaction).filter(
                Transaction.restaurant_id == restaurant_id,
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date
            ).all()
            
            # Calculate summary
            total_transactions = len(transactions)
            total_amount = sum(t.amount for t in transactions)
            verified_count = len([t for t in transactions if t.verification_status == VerificationStatus.VERIFIED])
            verified_amount = sum(t.amount for t in transactions if t.verification_status == VerificationStatus.VERIFIED)
            
            # Group by payment method
            payment_methods = {}
            for t in transactions:
                bank_type = t.bank_type.value
                if bank_type not in payment_methods:
                    payment_methods[bank_type] = {"count": 0, "amount": 0}
                payment_methods[bank_type]["count"] += 1
                payment_methods[bank_type]["amount"] += t.amount
            
            # Group by waiter
            waiters = {}
            for t in transactions:
                waiter_name = t.user.name if t.user else "Unknown"
                if waiter_name not in waiters:
                    waiters[waiter_name] = {"count": 0, "amount": 0}
                waiters[waiter_name]["count"] += 1
                waiters[waiter_name]["amount"] += t.amount
            
            return {
                "date": date.date(),
                "total_transactions": total_transactions,
                "total_amount": total_amount,
                "verified_transactions": verified_count,
                "verified_amount": verified_amount,
                "pending_transactions": total_transactions - verified_count,
                "payment_methods": payment_methods,
                "waiters": waiters
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting daily summary: {e}")
            return {}


class BankStatementOperations:
    """Bank statement operations"""
    
    @staticmethod
    def create_bank_statement(session: Session, statement_date: datetime,
                             bank_type: BankType, file_path: str,
                             uploaded_by: int) -> BankStatement:
        """Create a new bank statement record"""
        try:
            statement = BankStatement(
                statement_date=statement_date,
                bank_type=bank_type,
                file_path=file_path,
                uploaded_by=uploaded_by
            )
            session.add(statement)
            session.commit()
            session.refresh(statement)
            
            logger.info(f"Created bank statement: {file_path}")
            return statement
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating bank statement: {e}")
            raise
    
    @staticmethod
    def update_statement_processing(session: Session, statement_id: int,
                                  parsed_data: dict, total_amount: float,
                                  transaction_count: int) -> bool:
        """Update statement processing results"""
        try:
            statement = session.query(BankStatement).filter(
                BankStatement.id == statement_id
            ).first()
            
            if statement:
                statement.parsed_data = parsed_data
                statement.total_amount = total_amount
                statement.transaction_count = transaction_count
                statement.is_processed = True
                session.commit()
                
                logger.info(f"Updated statement processing: {statement_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating statement processing: {e}")
            return False


class SystemLogOperations:
    """System logging operations"""
    
    @staticmethod
    def log_event(session: Session, level: str, message: str, user_id: str = None,
                  module: str = None, function: str = None, line_number: int = None,
                  additional_data: dict = None):
        """Log system event"""
        try:
            log_entry = SystemLog(
                level=level,
                message=message,
                user_id=user_id,
                module=module,
                function=function,
                line_number=line_number,
                additional_data=additional_data
            )
            session.add(log_entry)
            session.commit()
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error logging event: {e}")
    
    @staticmethod
    def get_recent_logs(session: Session, hours: int = 24) -> List[SystemLog]:
        """Get recent system logs"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            return session.query(SystemLog).filter(
                SystemLog.created_at >= start_time
            ).order_by(SystemLog.created_at.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent logs: {e}")
            return [] 