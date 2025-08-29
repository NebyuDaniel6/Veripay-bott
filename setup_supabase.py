#!/usr/bin/env python3
"""
VeriPay Bot - Supabase Database Setup Script
Initializes the database with tables and demo data
"""

import os
import sys
import yaml
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.lean_models import Base, User, Restaurant, Table, TableAssignment, Transaction, BankStatement, ReconciliationReport, SystemLog, UserRole, BankType, VerificationStatus
from database.lean_operations import UserOperations, RestaurantOperations, TableOperations, TransactionOperations, BankStatementOperations, SystemLogOperations

def load_config():
    """Load configuration from environment or config file"""
    # First check environment variable
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        config = {
            'database': {
                'url': database_url
            }
        }
        return config
    
    # Fallback to config file
    config = {
        'database': {
            'url': 'sqlite:///lean_veripay.db'
        }
    }
    
    # Try to load from config file
    config_file = 'config_supabase.yaml'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = yaml.safe_load(f)
                if 'database' in file_config:
                    config['database'] = file_config['database']
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    return config

def create_tables(engine):
    """Create all database tables"""
    print("🗄️  Creating database tables...")
    
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    return True

def create_demo_data(session):
    """Create demo data for testing"""
    print("📊 Creating demo data...")
    
    try:
        # Create demo restaurant
        restaurant = Restaurant(
            name="Demo Restaurant",
            address="Addis Ababa, Ethiopia",
            admin_telegram_id="123456789",
            created_at=datetime.now()
        )
        session.add(restaurant)
        session.flush()  # Get the ID
        
        # Create demo admin user
        admin_user = User(
            telegram_id="123456789",
            name="Demo Admin",
            phone="+251911234567",
            role=UserRole.ADMIN,
            created_at=datetime.now()
        )
        session.add(admin_user)
        
        # Create demo waiter user
        waiter_user = User(
            telegram_id="369249230",
            name="Demo Waiter",
            phone="+251922345678",
            role=UserRole.WAITER,
            created_at=datetime.now()
        )
        session.add(waiter_user)
        session.flush()  # Get the user IDs
        
        # Create demo tables
        for i in range(1, 6):
            table = Table(
                restaurant_id=restaurant.id,
                table_number=f"T{i}",
                is_active=True,
                created_at=datetime.now()
            )
            session.add(table)
        
        session.flush()  # Get the table IDs
        
        # Create demo transactions
        demo_transactions = [
            {
                'stn_number': 'TXN001',
                'amount': 150.00,
                'sender_account': '1234567890',
                'receiver_account': '0987654321',
                'transaction_date': datetime.now(),
                'bank_type': BankType.CBE,
                'verification_status': VerificationStatus.VERIFIED,
                'user_id': waiter_user.id,
                'restaurant_id': restaurant.id,
                'table_id': 1
            },
            {
                'stn_number': 'TXN002',
                'amount': 250.00,
                'sender_account': '1234567890',
                'receiver_account': '0987654321',
                'transaction_date': datetime.now(),
                'bank_type': BankType.DASHEN,
                'verification_status': VerificationStatus.PENDING,
                'user_id': waiter_user.id,
                'restaurant_id': restaurant.id,
                'table_id': 2
            },
            {
                'stn_number': 'TXN003',
                'amount': 300.00,
                'sender_account': '1234567890',
                'receiver_account': '0987654321',
                'transaction_date': datetime.now(),
                'bank_type': BankType.TELEBIRR,
                'verification_status': VerificationStatus.VERIFIED,
                'user_id': waiter_user.id,
                'restaurant_id': restaurant.id,
                'table_id': 3
            }
        ]
        
        for tx_data in demo_transactions:
            transaction = Transaction(
                stn_number=tx_data['stn_number'],
                amount=tx_data['amount'],
                sender_account=tx_data['sender_account'],
                receiver_account=tx_data['receiver_account'],
                transaction_date=tx_data['transaction_date'],
                bank_type=tx_data['bank_type'],
                verification_status=tx_data['verification_status'],
                user_id=tx_data['user_id'],
                restaurant_id=tx_data['restaurant_id'],
                table_id=tx_data['table_id'],
                created_at=datetime.now()
            )
            session.add(transaction)
        
        # Create demo bank statement
        bank_statement = BankStatement(
            statement_date=datetime.now(),
            bank_type=BankType.CBE,
            file_path='/tmp/demo_statement.pdf',
            total_amount=700.00,
            transaction_count=3,
            uploaded_by=admin_user.id,
            created_at=datetime.now()
        )
        session.add(bank_statement)
        session.flush()  # Get the bank statement ID
        
        # Create demo reconciliation report
        reconciliation_report = ReconciliationReport(
            report_date=datetime.now(),
            report_period_start=datetime.now() - timedelta(days=7),
            report_period_end=datetime.now(),
            total_transactions=3,
            verified_transactions=2,
            failed_transactions=0,
            suspicious_transactions=0,
            bank_statement_id=bank_statement.id,
            admin_id=admin_user.id,
            created_at=datetime.now()
        )
        session.add(reconciliation_report)
        
        # Create demo system logs
        demo_logs = [
            {'level': 'INFO', 'message': 'System initialized', 'user_id': '123456789', 'module': 'setup'},
            {'level': 'INFO', 'message': 'Demo data created', 'user_id': '123456789', 'module': 'setup'},
            {'level': 'INFO', 'message': 'Database setup completed', 'user_id': '123456789', 'module': 'setup'}
        ]
        
        for log_data in demo_logs:
            system_log = SystemLog(
                level=log_data['level'],
                message=log_data['message'],
                user_id=log_data['user_id'],
                module=log_data['module'],
                created_at=datetime.now()
            )
            session.add(system_log)
        
        session.commit()
        print("✅ Demo data created successfully")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating demo data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def verify_setup(session):
    """Verify the setup by checking data"""
    print("🔍 Verifying setup...")
    
    try:
        # Check users
        users = session.query(User).all()
        print(f"✅ Found {len(users)} users")
        
        # Check restaurants
        restaurants = session.query(Restaurant).all()
        print(f"✅ Found {len(restaurants)} restaurants")
        
        # Check transactions
        transactions = session.query(Transaction).all()
        print(f"✅ Found {len(transactions)} transactions")
        
        # Check tables
        tables = session.query(Table).all()
        print(f"✅ Found {len(tables)} tables")
        
        print("✅ Setup verification completed")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying setup: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 VeriPay Bot - Supabase Database Setup")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    database_url = config['database']['url']
    
    print(f"📡 Database URL: {database_url}")
    
    # Create engine
    try:
        engine = create_engine(database_url)
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Create tables
        if not create_tables(engine):
            return False
        
        # Create demo data
        if not create_demo_data(session):
            return False
        
        # Verify setup
        if not verify_setup(session):
            return False
        
        print("\n🎉 Setup completed successfully!")
        print("\n📊 Demo Data Summary:")
        print("- 1 Restaurant: Demo Restaurant")
        print("- 2 Users: Demo Admin, Demo Waiter")
        print("- 5 Tables: T1-T5")
        print("- 3 Transactions: 2 verified, 1 pending")
        print("- 1 Bank Statement")
        print("- 1 Reconciliation Report")
        print("- 3 System Logs")
        
        print("\n🔧 Next Steps:")
        print("1. Set up your Telegram bot token")
        print("2. Deploy to Railway/Render")
        print("3. Test the bot functionality")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    finally:
        session.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 