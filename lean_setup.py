#!/usr/bin/env python3
"""
Lean VeriPay Setup Script - Simplified setup for core functionality
"""
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.lean_operations import (
    LeanDatabaseManager, UserOperations, RestaurantOperations, 
    TableOperations, TransactionOperations, SystemLogOperations
)
from database.lean_models import UserRole, BankType, VerificationStatus


class LeanVeriPaySetup:
    """Setup class for lean VeriPay system"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize setup"""
        self.config_path = config_path
        self.db_manager = LeanDatabaseManager(config_path)
        
        # Create necessary directories
        Path('uploads').mkdir(exist_ok=True)
        Path('logs').mkdir(exist_ok=True)
        Path('reports').mkdir(exist_ok=True)
        Path('backups').mkdir(exist_ok=True)
    
    def setup_database(self):
        """Setup database tables"""
        print("🗄️  Setting up database...")
        
        try:
            # Database tables are created automatically when LeanDatabaseManager is initialized
            print("✅ Database tables created successfully")
            return True
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
            return False
    
    def create_demo_data(self):
        """Create demo data for testing"""
        print("🎭 Creating demo data...")
        
        session = self.db_manager.get_session()
        
        try:
            # Create demo restaurant
            restaurant = RestaurantOperations.create_restaurant(
                session=session,
                name="Demo Restaurant",
                admin_telegram_id="123456789",
                address="Addis Ababa, Ethiopia",
                phone="+251911234567"
            )
            print(f"✅ Created demo restaurant: {restaurant.name}")
            
            # Create demo tables
            tables = []
            for i in range(1, 11):  # 10 tables
                table = TableOperations.create_table(
                    session=session,
                    table_number=f"T{i:02d}",
                    restaurant_id=restaurant.id
                )
                tables.append(table)
            print(f"✅ Created {len(tables)} demo tables")
            
            # Create demo users
            demo_users = [
                {
                    "telegram_id": "123456789",
                    "name": "Admin User",
                    "role": UserRole.ADMIN,
                    "phone": "+251911234567"
                },
                {
                    "telegram_id": "111111111",
                    "name": "John Doe",
                    "role": UserRole.WAITER,
                    "phone": "+251922345678"
                },
                {
                    "telegram_id": "222222222",
                    "name": "Jane Smith",
                    "role": UserRole.WAITER,
                    "phone": "+251933456789"
                },
                {
                    "telegram_id": "333333333",
                    "name": "Mike Johnson",
                    "role": UserRole.WAITER,
                    "phone": "+251944567890"
                }
            ]
            
            created_users = []
            for user_data in demo_users:
                user = UserOperations.create_user(
                    session=session,
                    telegram_id=user_data["telegram_id"],
                    name=user_data["name"],
                    role=user_data["role"],
                    phone=user_data["phone"]
                )
                created_users.append(user)
                print(f"✅ Created user: {user.name} ({user.role.value})")
            
            # Assign tables to waiters
            waiters = [u for u in created_users if u.role == UserRole.WAITER]
            for i, waiter in enumerate(waiters):
                # Assign 2-3 tables to each waiter
                start_idx = i * 3
                for j in range(2):
                    if start_idx + j < len(tables):
                        TableOperations.assign_table_to_user(
                            session=session,
                            user_id=waiter.id,
                            table_id=tables[start_idx + j].id
                        )
                        print(f"✅ Assigned table {tables[start_idx + j].table_number} to {waiter.name}")
            
            # Create demo transactions
            demo_transactions = [
                {
                    "stn_number": "STN12345678",
                    "amount": 5500.00,
                    "bank_type": BankType.CBE,
                    "sender_account": "Customer A",
                    "receiver_account": "Demo Restaurant"
                },
                {
                    "stn_number": "STN12345679",
                    "amount": 4200.00,
                    "bank_type": BankType.TELEBIRR,
                    "sender_account": "Customer B",
                    "receiver_account": "Demo Restaurant"
                },
                {
                    "stn_number": "STN12345680",
                    "amount": 3800.00,
                    "bank_type": BankType.CBE,
                    "sender_account": "Customer C",
                    "receiver_account": "Demo Restaurant"
                },
                {
                    "stn_number": "STN12345681",
                    "amount": 3000.00,
                    "bank_type": BankType.DASHEN,
                    "sender_account": "Customer D",
                    "receiver_account": "Demo Restaurant"
                },
                {
                    "stn_number": "STN12345682",
                    "amount": 2000.00,
                    "bank_type": BankType.TELEBIRR,
                    "sender_account": "Customer E",
                    "receiver_account": "Demo Restaurant"
                }
            ]
            
            waiter = waiters[0]  # Use first waiter for demo transactions
            for i, trans_data in enumerate(demo_transactions):
                transaction = TransactionOperations.create_transaction(
                    session=session,
                    stn_number=trans_data["stn_number"],
                    amount=trans_data["amount"],
                    user_id=waiter.id,
                    restaurant_id=restaurant.id,
                    bank_type=trans_data["bank_type"],
                    sender_account=trans_data["sender_account"],
                    receiver_account=trans_data["receiver_account"],
                    verification_confidence=0.85,
                    ocr_data={
                        "extracted_text": f"Demo transaction {i+1}",
                        "confidence": 0.85
                    }
                )
                
                # Update transaction status after creation
                TransactionOperations.update_transaction_status(
                    session=session,
                    transaction_id=transaction.id,
                    status=VerificationStatus.VERIFIED
                )
                print(f"✅ Created transaction: {transaction.stn_number}")
            
            # Log setup completion
            SystemLogOperations.log_event(
                session=session,
                level="INFO",
                message="Demo data setup completed successfully",
                module="lean_setup",
                function="create_demo_data"
            )
            
            print("✅ Demo data created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating demo data: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def setup_config(self):
        """Setup configuration file"""
        print("⚙️  Setting up configuration...")
        
        config_template = {
            "telegram": {
                "waiter_bot_token": "YOUR_BOT_TOKEN_HERE",
                "admin_bot_token": "YOUR_BOT_TOKEN_HERE",
                "webhook_url": "https://your-domain.com/webhook",
                "admin_user_ids": ["123456789"]  # Demo admin ID
            },
            "database": {
                "url": "sqlite:///lean_veripay.db",  # Use SQLite for simplicity
                "pool_size": 5,
                "max_overflow": 10,
                "echo": False
            },
            "ai": {
                "ocr_engine": "tesseract",
                "tesseract_path": "/usr/local/bin/tesseract",
                "confidence_threshold": 0.7
            },
            "storage": {
                "upload_path": "./uploads",
                "max_file_size_mb": 10,
                "allowed_extensions": ["jpg", "jpeg", "png", "pdf"]
            },
            "logging": {
                "level": "INFO",
                "file": "logs/lean_veripay.log",
                "max_size_mb": 50,
                "backup_count": 3
            }
        }
        
        try:
            # Check if config already exists
            if os.path.exists(self.config_path):
                print(f"⚠️  Configuration file {self.config_path} already exists")
                return True
            
            # Create config file
            with open(self.config_path, 'w') as file:
                yaml.dump(config_template, file, default_flow_style=False)
            
            print(f"✅ Configuration file created: {self.config_path}")
            print("⚠️  Please update the bot token in the configuration file")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up configuration: {e}")
            return False
    
    def run_setup(self):
        """Run complete setup"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                Lean VeriPay Setup                            ║
║                                                              ║
║  🚀 Setting up simplified VeriPay system                    ║
║  📱 Single bot with role-based access                       ║
║  🔍 OCR processing for payment screenshots                  ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # Setup configuration
        if not self.setup_config():
            print("❌ Setup failed at configuration step")
            return False
        
        # Setup database
        if not self.setup_database():
            print("❌ Setup failed at database step")
            return False
        
        # Create demo data
        if not self.create_demo_data():
            print("❌ Setup failed at demo data step")
            return False
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║                Setup Complete! 🎉                            ║
║                                                              ║
║  ✅ Configuration created                                    ║
║  ✅ Database tables created                                  ║
║  ✅ Demo data created                                        ║
║                                                              ║
║  📱 Next Steps:                                             ║
║  1. Update bot token in config.yaml                         ║
║  2. Run: python lean_veripay_bot.py                         ║
║  3. Test with demo users                                    ║
║                                                              ║
║  🎭 Demo Users:                                             ║
║  • Admin: 123456789                                         ║
║  • Waiters: 111111111, 222222222, 333333333                ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        return True


def main():
    """Main setup function"""
    setup = LeanVeriPaySetup()
    
    try:
        success = setup.run_setup()
        if success:
            print("🎉 Lean VeriPay setup completed successfully!")
        else:
            print("❌ Setup failed. Please check the error messages above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 