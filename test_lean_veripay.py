#!/usr/bin/env python3
"""
Test script for Lean VeriPay implementation
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test database models
        from database.lean_models import (
            Base, User, Restaurant, Table, TableAssignment, Transaction,
            BankStatement, ReconciliationReport, SystemLog,
            UserRole, VerificationStatus, BankType
        )
        print("✅ Database models imported successfully")
        
        # Test database operations
        from database.lean_operations import (
            LeanDatabaseManager, UserOperations, RestaurantOperations,
            TableOperations, TransactionOperations, BankStatementOperations,
            SystemLogOperations
        )
        print("✅ Database operations imported successfully")
        
        # Test OCR extractor
        from lean_veripay_bot import LeanOCRExtractor
        print("✅ OCR extractor imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_database_setup():
    """Test database setup"""
    print("\n🗄️  Testing database setup...")
    
    try:
        from database.lean_operations import LeanDatabaseManager
        
        # Create database manager
        db_manager = LeanDatabaseManager("config.yaml")
        session = db_manager.get_session()
        
        # Test basic operations
        from database.lean_models import User, UserRole
        
        # Create test user
        from database.lean_operations import UserOperations
        test_user = UserOperations.create_user(
            session=session,
            telegram_id="999999999",
            name="Test User",
            role=UserRole.WAITER
        )
        
        # Retrieve test user
        retrieved_user = UserOperations.get_user_by_telegram_id(
            session=session,
            telegram_id="999999999"
        )
        
        if retrieved_user and retrieved_user.name == "Test User":
            print("✅ Database operations working correctly")
            
            # Clean up test data
            session.delete(test_user)
            session.commit()
            session.close()
            return True
        else:
            print("❌ Database operations failed")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Database test error: {e}")
        return False

def test_ocr_extractor():
    """Test OCR extractor"""
    print("\n🔍 Testing OCR extractor...")
    
    try:
        from lean_veripay_bot import LeanOCRExtractor
        
        # Create OCR extractor
        extractor = LeanOCRExtractor()
        
        # Test pattern matching
        test_text = """
        Transaction: STN12345678
        Amount: 1,500.00 Birr
        Date: 15/01/2024
        Time: 14:30:25
        From: John Doe
        To: Sample Restaurant
        Bank: CBE
        """
        
        # Test text parsing
        extracted_data = extractor._parse_text_data(test_text)
        
        expected_fields = ['stn_number', 'amount', 'transaction_date', 'sender_account', 'receiver_account']
        missing_fields = [field for field in expected_fields if not extracted_data.get(field)]
        
        if not missing_fields:
            print("✅ OCR extractor working correctly")
            print(f"   Extracted: {extracted_data}")
            return True
        else:
            print(f"❌ OCR extractor missing fields: {missing_fields}")
            return False
            
    except Exception as e:
        print(f"❌ OCR test error: {e}")
        return False

def test_configuration():
    """Test configuration file"""
    print("\n⚙️  Testing configuration...")
    
    try:
        import yaml
        
        # Check if config file exists
        if not os.path.exists("config.yaml"):
            print("⚠️  config.yaml not found - run lean_setup.py first")
            return False
        
        # Load configuration
        with open("config.yaml", 'r') as file:
            config = yaml.safe_load(file)
        
        # Check required sections
        required_sections = ['telegram', 'database', 'ai', 'storage']
        missing_sections = [section for section in required_sections if section not in config]
        
        if not missing_sections:
            print("✅ Configuration file valid")
            return True
        else:
            print(f"❌ Missing configuration sections: {missing_sections}")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test error: {e}")
        return False

def test_directories():
    """Test required directories"""
    print("\n📁 Testing directories...")
    
    required_dirs = ['uploads', 'logs', 'reports', 'backups']
    missing_dirs = []
    
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing_dirs.append(dir_name)
            # Create directory
            Path(dir_name).mkdir(exist_ok=True)
            print(f"   Created directory: {dir_name}")
    
    if not missing_dirs:
        print("✅ All required directories exist")
        return True
    else:
        print(f"⚠️  Created missing directories: {missing_dirs}")
        return True

def test_dependencies():
    """Test required dependencies"""
    print("\n📦 Testing dependencies...")
    
    required_packages = [
        'aiogram',
        'sqlalchemy',
        'cv2',  # opencv-python
        'pytesseract',
        'PIL',  # Pillow
        'yaml',  # pyyaml
        'loguru'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if not missing_packages:
        print("✅ All required dependencies installed")
        return True
    else:
        print(f"❌ Missing dependencies: {missing_packages}")
        print("   Install with: pip install -r lean_requirements.txt")
        return False

def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                Lean VeriPay Test Suite                       ║
║                                                              ║
║  🧪 Testing lean VeriPay implementation                     ║
║  📱 Single bot with role-based access                       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Configuration", test_configuration),
        ("Directories", test_directories),
        ("Imports", test_imports),
        ("Database Setup", test_database_setup),
        ("OCR Extractor", test_ocr_extractor),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print('='*50)
    
    if passed == total:
        print("🎉 All tests passed! Lean VeriPay is ready to use.")
        print("\n📱 Next steps:")
        print("1. Update bot token in config.yaml")
        print("2. Run: python lean_veripay_bot.py")
        print("3. Test with demo users")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\n🔧 Common fixes:")
        print("1. Run: pip install -r lean_requirements.txt")
        print("2. Run: python lean_setup.py")
        print("3. Install Tesseract OCR")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 